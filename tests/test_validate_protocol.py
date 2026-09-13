import re
import sys
import subprocess
import pytest
import yaml
from scripts.validate_protocol import validate_protocol, extract_frontmatter
from pathlib import Path


FIXTURES_DIR = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _matches_expected_diagnostic(expected: str, output: str) -> bool:
    if expected in output:
        return True
        
    alt = (
        expected.replace("must be one of", "Input should be")
        .replace("must be either", "Input should be")
    )
    if alt in output:
        return True
        
    if ("malformed 'orcid'" in expected or "malformed ORCID" in expected) and "Malformed ORCID" in output:
        return True
        
    if "must be a single string" in expected and "Input should be a valid string" in output:
        return True
        
    if "must be an array" in expected and "Input should be a valid list" in output:
        return True
        
    if "missing required 'name' field" in expected and "Missing required fields: name" in output:
        return True
        
    if "missing required 'authors' field" in expected and "Missing required fields: authors" in output:
        return True

    required_field_match = re.match(r"'([^']+)' is required$", expected)
    if required_field_match and f"Missing required fields: {required_field_match.group(1)}" in output:
        return True
        
    if "must be a valid DOI or PMID" in expected and "String should match pattern" in output:
        return True
        
    if (
        expected == "'status' must be one of 'draft', 'stable', 'deprecated', 'superseded'"
        and "'status' Input should be 'draft', 'stable', 'deprecated' or 'superseded'" in output
    ):
        return True

    return False

@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "example-org/example-protocols")

def test_valid_fixtures():
    valid_dir = FIXTURES_DIR / "valid"
    if not valid_dir.exists():
        pytest.skip("Fixtures dir not found")
        
    for fixture in valid_dir.iterdir():
        if fixture.is_dir():
            protocol_files = list(fixture.rglob("protocol.md"))
            for p in protocol_files:
                assert validate_protocol(str(p), str(fixture / "protocols")), f"Failed on {p}"

def test_invalid_fixtures(capsys):
    invalid_dir = FIXTURES_DIR / "invalid"
    if not invalid_dir.exists():
        pytest.skip("Fixtures dir not found")
        
    for fixture in invalid_dir.iterdir():
        if fixture.is_dir():
            protocol_files = list(fixture.rglob("protocol.md"))
            for p in protocol_files:
                assert not validate_protocol(str(p), str(fixture / "protocols")), f"Expected {p} to fail validation"
                output = capsys.readouterr().out
                expected_path = fixture / "expected.txt"
                if expected_path.exists():
                    expected = expected_path.read_text(encoding="utf-8").strip()
                    assert _matches_expected_diagnostic(expected, output), (
                        f"Expected diagnostic not found for {p}: {expected}"
                    )

def test_template(capsys):
    template_dir = Path(__file__).parent.parent / "template" / "protocols"
    if template_dir.exists():
        protocol_files = list(template_dir.rglob("protocol.md"))
        for p in protocol_files:
            assert not validate_protocol(str(p), str(template_dir))
            output = capsys.readouterr().out
            assert "template placeholder" in output


def test_invalid_reviews_shape_does_not_crash(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "example-org/example-protocols")
    protocol_path = tmp_path / "protocols" / "example-protocol" / "protocol.md"
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    protocol_path.write_text(
        """---
name: example-protocol
description: Example protocol
version: 1.0.0
authors:
  - name: Ada Lovelace
date: 2026-03-01
status: draft
protocol_citation: "10.1000/example-procedure"
reviews: invalid
---

# Example Protocol

## Materials

- Item

## Steps

### Step 1: Do thing
Do thing.

## History & Reviews

### Version 1.0.0 (2026-03-01)

#### Changes
- Initial.

#### Reviews
*No reviews yet.*
""",
        encoding="utf-8",
    )
    assert not validate_protocol(str(protocol_path), str(tmp_path / "protocols"))
    output = capsys.readouterr().out
    assert "'reviews'" in output


@pytest.mark.parametrize("field", ["name", "description", "version", "date", "status", "protocol_citation"])
@pytest.mark.parametrize("bad_value", [None, ["bad"], {"bad": "value"}, 123, True])
def test_required_scalar_fields_reject_malformed_shapes(tmp_path, capsys, monkeypatch, field, bad_value):
    monkeypatch.setenv("GITHUB_REPOSITORY", "example-org/example-protocols")
    protocol_path = tmp_path / "protocols" / "example-protocol" / "protocol.md"
    protocol_path.parent.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        "name": "example-protocol",
        "description": "Example protocol",
        "version": "1.0.0",
        "authors": [{"name": "Ada Lovelace"}],
        "date": "2026-03-01",
        "status": "draft",
        "protocol_citation": "10.1000/example-procedure",
    }
    frontmatter[field] = bad_value

    protocol_path.write_text(
        "---\n"
        + yaml.safe_dump(frontmatter, sort_keys=False)
        + "---\n\n"
        + "# Example Protocol\n\n"
        + "## Materials\n\n- Item\n\n"
        + "## Steps\n\n### Step 1: Do thing\nDo thing.\n\n"
        + "## History & Reviews\n\n"
        + "### Version 1.0.0 (2026-03-01)\n\n"
        + "#### Changes\n- Initial.\n\n"
        + "#### Reviews\n*No reviews yet.*\n",
        encoding="utf-8",
    )

    assert not validate_protocol(str(protocol_path), str(tmp_path / "protocols"))
    output = capsys.readouterr().out
    assert f"'{field}'" in output or f"Missing required fields: {field}" in output


@pytest.mark.parametrize(
    ("field", "bad_value", "should_fail"),
    [
        ("authors", None, True),
        ("authors", "bad", True),
        ("authors", 123, True),
        ("authors", True, True),
        ("authors", {"bad": "value"}, True),
        ("protocols_used", None, False),
        ("protocols_used", "bad", True),
        ("protocols_used", 123, True),
        ("protocols_used", True, True),
        ("protocols_used", {"bad": "value"}, True),
        ("reviews", None, False),
        ("reviews", "bad", True),
        ("reviews", 123, True),
        ("reviews", True, True),
        ("reviews", {"bad": "value"}, True),
    ],
)
def test_container_fields_reject_malformed_shapes(
    tmp_path, capsys, monkeypatch, field, bad_value, should_fail
):
    monkeypatch.setenv("GITHUB_REPOSITORY", "example-org/example-protocols")
    protocol_path = tmp_path / "protocols" / "example-protocol" / "protocol.md"
    protocol_path.parent.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        "name": "example-protocol",
        "description": "Example protocol",
        "version": "1.0.0",
        "authors": [{"name": "Ada Lovelace"}],
        "date": "2026-03-01",
        "status": "draft",
        "protocol_citation": "10.1000/example-procedure",
    }
    frontmatter[field] = bad_value

    protocol_path.write_text(
        "---\n"
        + yaml.safe_dump(frontmatter, sort_keys=False)
        + "---\n\n"
        + "# Example Protocol\n\n"
        + "## Materials\n\n- Item\n\n"
        + "## Steps\n\n### Step 1: Do thing\nDo thing.\n\n"
        + "## History & Reviews\n\n"
        + "### Version 1.0.0 (2026-03-01)\n\n"
        + "#### Changes\n- Initial.\n\n"
        + "#### Reviews\n*No reviews yet.*\n",
        encoding="utf-8",
    )

    result = validate_protocol(str(protocol_path), str(tmp_path / "protocols"))
    output = capsys.readouterr().out
    if should_fail:
        assert not result
        assert f"'{field}'" in output
    else:
        assert result


def test_extract_frontmatter_does_not_treat_arbitrary_three_chars_as_terminator(tmp_path):
    protocol_path = tmp_path / "protocol.md"
    protocol_path.write_text(
        """---
name: example-protocol
description: abc
version: 1.0.0
authors:
  - name: Ada Lovelace
date: 2026-03-01
status: draft
protocol_citation: "10.1000/example-procedure"
---
""",
        encoding="utf-8",
    )
    fm = extract_frontmatter(str(protocol_path))
    assert isinstance(fm, dict)
    assert fm["protocol_citation"] == "10.1000/example-procedure"


def test_validate_protocol_cli_exits_when_protocols_dir_missing(tmp_path):
    missing_dir = tmp_path / "missing"
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_protocol.py"), str(missing_dir)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 1
    assert f"No '{missing_dir}' directory found" in result.stdout


def test_validate_protocol_cli_exits_when_no_protocols_found(tmp_path):
    empty_dir = tmp_path / "protocols"
    empty_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_protocol.py"), str(empty_dir)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 1
    assert "No 'protocol.md' files found" in result.stdout


def test_validate_protocol_cli_exits_nonzero_when_any_protocol_fails(tmp_path):
    protocol_path = tmp_path / "protocols" / "example-protocol" / "protocol.md"
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    protocol_path.write_text(
        """---
name: example-protocol
description: Example protocol
version: 1.0.0
authors:
  - name: Ada Lovelace
date: 2026-03-01
status: draft
protocol_citation: "10.1000/example-procedure"
---
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_protocol.py"), str(tmp_path / "protocols")],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 1
    assert "Validation failed for some protocols." in result.stdout
