#!/usr/bin/env python3
"""Check an execution of a protocol's tests against their expectations.

    check_test_result.py --shape TESTS_DIR RESULTS_DIR [--test NAME]
        Print the result shape of every test (values withheld) and write
        RESULTS_DIR/source.yaml, the snapshot the run is attributed to.

    check_test_result.py TESTS_DIR RESULTS_DIR [--test NAME]
        Compare RESULTS_DIR/<test>/result.yaml against each test, write
        RESULTS_DIR/run.yaml, and exit 0 if every compared test passed, 1 if
        any failed, 2 if the contract was not met.

The contract is the "Tests" section of PROTOCOL_STANDARD.md. This script is
the only thing that decides pass or fail.
"""
import sys
import os
import csv
import hashlib
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
CHECKER_VERSION = "0.2.0"
RUN_RECORD_VERSION = 1
SOURCE_FILE = "source.yaml"
EXECUTOR_FILE = "executor.yaml"
RUN_FILE = "run.yaml"
RESULT_FILE = "result.yaml"
CACHE_DIR = ".remote"


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


def check_results_dir_for_shape(protocol_dir: Path, results_dir: Path):
    inside = False
    try:
        results_dir.resolve().relative_to(protocol_dir.resolve())
        inside = True
    except ValueError:
        pass
    if inside:  # checked before anything is created, so a refusal leaves nothing behind
        raise ContractError(f"results directory {results_dir} lies inside the protocol directory; put it elsewhere")
    results_dir.mkdir(parents=True, exist_ok=True)
    if any(results_dir.iterdir()):
        raise ContractError(f"results directory {results_dir} is not empty; use a new directory for each run")


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
    if warnings is not None and not (isinstance(warnings, list) and all(isinstance(w, str) for w in warnings)):
        entry["result"] = "fail"
        entry["failures"] = ["warnings: must be a list of strings"]
        return entry
    if case.evaluation.mode == "exact":
        failures = compare_top(case.expected_outputs, result, tol, test_dir, result_dir, results_dir)
    else:
        failures = []
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
                if not any(needle in w.casefold() for w in warnings or []):
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


def build_run_record(fm: dict, source: dict, executor: dict, tests: list) -> dict:
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

def cmd_shape(tests_dir: Path, results_dir: Path, only: str = None) -> int:
    protocol_dir = tests_dir.parent
    fm = load_frontmatter(protocol_dir)
    cases = load_tests(tests_dir, only)
    check_results_dir_for_shape(protocol_dir, results_dir)
    snapshot = source_snapshot(protocol_dir)
    snapshot["protocol"] = fm.get("name")
    snapshot["taken"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (results_dir / SOURCE_FILE).write_text(yaml.safe_dump(snapshot, sort_keys=False), encoding="utf-8")
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

    entries = []
    for test_dir, case in cases:
        result_dir = results_dir / case.name
        if not result_dir.is_dir():
            entries.append({"name": case.name, "result": "not_run"})
            continue
        try:
            result_dir.resolve().relative_to(results_dir.resolve())
            if result_dir.is_symlink():
                raise ValueError
        except ValueError:
            # A symlink to another run's directory would let stale outputs pass.
            entries.append({"name": case.name, "result": "fail",
                            "failures": [f"{result_dir} is a symlink or resolves outside the results directory"]})
            continue
        entries.append(check_one(case, test_dir, result_dir, results_dir))

    record = build_run_record(fm, source, executor, entries)
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
    if len(argv) != 2 or any(a.startswith("-") for a in argv):
        print(__doc__)
        return 2
    tests_dir, results_dir = Path(argv[0]), Path(argv[1])
    try:
        return cmd_shape(tests_dir, results_dir, only) if shape else cmd_check(tests_dir, results_dir, only)
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
