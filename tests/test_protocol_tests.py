"""Protocol tests: the test.yaml schema, the validator's tests/ checks, and the checker."""
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from scripts.models import ProtocolTest
from scripts.validate_protocol import validate_protocol, load_test_case
from scripts import check_test_result as checker

FIXTURES = Path(__file__).parent / "fixtures"
WITH_TESTS = FIXTURES / "valid" / "with-tests" / "protocols" / "example-protocol"


# ---------------------------------------------------------------------------
# Schema, in memory
# ---------------------------------------------------------------------------

def exact_case(**over):
    d = {
        "name": "basic",
        "description": "A test.",
        "inputs": {"theta": 0.5, "data": {"path": "input.csv"}},
        "expected_outputs": {"n": 1, "table": {"path": "out.csv"}},
        "evaluation": {"mode": "exact"},
    }
    d.update(over)
    return d


def test_exact_case_valid():
    case = ProtocolTest(**exact_case())
    assert case.evaluation.numeric_tolerance == 0


def test_remote_file_needs_https_and_digest():
    bad = exact_case(inputs={"data": {"url": "http://example.org/x.csv", "sha256": "0" * 64}})
    with pytest.raises(ValidationError, match="https"):
        ProtocolTest(**bad)
    bad = exact_case(inputs={"data": {"url": "https://example.org/x.csv"}})
    with pytest.raises(ValidationError, match="sha256"):
        ProtocolTest(**bad)


def test_path_may_not_escape():
    with pytest.raises(ValidationError, match="leave the test directory"):
        ProtocolTest(**exact_case(inputs={"data": {"path": "../secret.csv"}}))


def test_header_only_on_expected_table():
    with pytest.raises(ValidationError, match="'header' is only allowed"):
        ProtocolTest(**exact_case(inputs={"data": {"path": "input.csv", "header": "withheld"}}))
    ok = exact_case(expected_outputs={"t": {"path": "out.csv", "header": "withheld"}})
    ProtocolTest(**ok)


def test_diagnostic_requires_evidence_and_no_top_level_expectations():
    base = {
        "name": "diag", "description": "x", "inputs": {},
        "evaluation": {"mode": "diagnostic", "accepted_outcomes": [{"outcome": "refused", "expected_absent": ["n"]}]},
    }
    ProtocolTest(**base)
    with pytest.raises(ValidationError, match="under each accepted outcome"):
        ProtocolTest(**{**base, "expected_outputs": {"n": 1}})
    with pytest.raises(ValidationError, match="needs evidence"):
        ProtocolTest(**{**base, "evaluation": {"mode": "diagnostic",
                                            "accepted_outcomes": [{"outcome": "refused", "expected_absent": []}]}})
    with pytest.raises(ValidationError, match="reserved key"):
        ProtocolTest(**{**base, "evaluation": {"mode": "diagnostic",
                                            "accepted_outcomes": [{"outcome": "r", "expected_absent": ["observation"]}]}})
    with pytest.raises(ValidationError, match="unique"):
        ProtocolTest(**{**base, "evaluation": {"mode": "diagnostic", "accepted_outcomes": [
            {"outcome": "r", "expected_absent": ["n"]}, {"outcome": "r", "expected_absent": ["m"]}]}})


def test_negative_or_non_finite_tolerance_rejected():
    for bad in (-1, float("nan"), float("inf")):
        with pytest.raises(ValidationError, match="finite number >= 0"):
            ProtocolTest(**exact_case(evaluation={"mode": "exact", "numeric_tolerance": bad}))


def test_parameter_named_path_is_not_a_file():
    case = ProtocolTest(**exact_case(inputs={"path": "literal", "url": "also literal"},
                                     expected_outputs={"path": "out"}))
    assert case.inputs["path"] == "literal"
    case = ProtocolTest(**exact_case(inputs={"path": {"path": "input.csv"}}))
    assert case.inputs["path"] == {"path": "input.csv"}


# ---------------------------------------------------------------------------
# Validator: fixtures on disk
# ---------------------------------------------------------------------------

def test_with_tests_fixture_validates(capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "example-org/example-protocols")
    assert validate_protocol(str(WITH_TESTS / "protocol.md"), str(WITH_TESTS.parent))
    assert "2 tests under tests/ conform" in capsys.readouterr().out


def test_load_test_case_reports_missing_test_yaml(tmp_path):
    (tmp_path / "empty").mkdir()
    case, errors = load_test_case(tmp_path / "empty")
    assert case is None and "no test.yaml" in errors[0]


# ---------------------------------------------------------------------------
# Checker, end to end in a throwaway git repository
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    """A git repository holding the with-tests fixture, committed."""
    root = tmp_path / "repo"
    shutil.copytree(FIXTURES / "valid" / "with-tests", root)
    git = lambda *a: subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)  # noqa: E731
    git("init", "-q")
    git("config", "user.email", "t@example.org")
    git("config", "user.name", "t")
    git("add", "-A")
    git("commit", "-qm", "fixture")
    return root


def write_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def executor(results: Path, **extra):
    data = {"started": "2026-10-20T04:30:00Z", "finished": "2026-10-20T04:31:00Z",
            "executor": {"agent": "pytest", "invocation": {"kind": "in-context"}}}
    data.update(extra)
    write_yaml(results / "executor.yaml", data)


def passing_results(results: Path):
    write_yaml(results / "basic" / "result.yaml", {
        "summary": {"A": 1, "B": 3, "C": 6.5, "D": 10}, "n_eligible": 4, "m": 2, "cutoff": 3.0,
        "removed_features": ["A", "B"], "retained_matrix": {"path": "retained.csv"}, "extra": "ignored",
    })
    (results / "basic" / "retained.csv").write_text("feature,sample_1,sample_2\nC,5,8.0\nD,10,10\n")
    write_yaml(results / "orientation" / "result.yaml", {
        "outcome": "orientation_corrected", "observation": "Transposed the input.",
        "removed_features": ["A", "B"], "retained_features": ["C", "D"],
        "retained_matrix": {"path": "kept.csv"},
    })
    (results / "orientation" / "kept.csv").write_text("feature,s1,s2\nC,5,8\nD,10,10\n")


def shape(repo, results, capsys, *extra):
    tests = repo / "protocols" / "example-protocol" / "tests"
    rc = checker.main(["--shape", str(tests), str(results), *extra])
    return rc, yaml.safe_load(capsys.readouterr().out)


def test_shape_withholds_values_and_nested_keys(repo, tmp_path, capsys):
    results = tmp_path / "results"
    rc, out = shape(repo, results, capsys)
    assert rc == 0
    basic = next(t for t in out["tests"] if t["name"] == "basic")
    assert basic["result"]["summary"] == {"<key>": "number"}
    assert basic["result"]["n_eligible"] == "number"
    assert basic["result"]["removed_features"] == "list"
    assert basic["result"]["retained_matrix"] == {"file": "csv", "header": ["feature", "sample_1", "sample_2"]}
    orient = next(t for t in out["tests"] if t["name"] == "orientation")
    present = orient["accepted_outcomes"][0]["expected_present"]
    assert present["retained_matrix"]["header"] == "withheld"
    assert orient["accepted_outcomes"][1]["expected_absent"] == ["removed_features", "retained_features", "retained_matrix"]
    text = yaml.safe_dump(out)
    assert "6.5" not in text and '"A"' not in text and "- A\n" not in text
    source = yaml.safe_load((results / "source.yaml").read_text())
    assert source["uncommitted"] is False and len(source["protocol_commit"]) == 7
    assert source["source_digest"].startswith("sha256:")


def test_shape_refuses_non_empty_and_inside_protocol(repo, tmp_path, capsys):
    results = tmp_path / "results"
    assert shape(repo, results, capsys)[0] == 0
    assert checker.main(["--shape", str(repo / "protocols/example-protocol/tests"), str(results)]) == 2
    assert checker.main(["--shape", str(repo / "protocols/example-protocol/tests"),
                         str(repo / "protocols/example-protocol/out")]) == 2


def test_shape_on_dirty_checkout_records_no_commit(repo, tmp_path, capsys):
    (repo / "protocols/example-protocol/protocol.md").open("a").write("\n<!-- edited -->\n")
    results = tmp_path / "results"
    assert shape(repo, results, capsys)[0] == 0
    source = yaml.safe_load((results / "source.yaml").read_text())
    assert source["uncommitted"] is True and source["protocol_commit"] is None


def test_check_passes_and_writes_run_record(repo, tmp_path, capsys):
    results = tmp_path / "results"
    tests = repo / "protocols/example-protocol/tests"
    assert shape(repo, results, capsys)[0] == 0
    passing_results(results)
    executor(results, condition="B")
    assert checker.main([str(tests), str(results)]) == 0
    out = capsys.readouterr().out
    assert "[PASS   ] basic" in out and "orientation (orientation_corrected)" in out
    record = yaml.safe_load((results / "run.yaml").read_text())
    assert record["run_record"] == 1
    assert record["protocol"] == "example-protocol" and record["version"] == "1.1.0"
    assert record["checker"].startswith("check_test_result.py ")
    assert record["condition"] == "B"
    assert record["executor"]["agent"] == "pytest"
    assert [t["result"] for t in record["tests"]] == ["pass", "pass"]
    assert record["tests"][1]["outcome"] == "orientation_corrected"


def test_check_reports_failures(repo, tmp_path, capsys):
    results = tmp_path / "results"
    tests = repo / "protocols/example-protocol/tests"
    shape(repo, results, capsys)
    passing_results(results)
    executor(results)
    r = yaml.safe_load((results / "basic/result.yaml").read_text())
    r["summary"]["E"] = 1              # extra nested key is a wrong answer
    del r["m"]                         # missing top-level key fails
    r["cutoff"] = 3.5                  # out of tolerance
    write_yaml(results / "basic/result.yaml", r)
    (results / "basic/retained.csv").write_text("feature,sample_1,sample_2\nC,5,8.1\nD,10,10\n")
    assert checker.main([str(tests), str(results)]) == 1
    out = capsys.readouterr().out
    assert "unexpected keys ['E']" in out
    assert "m: missing" in out
    assert "cutoff: 3.5" in out
    assert "row 1 column 'sample_2': '8.1'" in out
    record = yaml.safe_load((results / "run.yaml").read_text())
    assert record["tests"][0]["result"] == "fail" and len(record["tests"][0]["failures"]) == 4


def test_check_diagnostic_rules(repo, tmp_path, capsys):
    results = tmp_path / "results"
    tests = repo / "protocols/example-protocol/tests"
    shape(repo, results, capsys)
    executor(results)
    write_yaml(results / "orientation/result.yaml",
               {"outcome": "refused_for_orientation", "observation": "Features are in columns."})
    assert checker.main(["--test", "orientation", str(tests), str(results)]) == 0
    # a refusal that still produced outputs fails
    write_yaml(results / "orientation/result.yaml",
               {"outcome": "refused_for_orientation", "observation": "x", "retained_features": ["C", "D"]})
    assert checker.main(["--test", "orientation", str(tests), str(results)]) == 1
    assert "requires it absent" in capsys.readouterr().out
    # an unknown label or a missing observation fails
    write_yaml(results / "orientation/result.yaml", {"outcome": "gave_up"})
    assert checker.main(["--test", "orientation", str(tests), str(results)]) == 1
    out = capsys.readouterr().out
    assert "not one of the accepted outcomes" in out and "observation: missing" in out


def test_check_not_run_is_neither(repo, tmp_path, capsys):
    results = tmp_path / "results"
    tests = repo / "protocols/example-protocol/tests"
    shape(repo, results, capsys)
    passing_results(results)
    shutil.rmtree(results / "orientation")
    executor(results)
    assert checker.main([str(tests), str(results)]) == 0
    record = yaml.safe_load((results / "run.yaml").read_text())
    assert [t["result"] for t in record["tests"]] == ["pass", "not_run"]


def test_check_refuses_changed_source_and_bad_executor(repo, tmp_path, capsys):
    results = tmp_path / "results"
    tests = repo / "protocols/example-protocol/tests"
    shape(repo, results, capsys)
    passing_results(results)
    assert checker.main([str(tests), str(results)]) == 2          # no executor.yaml
    executor(results, protocol_commit="abc1234")
    assert checker.main([str(tests), str(results)]) == 2          # reserved key
    executor(results)
    (repo / "protocols/example-protocol/protocol.md").open("a").write("\n<!-- edited -->\n")
    assert checker.main([str(tests), str(results)]) == 2          # digest changed
    assert not (results / "run.yaml").exists()


def test_table_rules(tmp_path):
    exp = tmp_path / "exp.csv"
    act = tmp_path / "act.csv"
    exp.write_text("id,x,label\n001,1.0,a\n002,,b\n")
    act.write_text("id,x,label\n001,1.0000001,a\n002,,b\n")
    assert checker.compare_table(exp, act, 1e-6, "t") == []
    act.write_text("id,x,label\n1,1.0,a\n002,,b\n")               # identifier column is a string
    assert "'1', expected '001'" in checker.compare_table(exp, act, 1e-6, "t")[0]
    act.write_text("id,x,label\n001,1.0,a\n002,0,b\n")              # empty cell matches only empty
    assert checker.compare_table(exp, act, 1e-6, "t")
    act.write_text("x,id,label\n1.0,001,a\n,002,b\n")               # header order matters
    assert "header" in checker.compare_table(exp, act, 1e-6, "t")[0]
    act.write_text("id,x,label\n001,1.0,a\n")                       # row count
    assert "data rows" in checker.compare_table(exp, act, 1e-6, "t")[0]


def test_nan_never_passes(tmp_path):
    cv = lambda e, a, tol=0: checker.compare_value(e, a, tol, "k", tmp_path, tmp_path, tmp_path)  # noqa: E731
    assert cv(3, float("nan")) and cv(3, float("nan"), 1e9)
    exp = tmp_path / "exp.csv"
    act = tmp_path / "act.csv"
    exp.write_text("id,x\n001,3\n")
    act.write_text("id,x\n001,NaN\n")
    assert checker.compare_table(exp, act, 1e9, "t")


def test_malformed_executor_is_a_contract_error(repo, tmp_path, capsys):
    results = tmp_path / "results"
    tests = repo / "protocols/example-protocol/tests"
    shape(repo, results, capsys)
    passing_results(results)
    (results / "executor.yaml").write_text("executor: [unclosed\n")
    assert checker.main([str(tests), str(results)]) == 2


def test_shape_section_named_path(tmp_path, capsys):
    """A top-level key called `path` is a parameter, not a file slot."""
    case = ProtocolTest(**exact_case(expected_outputs={"path": "out", "n": 1}))
    s = checker.shape_of(case, tmp_path, tmp_path)
    assert s["result"] == {"path": "string", "n": "number"}


def test_cached_remote_file_is_verified(tmp_path, monkeypatch):
    from scripts.models import FileRef
    data = b"id,x\n001,1\n"
    import hashlib
    digest = hashlib.sha256(data).hexdigest()
    ref = FileRef(url="https://example.org/t.csv", sha256=digest)
    results = tmp_path / "results"
    cache = results / checker.CACHE_DIR
    cache.mkdir(parents=True)
    (cache / f"{digest}.csv").write_bytes(b"id,x\n001,999\n")      # tampered cache
    calls = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            calls.append(1)
            return data

    monkeypatch.setattr(checker.urllib.request, "urlopen", lambda url: Resp())
    path = checker.resolve_expected_file(tmp_path, results, ref)
    assert path.read_bytes() == data and calls == [1]        # re-downloaded, not trusted
    checker.resolve_expected_file(tmp_path, results, ref)
    assert calls == [1]                                        # good cache reused


def test_nested_file_slot_rejected():
    with pytest.raises(ValidationError, match="direct value of inputs"):
        ProtocolTest(**exact_case(inputs={"files": {"a": {"path": "input.csv"}}}))
    with pytest.raises(ValidationError, match="direct value of expected_outputs"):
        ProtocolTest(**exact_case(expected_outputs={"tables": [{"path": "out.csv"}]}))


def test_shape_refusal_creates_nothing(repo, tmp_path, capsys):
    inside = repo / "protocols/example-protocol/results"
    assert checker.main(["--shape", str(repo / "protocols/example-protocol/tests"), str(inside)]) == 2
    assert not inside.exists()


def test_table_width_and_precision(tmp_path):
    exp, act = tmp_path / "exp.csv", tmp_path / "act.csv"
    exp.write_text("id,x\n001,9007199254740993\n")
    act.write_text("id,x\n001,9007199254740992\n")           # adjacent integers beyond float precision
    assert checker.compare_table(exp, act, 0, "t")
    act.write_text("id,x\n001,9007199254740993\n")
    assert checker.compare_table(exp, act, 0, "t") == []
    act.write_text("id,x\n001\n")                           # ragged actual row is a failure
    assert "malformed" in checker.compare_table(exp, act, 0, "t")[0]
    act.write_text("")                                       # empty actual file is a failure
    assert "malformed" in checker.compare_table(exp, act, 0, "t")[0]
    exp.write_text("id,x\n001,1,2\n")                       # ragged expected row is a broken test
    act.write_text("id,x\n001,1\n")
    with pytest.raises(checker.ContractError):
        checker.compare_table(exp, act, 0, "t")


def test_result_symlink_outside_results_fails(repo, tmp_path, capsys):
    results = tmp_path / "results"
    tests = repo / "protocols/example-protocol/tests"
    shape(repo, results, capsys)
    passing_results(results)
    executor(results)
    (results / "basic/retained.csv").unlink()
    (results / "basic/retained.csv").symlink_to(tests / "basic/retained.csv")
    assert checker.main(["--test", "basic", str(tests), str(results)]) == 1
    assert "resolves outside" in capsys.readouterr().out


def test_timestamps_must_carry_a_timezone(repo, tmp_path, capsys):
    results = tmp_path / "results"
    tests = repo / "protocols/example-protocol/tests"
    shape(repo, results, capsys)
    passing_results(results)
    executor(results, started="2026-10-20")
    assert checker.main([str(tests), str(results)]) == 2
    executor(results, started="2026-10-20T06:30:00+02:00")
    assert checker.main([str(tests), str(results)]) == 0
    record = yaml.safe_load((results / "run.yaml").read_text())
    assert record["started"] == "2026-10-20T04:30:00Z"


def test_shape_downloads_and_verifies_remote_inputs(repo, tmp_path, capsys, monkeypatch):
    import hashlib
    data = b"feature,s1\nA,1\n"
    digest = hashlib.sha256(data).hexdigest()
    test_yaml = repo / "protocols/example-protocol/tests/basic/test.yaml"
    t = yaml.safe_load(test_yaml.read_text())
    t["inputs"]["data"] = {"url": "https://example.org/input.csv", "sha256": digest}
    test_yaml.write_text(yaml.safe_dump(t))

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return data

    monkeypatch.setattr(checker.urllib.request, "urlopen", lambda url: Resp())
    results = tmp_path / "results"
    rc, out = shape(repo, results, capsys, "--test", "basic")
    assert rc == 0
    given = out["tests"][0]["inputs"]["data"]
    assert given["url"] == "https://example.org/input.csv"
    assert Path(given["path"]).read_bytes() == data
    assert Path(given["path"]).resolve().is_relative_to(results.resolve())
    # a digest mismatch refuses before anything is executed
    t["inputs"]["data"]["sha256"] = "0" * 64
    test_yaml.write_text(yaml.safe_dump(t))
    assert checker.main(["--shape", str(repo / "protocols/example-protocol/tests"), str(tmp_path / "r2"), "--test", "basic"]) == 2


def test_mixed_int_float_precision(tmp_path):
    cv = lambda e, a, tol=0: checker.compare_value(e, a, tol, "k", tmp_path, tmp_path, tmp_path)  # noqa: E731
    assert cv(9007199254740993, 9007199254740992.0)
    assert cv(9007199254740993, 9007199254740993) == []


def test_unterminated_quote_is_malformed(tmp_path):
    exp, act = tmp_path / "exp.csv", tmp_path / "act.csv"
    exp.write_text("id,x\n001,3\n")
    act.write_text('id,x\n001,"3')
    assert "malformed" in checker.compare_table(exp, act, 0, "t")[0]


def test_symlinks_in_source_and_results_are_refused(repo, tmp_path, capsys):
    tests = repo / "protocols/example-protocol/tests"
    real = tmp_path / "elsewhere"
    shutil.copytree(tests / "basic", real)
    (tests / "linked").symlink_to(real)
    assert checker.main(["--shape", str(tests), str(tmp_path / "r1")]) == 2
    (tests / "linked").unlink()
    results = tmp_path / "results"
    shape(repo, results, capsys)
    old = tmp_path / "old-run"
    passing_results(old)
    passing_results(results)
    shutil.rmtree(results / "basic")
    (results / "basic").symlink_to(old / "basic")
    executor(results)
    assert checker.main(["--test", "basic", str(tests), str(results)]) == 1
    assert "symlink" in capsys.readouterr().out


def test_contract_errors_exit_2(repo, tmp_path, capsys):
    tests = repo / "protocols/example-protocol/tests"
    results = tmp_path / "results"
    shape(repo, results, capsys)
    (results / "source.yaml").write_text("- not a mapping\n")
    passing_results(results)
    executor(results)
    assert checker.main([str(tests), str(results)]) == 2
    (repo / "protocols/example-protocol/protocol.md").write_text("---\nname: [unclosed\n---\n")
    assert checker.main(["--shape", str(tests), str(tmp_path / "r2")]) == 2


def test_remote_input_path_is_absolute_for_relative_results_dir(repo, tmp_path, capsys, monkeypatch):
    import hashlib
    data = b"feature,s1\nA,1\n"
    test_yaml = repo / "protocols/example-protocol/tests/basic/test.yaml"
    t = yaml.safe_load(test_yaml.read_text())
    t["inputs"]["data"] = {"url": "https://example.org/input.csv", "sha256": hashlib.sha256(data).hexdigest()}
    test_yaml.write_text(yaml.safe_dump(t))

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return data

    monkeypatch.setattr(checker.urllib.request, "urlopen", lambda url: Resp())
    monkeypatch.chdir(tmp_path)
    rc = checker.main(["--shape", str(repo / "protocols/example-protocol/tests"), "rel-results", "--test", "basic"])
    assert rc == 0
    out = yaml.safe_load(capsys.readouterr().out)
    assert Path(out["tests"][0]["inputs"]["data"]["path"]).is_absolute()


def test_url_validation_and_name():
    from scripts.models import FileRef
    d = "a" * 64
    for bad in ("https:///input.csv", "https://example.org:nope/input.csv", "ftp://example.org/x.csv"):
        with pytest.raises(ValidationError):
            FileRef(url=bad, sha256=d)
    ref = FileRef(url="https://example.org/expected.csv?token=a/b", sha256=d)
    assert ref.name == "expected.csv" and ref.is_table


def test_unsupported_expectation_types_rejected():
    import datetime
    with pytest.raises(ValidationError, match="unsupported value of type date"):
        ProtocolTest(**exact_case(expected_outputs={"day": datetime.date(2026, 10, 18)}))
    with pytest.raises(ValidationError, match="unsupported value"):
        ProtocolTest(**{"name": "d", "description": "x", "inputs": {},
                        "evaluation": {"mode": "diagnostic", "accepted_outcomes": [
                            {"outcome": "r", "expected_outputs": {"when": [datetime.datetime(2026, 1, 1)]}}]}})


def test_tolerance_boundary_is_exact(tmp_path):
    exp, act = tmp_path / "exp.csv", tmp_path / "act.csv"
    exp.write_text("id,x\n001,0\n")
    act.write_text("id,x\n001,1.0000000000000000000000000001e-12\n")
    assert checker.compare_table(exp, act, 1e-12, "t")          # just outside
    act.write_text("id,x\n001,1e-12\n")
    assert checker.compare_table(exp, act, 1e-12, "t") == []    # on the boundary


def test_ignored_input_is_uncommitted(repo, tmp_path, capsys):
    (repo / ".gitignore").write_text("*.secret\n")
    subprocess.run(["git", "-C", str(repo), "add", ".gitignore"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "ignore"], check=True)
    (repo / "protocols/example-protocol/tests/basic/extra.secret").write_text("x")
    results = tmp_path / "results"
    assert shape(repo, results, capsys)[0] == 0
    source = yaml.safe_load((results / "source.yaml").read_text())
    assert source["uncommitted"] is True and source["protocol_commit"] is None


def test_symlinked_result_yaml_fails(repo, tmp_path, capsys):
    tests = repo / "protocols/example-protocol/tests"
    results = tmp_path / "results"
    shape(repo, results, capsys)
    old = tmp_path / "old"
    passing_results(old)
    passing_results(results)
    (results / "basic/result.yaml").unlink()
    (results / "basic/result.yaml").symlink_to(old / "basic/result.yaml")
    executor(results)
    assert checker.main(["--test", "basic", str(tests), str(results)]) == 1
    assert "symlink" in capsys.readouterr().out


def test_parameter_named_path_does_not_shield_siblings():
    import datetime
    with pytest.raises(ValidationError, match="unsupported value of type date"):
        ProtocolTest(**exact_case(expected_outputs={"path": "literal", "day": datetime.date(2026, 10, 18)}))


def test_checker_rejects_stray_files_and_symlinked_tests_root(repo, tmp_path, capsys):
    tests = repo / "protocols/example-protocol/tests"
    (tests / "README.md").write_text("notes\n")
    assert checker.main(["--shape", str(tests), str(tmp_path / "r1")]) == 2
    (tests / "README.md").unlink()
    real = tmp_path / "real-tests"
    shutil.move(str(tests), str(real))
    tests.symlink_to(real)
    assert checker.main(["--shape", str(tests), str(tmp_path / "r2")]) == 2


def test_undownloadable_url_is_a_contract_error(tmp_path):
    from scripts.models import FileRef
    ref = FileRef(url="https://example.org/my input.csv", sha256="a" * 64)
    with pytest.raises(checker.ContractError, match="could not download"):
        checker.resolve_expected_file(tmp_path, tmp_path / "results", ref)


def test_compare_value_scalars(tmp_path):
    cv = lambda e, a, tol=0: checker.compare_value(e, a, tol, "k", tmp_path, tmp_path, tmp_path)  # noqa: E731
    assert cv(1, 1.0) == []
    assert cv(True, 1)                   # a boolean is not a number
    assert cv(1, True)
    assert cv(None, None) == [] and cv(None, "null")
    assert cv("a", "a") == [] and cv("a", "b")
    assert cv([1, 2], [1, 2]) == [] and cv([1, 2], [2, 1])
    assert cv(1.0, 1.05, 0.1) == [] and cv(1.0, 1.2, 0.1)
