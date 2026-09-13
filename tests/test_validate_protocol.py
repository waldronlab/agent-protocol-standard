import pytest
from scripts.validate_protocol import validate_protocol, extract_frontmatter
from pathlib import Path
import re

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _matches_expected_diagnostic(expected: str, output: str) -> bool:
    if expected in output:
        return True
    alt = (
        expected.replace("must be one of", "Input should be")
        .replace("must be either", "Input should be")
    )
    if alt in output:
        return True
    quoted = re.findall(r"'([^']+)'", expected)
    if quoted and all(f"'{token}'" in output for token in quoted):
        return True
    expected_words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", expected.lower()) if len(w) >= 4]
    output_lower = output.lower()
    matches = sum(1 for w in expected_words if w in output_lower)
    return matches >= min(2, len(expected_words))

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

def test_template():
    template_dir = Path(__file__).parent.parent / "template" / "protocols"
    if template_dir.exists():
        protocol_files = list(template_dir.rglob("protocol.md"))
        for p in protocol_files:
            assert not validate_protocol(str(p), str(template_dir))


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
