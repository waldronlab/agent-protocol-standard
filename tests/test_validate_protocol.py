import pytest
from scripts.validate_protocol import validate_protocol
import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

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

def test_invalid_fixtures():
    invalid_dir = FIXTURES_DIR / "invalid"
    if not invalid_dir.exists():
        pytest.skip("Fixtures dir not found")
        
    for fixture in invalid_dir.iterdir():
        if fixture.is_dir():
            protocol_files = list(fixture.rglob("protocol.md"))
            for p in protocol_files:
                # Should fail
                assert not validate_protocol(str(p), str(fixture / "protocols")), f"Expected {p} to fail validation"

def test_template():
    template_dir = Path(__file__).parent.parent / "template" / "protocols"
    if template_dir.exists():
        protocol_files = list(template_dir.rglob("protocol.md"))
        for p in protocol_files:
            assert not validate_protocol(str(p), str(template_dir))
