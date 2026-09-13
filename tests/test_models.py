import pytest
from pydantic import ValidationError
from datetime import date
from scripts.models import ProtocolFrontmatter, Author

def valid_dict():
    return {
        "name": "valid-protocol",
        "description": "A valid protocol.",
        "version": "1.0.0",
        "authors": [{"name": "Jane Doe"}],
        "date": date(2026, 8, 8),
        "status": "draft",
        "protocol_citation": "10.1234/abcd"
    }

def test_valid_protocol():
    proto = ProtocolFrontmatter(**valid_dict())
    assert proto.name == "valid-protocol"

def test_missing_required():
    d = valid_dict()
    del d["name"]
    with pytest.raises(ValidationError):
        ProtocolFrontmatter(**d)

def test_invalid_name_kebab():
    d = valid_dict()
    d["name"] = "Invalid_Name"
    with pytest.raises(ValidationError):
        ProtocolFrontmatter(**d)

def test_authors_list():
    d = valid_dict()
    d["authors"] = []
    with pytest.raises(ValidationError):
        ProtocolFrontmatter(**d)

def test_invalid_citation():
    d = valid_dict()
    d["protocol_citation"] = "not-a-doi"
    with pytest.raises(ValidationError):
        ProtocolFrontmatter(**d)

def test_template_placeholder():
    d = valid_dict()
    d["protocol_citation"] = "10.0000/replace-with-a-real-doi"
    with pytest.raises(ValidationError):
        ProtocolFrontmatter(**d)

def test_type_and_deps():
    d = valid_dict()
    d["type"] = "atomic"
    d["protocols_used"] = [{"name": "dep", "repository": "owner/repo", "version": "1.0.0"}]
    with pytest.raises(ValidationError):
        ProtocolFrontmatter(**d)
        
    d = valid_dict()
    d["type"] = "composite"
    d["protocols_used"] = []
    with pytest.raises(ValidationError):
        ProtocolFrontmatter(**d)


def test_explicit_null_type_rejected():
    d = valid_dict()
    d["type"] = None
    with pytest.raises(ValidationError):
        ProtocolFrontmatter(**d)


def test_explicit_null_method_origin_citation_rejected():
    d = valid_dict()
    d["method_origin_citation"] = None
    with pytest.raises(ValidationError):
        ProtocolFrontmatter(**d)
