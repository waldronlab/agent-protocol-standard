#!/usr/bin/env python3
"""Check an execution of a protocol's tests against their expectations.

    check_test_result.py --shape TESTS_DIR RESULTS_DIR [--test NAME] [--bundle BUNDLE_DIR]
        Print the result shape of every test (values withheld) and write
        RESULTS_DIR/source.yaml, the snapshot the run is attributed to. With
        --bundle, also write everything the executor may see into BUNDLE_DIR:
        protocol.md, the protocols it uses, each test's inputs, and the shape.
        The executor then writes its results into BUNDLE_DIR/results.

    check_test_result.py TESTS_DIR RESULTS_DIR [--test NAME]
        Compare each test's result.yaml against the test, write
        RESULTS_DIR/run.yaml, and exit 0 if every compared test passed, 1 if
        any failed, 2 if the contract was not met. A run is checked once:
        a results directory that already holds run.yaml is refused.

The contract is the "Tests" section of PROTOCOL_STANDARD.md. This script is
the only thing that decides pass or fail.
"""
import sys
import os
import csv
import hashlib
import shutil
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import subprocess
import urllib.request
import http.client
from pathlib import Path
from datetime import datetime, timezone

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from models import (  # noqa: E402
    ProtocolTest, FileRef, is_file_mapping, RESERVED_RESULT_KEYS, RESERVED_RUN_RECORD_KEYS,
)
from validate_protocol import load_test_case, extract_frontmatter  # noqa: E402
from repo_utils import parse_repository_url  # noqa: E402

CHECKER_NAME = "check_test_result.py"
CHECKER_VERSION = "0.3.0"
RUN_RECORD_VERSION = 1
SOURCE_FILE = "source.yaml"
EXECUTOR_FILE = "executor.yaml"
RUN_FILE = "run.yaml"
RESULT_FILE = "result.yaml"
CACHE_DIR = ".remote"
# Inside a bundle
SHAPE_FILE = "shape.yaml"
BUNDLE_INPUTS = "inputs"
BUNDLE_PROTOCOLS = "protocols"
BUNDLE_RESULTS = "results"


class ContractError(Exception):
    """The inputs do not meet the contract; nothing was compared."""


class TableError(Exception):
    """A CSV file is not a well-formed table."""


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_tests(tests_dir: Path, only: str = None):
    if not tests_dir.is_dir():
        raise ContractError(f"'{tests_dir}' is not a directory")
    if tests_dir.is_symlink():
        raise ContractError(f"{tests_dir} is a symlink; the protocol directory and tests/ may not contain symlinks")
    cases = []
    errors = []
    for entry in sorted(tests_dir.iterdir()):
        if entry.name.startswith('.'):
            continue
        if not entry.is_dir():
            # The validator rejects these; the checker must not quietly run without them.
            errors.append(f"tests/{entry.name}: only test directories belong directly under tests/")
            continue
        if only is not None and entry.name != only:
            continue
        case, errs = load_test_case(entry)
        if errs:
            errors.extend(errs)
        else:
            cases.append((entry, case))
    if errors:
        raise ContractError("tests do not conform to the schema:\n  " + "\n  ".join(errors))
    if only is not None and not cases:
        raise ContractError(f"no test named '{only}' under {tests_dir}")
    if not cases:
        raise ContractError(f"no tests under {tests_dir}")
    return cases


def load_frontmatter(protocol_dir: Path) -> dict:
    protocol_md = protocol_dir / "protocol.md"
    if not protocol_md.is_file():
        raise ContractError(f"no protocol.md beside {protocol_dir / 'tests'}")
    try:
        fm = extract_frontmatter(str(protocol_md))
    except Exception as e:
        raise ContractError(f"{protocol_md}: {e}")
    if not isinstance(fm, dict):
        raise ContractError(f"{protocol_md} has no parseable frontmatter")
    return fm


# ---------------------------------------------------------------------------
# Source snapshot
# ---------------------------------------------------------------------------

def compute_digest(protocol_dir: Path) -> str:
    """sha256 over protocol.md and every file under tests/, by sorted relative path."""
    h = hashlib.sha256()
    files = [protocol_dir / "protocol.md"]
    tests_dir = protocol_dir / "tests"
    if tests_dir.is_symlink():
        raise ContractError(f"{tests_dir} is a symlink; the protocol directory and tests/ may not contain symlinks")
    if tests_dir.is_dir():
        for p in tests_dir.rglob("*"):
            if p.is_symlink():
                # A symlink would let the content change without the digest noticing.
                raise ContractError(f"{p} is a symlink; the protocol directory and tests/ may not contain symlinks")
            if p.is_file():
                files.append(p)
    if files[0].is_symlink():
        raise ContractError(f"{files[0]} is a symlink; the protocol directory and tests/ may not contain symlinks")
    for p in sorted(files, key=lambda p: p.relative_to(protocol_dir).as_posix()):
        h.update(p.relative_to(protocol_dir).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def _git(protocol_dir: Path, *args):
    try:
        out = subprocess.run(["git", "-C", str(protocol_dir), *args],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return None


def source_snapshot(protocol_dir: Path) -> dict:
    commit = _git(protocol_dir, "rev-parse", "--short=7", "HEAD")
    status = _git(protocol_dir, "status", "--porcelain", "--untracked-files=all", "--", ".")
    # git status omits ignored files, but the digest covers them; an ignored input is still
    # content the commit does not contain.
    ignored = _git(protocol_dir, "ls-files", "--others", "--ignored", "--exclude-standard", "--", ".")
    uncommitted = commit is None or status is None or bool(status) or bool(ignored)
    snapshot = {
        "protocol_commit": None if uncommitted else commit,
        "uncommitted": uncommitted,
        "source_digest": compute_digest(protocol_dir),
    }
    remote = _git(protocol_dir, "remote", "get-url", "origin")
    repo = os.environ.get("GITHUB_REPOSITORY") or (parse_repository_url(remote) if remote else None)
    snapshot["repository"] = repo
    return snapshot


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------

def _type_name(v) -> str:
    if isinstance(v, bool):
        return "boolean"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "mapping"
    return "any"


def _csv_header(test_dir: Path, results_dir: Path, ref: FileRef):
    path = resolve_expected_file(test_dir, results_dir, ref)
    with path.open(newline="", encoding="utf-8") as f:
        return next(csv.reader(f), [])


def shape_value(v, test_dir: Path, results_dir: Path, top: bool):
    """Describe v with every value withheld. Nested mapping keys are withheld too."""
    if top:
        # The section itself: its keys are parameter names, never a file slot.
        return {k: shape_value(x, test_dir, results_dir, False) for k, x in v.items()}
    if is_file_mapping(v):
        ref = FileRef(**v)
        slot = {"file": "csv" if ref.is_table else "file"}
        if ref.is_table:
            slot["header"] = "withheld" if ref.header == "withheld" else _csv_header(test_dir, results_dir, ref)
        return slot
    if isinstance(v, dict):
        types = {_type_name(x) for x in v.values()}
        value_type = types.pop() if len(types) == 1 else "any"
        return {"<key>": value_type}
    return _type_name(v)


def shape_inputs(inputs: dict, test_dir: Path, results_dir: Path) -> dict:
    """Inputs as the executor receives them. A remote file is downloaded now, verified against
    its digest, and handed over as a local path, so execution never runs on unverified bytes."""
    out = {}
    for k, v in inputs.items():
        if is_file_mapping(v) and "url" in v:
            ref = FileRef(**v)
            local = resolve_expected_file(test_dir, results_dir, ref)
            # Absolute, because the executor resolves input paths against the test directory.
            out[k] = {"path": str(local.resolve()), "url": ref.url, "sha256": ref.sha256}
        else:
            out[k] = v
    return out


def shape_of(case: ProtocolTest, test_dir: Path, results_dir: Path) -> dict:
    shape = {
        "name": case.name,
        "description": case.description,
        "test_directory": str(test_dir),
        "mode": case.evaluation.mode,
        "numeric_tolerance": case.evaluation.numeric_tolerance,
        "inputs": shape_inputs(case.inputs, test_dir, results_dir),
    }
    if case.evaluation.mode == "exact":
        shape["result"] = shape_value(case.expected_outputs, test_dir, results_dir, True)
    else:
        outcomes = []
        for o in case.evaluation.accepted_outcomes:
            entry = {"outcome": o.outcome}
            if o.expected_outputs:
                entry["expected_present"] = shape_value(o.expected_outputs, test_dir, results_dir, True)
            if o.expected_absent:
                entry["expected_absent"] = list(o.expected_absent)
            outcomes.append(entry)
        shape["result"] = {"outcome": "one of the labels below", "observation": "string",
                           "warnings": "list of strings, when the protocol said to warn"}
        shape["accepted_outcomes"] = outcomes
    return shape


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def check_dirs_for_shape(protocol_dir: Path, results_dir: Path, bundle_dir: Path = None):
    # Everything is checked before anything is created, so a refusal leaves nothing behind.
    if _inside(results_dir, protocol_dir):
        raise ContractError(f"results directory {results_dir} lies inside the protocol directory; put it elsewhere")
    dirs = [("results", results_dir)]
    if bundle_dir is not None:
        checkout = Path(_git(protocol_dir, "rev-parse", "--show-toplevel") or protocol_dir.parent)
        if _inside(bundle_dir, checkout):
            raise ContractError(f"bundle directory {bundle_dir} lies inside the checkout {checkout}, "
                                "where the executor could reach the tests; put it elsewhere")
        if _inside(bundle_dir, results_dir) or _inside(results_dir, bundle_dir):
            # The results directory caches remote expected files, so the executor never sees it.
            raise ContractError(f"bundle directory {bundle_dir} and results directory {results_dir} "
                                "must not contain one another")
        dirs.append(("bundle", bundle_dir))
    for what, d in dirs:
        if d.is_dir() and any(d.iterdir()):
            raise ContractError(f"{what} directory {d} is not empty; use a new directory for each run")
    for _, d in dirs:
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Bundle: everything the executor may see, and nothing else
# ---------------------------------------------------------------------------

def bundle_dependencies(protocol_dir: Path, fm: dict) -> list:
    """protocol.md of every protocol this one uses, transitively, found in the checkout by file
    presence at the pinned version. Resolving a dependency from another repository is #55; until
    then one that is not in the checkout cannot be bundled."""
    protocols_dir = protocol_dir.parent
    found = {}
    queue = [(fm.get("name"), fm)]
    while queue:
        user, user_fm = queue.pop()
        for dep in user_fm.get("protocols_used") or []:
            name = dep.get("name") if isinstance(dep, dict) else None
            if not isinstance(name, str) or Path(name).name != name or name in (".", ".."):
                raise ContractError(f"'{user}' has a protocols_used entry without a usable name: {dep!r}")
            version = str(dep.get("version"))
            if name in found:
                if found[name][1] != version:
                    raise ContractError(f"'{name}' is pinned at both {found[name][1]} and {version}; "
                                        "a bundle holds one version of each protocol")
                continue
            path = protocols_dir / name / "protocol.md"
            if not path.is_file():
                raise ContractError(f"'{user}' uses '{name}', which is not in this checkout at {path}; "
                                    "bundling a dependency from another repository waits on #55")
            dep_fm = load_frontmatter(path.parent)
            if str(dep_fm.get("version")) != version:
                raise ContractError(f"'{user}' pins '{name}' at {version}, but {path} is version {dep_fm.get('version')}")
            found[name] = (path, version)
            queue.append((name, dep_fm))
    return [path for path, _ in found.values()]


def write_bundle(bundle_dir: Path, protocol_dir: Path, fm: dict, cases: list, results_dir: Path,
                 dependencies: list) -> dict:
    """Copy what the executor may see into bundle_dir and return the shape, with input paths
    relative to each test's directory in the bundle."""
    bundle_dir = bundle_dir.resolve()  # the executor is handed these paths from anywhere
    shutil.copyfile(protocol_dir / "protocol.md", bundle_dir / "protocol.md")
    for path in dependencies:
        target = bundle_dir / BUNDLE_PROTOCOLS / path.parent.name / "protocol.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    shapes = []
    for test_dir, case in cases:
        dest = bundle_dir / BUNDLE_INPUTS / case.name
        dest.mkdir(parents=True)
        shape = shape_of(case, test_dir, results_dir)
        inputs = {}
        for k, v in case.inputs.items():
            if not is_file_mapping(v):
                inputs[k] = v
                continue
            ref = FileRef(**v)
            # Only the files the inputs name; a remote one is the copy --shape already verified.
            rel = ref.path if ref.path is not None else ref.name
            target = dest / rel
            if target.exists():
                raise ContractError(f"test '{case.name}' names two inputs that would both be {rel} in the bundle")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resolve_expected_file(test_dir, results_dir, ref), target)
            inputs[k] = {"path": rel}
        shape["test_directory"] = str(dest)
        shape["inputs"] = inputs
        shapes.append(shape)
    (bundle_dir / BUNDLE_RESULTS).mkdir()
    out = {
        "protocol": fm.get("name"),
        "version": str(fm.get("version")),
        "results_directory": str(bundle_dir / BUNDLE_RESULTS),
        "tests": shapes,
    }
    (bundle_dir / SHAPE_FILE).write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True),
                                         encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def resolve_expected_file(test_dir: Path, results_dir: Path, ref: FileRef) -> Path:
    if ref.path is not None:
        p = test_dir / ref.path
        if not p.is_file():
            raise ContractError(f"expected file '{ref.path}' is missing from {test_dir}")
        return p
    cache = results_dir / CACHE_DIR
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f"{ref.sha256}{Path(ref.name).suffix}"
    if target.is_file():
        # The cache lives in the results directory, which the digest of the source does not
        # cover, so cached bytes are verified every time they are used.
        cached = hashlib.sha256(target.read_bytes()).hexdigest()
        if cached == ref.sha256:
            return target
        target.unlink()
    try:
        with urllib.request.urlopen(ref.url) as resp:  # noqa: S310 - https enforced by the schema
            data = resp.read()
    except (OSError, ValueError, UnicodeError, http.client.HTTPException) as e:
        # URLError and HTTPError are OSErrors; InvalidURL is an HTTPException.
        raise ContractError(f"could not download {ref.url}: {e}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != ref.sha256:
        raise ContractError(f"downloaded {ref.url} has sha256 {digest}, expected {ref.sha256}")
    target.write_bytes(data)
    return target


def read_csv(path: Path):
    """Header and rows of a CSV table. Raises TableError when it is not a table."""
    try:
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f, strict=True))  # strict: an unterminated quote is an error
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        raise TableError(f"{path}: {e}")
    if not rows:
        raise TableError(f"{path} is empty; a table needs a header row")
    width = len(rows[0])
    for i, r in enumerate(rows[1:], start=1):
        if len(r) != width:
            raise TableError(f"{path} row {i} has {len(r)} cells but the header has {width}")
    return rows[0], rows[1:]


def _as_number(s: str):
    """A CSV cell as a Decimal, exact to the digits written, or None if it is not a number.
    NaN parses as a number so that it can fail the comparison rather than match as a string."""
    s = s.strip()
    if s == "":
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _within(actual: Decimal, expected: Decimal, tol: Decimal) -> bool:
    if actual.is_nan() or expected.is_nan():
        return False
    if actual.is_infinite() or expected.is_infinite():
        return actual == expected
    # Exact rational arithmetic: the Decimal context would round a boundary difference.
    return abs(Fraction(actual) - Fraction(expected)) <= Fraction(tol)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare_table(expected_path: Path, actual_path: Path, tol: float, where: str):
    failures = []
    try:
        exp_header, exp_rows = read_csv(expected_path)
    except TableError as e:
        raise ContractError(f"expected table is malformed: {e}")  # the test is broken, not the result
    try:
        act_header, act_rows = read_csv(actual_path)
    except TableError as e:
        return [f"{where}: result table is malformed: {e}"]
    dtol = Decimal(repr(tol))
    if exp_header != act_header:
        failures.append(f"{where}: header is {act_header}, expected {exp_header}")
        return failures
    if len(exp_rows) != len(act_rows):
        failures.append(f"{where}: {len(act_rows)} data rows, expected {len(exp_rows)}")
        return failures
    for i, (e, a) in enumerate(zip(exp_rows, act_rows), start=1):
        if len(e) != len(a):
            failures.append(f"{where} row {i}: {len(a)} cells, expected {len(e)}")
            continue
        for j, (ec, ac) in enumerate(zip(e, a)):
            cell = f"{where} row {i} column '{exp_header[j]}'"
            if j == 0 or _as_number(ec) is None:
                if ec != ac:
                    failures.append(f"{cell}: '{ac}', expected '{ec}'")
            else:
                an = _as_number(ac)
                if an is None or not _within(an, _as_number(ec), dtol):
                    failures.append(f"{cell}: '{ac}', expected {ec} within {tol}")
    return failures


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def compare_value(expected, actual, tol: float, where: str, test_dir: Path, result_dir: Path,
                  results_dir: Path):
    """Return a list of failure messages; empty means match."""
    if is_file_mapping(expected):
        ref = FileRef(**expected)
        if not (isinstance(actual, dict) and isinstance(actual.get("path"), str)):
            return [f"{where}: expected a file slot {{path: ...}}, found {actual!r}"]
        actual_path = result_dir / actual["path"]
        try:
            actual_path.resolve().relative_to(result_dir.resolve())
        except ValueError:
            # Lexical '..' and symlinks alike: a result file is produced inside the result
            # directory, or it is not a result.
            return [f"{where}: result file '{actual['path']}' resolves outside the result directory"]
        if not actual_path.is_file():
            return [f"{where}: result file '{actual['path']}' does not exist in {result_dir}"]
        return compare_table(resolve_expected_file(test_dir, results_dir, ref), actual_path, tol, where)
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{where}: expected a mapping, found {_type_name(actual)}"]
        failures = []
        missing = [k for k in expected if k not in actual]
        extra = [k for k in actual if k not in expected]
        if missing:
            failures.append(f"{where}: missing keys {missing}")
        if extra:
            failures.append(f"{where}: unexpected keys {extra}")
        for k in expected:
            if k in actual:
                failures += compare_value(expected[k], actual[k], tol, f"{where}.{k}",
                                          test_dir, result_dir, results_dir)
        return failures
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{where}: expected a list, found {_type_name(actual)}"]
        if len(expected) != len(actual):
            return [f"{where}: {len(actual)} elements, expected {len(expected)}: {actual!r} vs {expected!r}"]
        failures = []
        for i, (e, a) in enumerate(zip(expected, actual)):
            failures += compare_value(e, a, tol, f"{where}[{i}]", test_dir, result_dir, results_dir)
        return failures
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if type(actual) is not type(expected) or actual != expected:
            return [f"{where}: {actual!r}, expected {expected!r}"]
        return []
    if _is_number(expected):
        if not _is_number(actual):
            return [f"{where}: {actual!r}, expected the number {expected!r}"]
        # Decimals from the written representation, so an int and a float that differ beyond
        # float precision do not round to equality, and NaN never matches.
        if not _within(Decimal(repr(actual)), Decimal(repr(expected)), Decimal(repr(tol))):
            return [f"{where}: {actual!r}, expected {expected!r} within {tol}"]
        return []
    return [f"{where}: unsupported expected value {expected!r}"]


def compare_top(expected: dict, result: dict, tol: float, test_dir: Path, result_dir: Path,
                results_dir: Path):
    """Top level of result.yaml: missing keys fail, extra keys are ignored."""
    failures = []
    for k, e in expected.items():
        if k not in result:
            failures.append(f"{k}: missing from result.yaml")
        else:
            failures += compare_value(e, result[k], tol, k, test_dir, result_dir, results_dir)
    return failures


def check_one(case: ProtocolTest, test_dir: Path, result_dir: Path, results_dir: Path) -> dict:
    entry = {"name": case.name}
    result_yaml = result_dir / RESULT_FILE
    if result_yaml.is_symlink():
        entry["result"] = "fail"
        entry["failures"] = [f"{result_yaml} is a symlink; a result is written in place"]
        return entry
    if not result_yaml.is_file():
        entry["result"] = "fail"
        entry["failures"] = [f"{result_dir / RESULT_FILE} does not exist"]
        return entry
    try:
        result = yaml.safe_load(result_yaml.read_text(encoding="utf-8"))
    except Exception as e:
        entry["result"] = "fail"
        entry["failures"] = [f"result.yaml failed to parse: {e}"]
        return entry
    if not isinstance(result, dict):
        entry["result"] = "fail"
        entry["failures"] = ["result.yaml is not a mapping"]
        return entry

    tol = case.evaluation.numeric_tolerance
    warnings = result.get("warnings")
    warnings_ok = warnings is None or (isinstance(warnings, list) and all(isinstance(w, str) for w in warnings))
    failures = [] if warnings_ok else ["warnings: must be a list of strings"]
    if case.evaluation.mode == "exact":
        failures += compare_top(case.expected_outputs, result, tol, test_dir, result_dir, results_dir)
    else:
        label = result.get("outcome")
        outcome = case.outcome(label) if isinstance(label, str) else None
        if outcome is None:
            accepted = [o.outcome for o in case.evaluation.accepted_outcomes]
            failures.append(f"outcome: {label!r} is not one of the accepted outcomes {accepted}")
        if not isinstance(result.get("observation"), str) or not result["observation"].strip():
            failures.append("observation: missing or empty; one sentence saying what was found is required")
        if outcome is not None:
            entry["outcome"] = label
            if outcome.expected_outputs:
                failures += compare_top(outcome.expected_outputs, result, tol, test_dir, result_dir, results_dir)
            for k in outcome.expected_absent or []:
                if k in result:
                    failures.append(f"{k}: present in result.yaml, but outcome '{label}' requires it absent")
            if outcome.expected_warning:
                needle = outcome.expected_warning.casefold()
                if not warnings_ok or not any(needle in w.casefold() for w in warnings or []):
                    failures.append(
                        f"warnings: no entry contains {outcome.expected_warning!r}, which outcome '{label}' requires"
                    )
    entry["result"] = "pass" if not failures else "fail"
    if failures:
        entry["failures"] = failures
    return entry


# ---------------------------------------------------------------------------
# Executor and run record
# ---------------------------------------------------------------------------

def _parse_timestamp(v):
    """A timezone-aware datetime, or None. Date-only and naive values are not timestamps."""
    if isinstance(v, datetime):
        dt = v
    elif isinstance(v, str):
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return dt if dt.tzinfo is not None else None


def _is_timestamp(v) -> bool:
    return _parse_timestamp(v) is not None


def load_executor(results_dir: Path) -> dict:
    path = results_dir / EXECUTOR_FILE
    if not path.is_file():
        raise ContractError(f"{path} is missing; the executor writes it before invoking the checker")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ContractError(f"{path} is not a mapping")
    for k in RESERVED_RUN_RECORD_KEYS:
        if k in data:
            raise ContractError(f"{path} supplies '{k}', which the checker writes itself; remove it")
    ex = data.get("executor")
    if not isinstance(ex, dict) or not isinstance(ex.get("agent"), str) or not ex["agent"].strip():
        raise ContractError(f"{path} needs an 'executor' mapping with a non-empty 'agent'")
    for k in ("started", "finished"):
        if not _is_timestamp(data.get(k)):
            raise ContractError(f"{path} needs '{k}' as an ISO 8601 timestamp with a timezone, such as 2026-10-18T14:02:11Z")
    return data


def _stamp(v) -> str:
    """Normalised to UTC, since the record says its timestamps are UTC."""
    return _parse_timestamp(v).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_timestamps(executor: dict, source: dict, checked: datetime):
    """The executor's times must fit between the checker's own: --shape before execution
    finished, and execution finished before now. Compared to the second, as they are recorded."""
    shaped = _parse_timestamp(source.get("taken"))
    if shaped is None:
        raise ContractError(f"{SOURCE_FILE} has no 'taken' timestamp; re-run from --shape")
    second = lambda dt: dt.astimezone(timezone.utc).replace(microsecond=0)  # noqa: E731
    started, finished = (second(_parse_timestamp(executor[k])) for k in ("started", "finished"))
    if started > finished:
        raise ContractError(f"{EXECUTOR_FILE}: 'started' {_stamp(started)} is after 'finished' {_stamp(finished)}")
    if finished < second(shaped):
        raise ContractError(f"{EXECUTOR_FILE}: 'finished' {_stamp(finished)} is before --shape took the snapshot "
                            f"at {_stamp(shaped)}; execution follows --shape")
    if finished > second(checked):
        raise ContractError(f"{EXECUTOR_FILE}: 'finished' {_stamp(finished)} is later than now, {_stamp(checked)}; "
                            "take timestamps from the clock, never write them by hand")


def build_run_record(fm: dict, source: dict, executor: dict, tests: list, checked: datetime) -> dict:
    record = {
        "run_record": RUN_RECORD_VERSION,
        "protocol": fm.get("name"),
        "version": str(fm.get("version")),
        "repository": source.get("repository"),
        "protocol_commit": source.get("protocol_commit"),
        "uncommitted": bool(source.get("uncommitted")),
        "source_digest": source.get("source_digest"),
        "started": _stamp(executor["started"]),
        "finished": _stamp(executor["finished"]),
        "shaped": _stamp(source["taken"]),
        "checked": _stamp(checked),
        "executor": executor["executor"],
    }
    for k, v in executor.items():
        if k not in ("executor", "started", "finished"):
            record[k] = v
    record["checker"] = f"{CHECKER_NAME} {CHECKER_VERSION}"
    record["tests"] = tests
    return record


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_shape(tests_dir: Path, results_dir: Path, only: str = None, bundle_dir: Path = None) -> int:
    protocol_dir = tests_dir.parent
    fm = load_frontmatter(protocol_dir)
    cases = load_tests(tests_dir, only)
    # Resolved before anything is created, so a refused dependency leaves nothing behind.
    dependencies = bundle_dependencies(protocol_dir, fm) if bundle_dir is not None else None
    check_dirs_for_shape(protocol_dir, results_dir, bundle_dir)
    snapshot = source_snapshot(protocol_dir)
    snapshot["protocol"] = fm.get("name")
    snapshot["taken"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if bundle_dir is not None:
        snapshot["bundle"] = str(bundle_dir.resolve())
    (results_dir / SOURCE_FILE).write_text(yaml.safe_dump(snapshot, sort_keys=False), encoding="utf-8")
    if bundle_dir is not None:
        out = write_bundle(bundle_dir, protocol_dir, fm, cases, results_dir, dependencies)
    else:
        out = {
            "protocol": fm.get("name"),
            "version": str(fm.get("version")),
            "results_directory": str(results_dir),
            "tests": [shape_of(case, test_dir, results_dir) for test_dir, case in cases],
        }
    sys.stdout.write(yaml.safe_dump(out, sort_keys=False, allow_unicode=True))
    return 0


def cmd_check(tests_dir: Path, results_dir: Path, only: str = None) -> int:
    protocol_dir = tests_dir.parent
    fm = load_frontmatter(protocol_dir)
    cases = load_tests(tests_dir, only)
    if not results_dir.is_dir():
        raise ContractError(f"results directory {results_dir} does not exist")
    if (results_dir / RUN_FILE).exists() or (results_dir / RUN_FILE).is_symlink():
        # A second check after reading the first one's failures would not be blind.
        raise ContractError(f"{results_dir / RUN_FILE} exists: this run was already checked, and a run is "
                            "checked once. Report it as it stands; another attempt starts from --shape "
                            "in a new results directory")
    source_path = results_dir / SOURCE_FILE
    if not source_path.is_file():
        raise ContractError(f"{source_path} is missing; run --shape before executing")
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise ContractError(f"{source_path} is not a mapping; re-run from --shape")
    current = compute_digest(protocol_dir)
    if source.get("source_digest") != current:
        raise ContractError(
            f"the protocol or its tests changed since --shape wrote {SOURCE_FILE} "
            f"({source.get('source_digest')} then, {current} now); re-run from --shape"
        )
    executor = load_executor(results_dir)
    checked = datetime.now(timezone.utc)
    check_timestamps(executor, source, checked)
    # With a bundle the executor wrote into the bundle, never into the results directory.
    results_root = results_dir
    if source.get("bundle"):
        results_root = Path(source["bundle"]) / BUNDLE_RESULTS
        if not results_root.is_dir():
            raise ContractError(f"{results_root} does not exist; the executor writes its results there")

    entries = []
    for test_dir, case in cases:
        result_dir = results_root / case.name
        if not result_dir.is_dir():
            entries.append({"name": case.name, "result": "not_run"})
            continue
        try:
            result_dir.resolve().relative_to(results_root.resolve())
            if result_dir.is_symlink():
                raise ValueError
        except ValueError:
            # A symlink to another run's directory would let stale outputs pass.
            entries.append({"name": case.name, "result": "fail",
                            "failures": [f"{result_dir} is a symlink or resolves outside the results directory"]})
            continue
        entries.append(check_one(case, test_dir, result_dir, results_dir))

    record = build_run_record(fm, source, executor, entries, checked)
    (results_dir / RUN_FILE).write_text(yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
                                        encoding="utf-8")

    n_pass = sum(1 for e in entries if e["result"] == "pass")
    n_fail = sum(1 for e in entries if e["result"] == "fail")
    n_skip = sum(1 for e in entries if e["result"] == "not_run")
    for e in entries:
        print(f"[{e['result'].upper():7}] {e['name']}" + (f" ({e['outcome']})" if "outcome" in e else ""))
        for f in e.get("failures", []):
            print(f"          {f}")
    print(f"\n{n_pass} passed, {n_fail} failed, {n_skip} not run. Record: {results_dir / RUN_FILE}")
    if n_fail:
        return 1
    if n_pass == 0:
        print("Nothing was compared.")
        return 2
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    shape = "--shape" in argv
    if shape:
        argv.remove("--shape")
    only = None
    if "--test" in argv:
        i = argv.index("--test")
        if i + 1 >= len(argv):
            print(__doc__)
            return 2
        only = argv[i + 1]
        del argv[i:i + 2]
    bundle_dir = None
    if "--bundle" in argv:
        i = argv.index("--bundle")
        if not shape or i + 1 >= len(argv):  # a bundle is made by --shape, before execution
            print(__doc__)
            return 2
        bundle_dir = Path(argv[i + 1])
        del argv[i:i + 2]
    if len(argv) != 2 or any(a.startswith("-") for a in argv):
        print(__doc__)
        return 2
    tests_dir, results_dir = Path(argv[0]), Path(argv[1])
    try:
        if shape:
            return cmd_shape(tests_dir, results_dir, only, bundle_dir)
        return cmd_check(tests_dir, results_dir, only)
    except ContractError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2
    except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
        # Malformed YAML, unreadable files, failed downloads: checking could not complete,
        # which is exit 2, not the exit 1 reserved for a failed comparison.
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
