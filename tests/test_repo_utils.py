import pytest
from scripts.repo_utils import parse_repository_url

def test_parse_repository_url():
    valid = [
        "https://github.com/owner/name.git",
        "https://github.com/owner/name",
        "git@github.com:owner/name.git",
        "git@github.com:owner/name",
        "https://github.com/owner/name.git/",
        "https://github.com/owner/name/",
        "http://github.com/owner/name"
    ]
    for url in valid:
        assert parse_repository_url(url) == "owner/name"
        
    invalid = [
        "",
        "/tmp/protocols",
        "file:///tmp/protocols",
        "owner/name",
        "https://github.com/owner"
    ]
    for url in invalid:
        assert parse_repository_url(url) is None
