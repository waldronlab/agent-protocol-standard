import pytest
from scripts.repo_utils import parse_repository_url, detect_repository, detect_ref

def test_parse_repository_url():
    valid = [
        "https://github.com/owner/name.git",
        "https://github.com/owner/name",
        "git@github.com:owner/name.git",
        "git@github.com:owner/name",
        "https://github.com/owner/name.git/",
        "https://github.com/owner/name/",
        "http://github.com/owner/name",
        "ssh://git@github.com/owner/name.git",
        "git@gitlab.com:owner/name.git",
        "https://x-access-token:v1.12345@github.com/owner/name.git",
        "  https://github.com/owner/name.git  "
    ]
    for url in valid:
        assert parse_repository_url(url) == "owner/name"
        
    invalid = [
        "",
        "/tmp/protocols",
        "file:///tmp/protocols",
        "owner/name",
        "https://github.com/owner",
        "https://github.com/owner/name/extra"
    ]
    for url in invalid:
        assert parse_repository_url(url) is None


def test_detect_repository_prefers_env(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/from-env")
    assert detect_repository() == "owner/from-env"


def test_detect_repository_falls_back_to_git_remote(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    class Completed:
        stdout = "https://github.com/owner/from-git.git\n"

    def fake_run(*args, **kwargs):
        return Completed()

    monkeypatch.setattr("scripts.repo_utils.subprocess.run", fake_run)
    assert detect_repository() == "owner/from-git"


def test_detect_ref_pull_request_uses_base_ref(monkeypatch):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    assert detect_ref() == "main"


def test_detect_ref_push_uses_ref_name(monkeypatch):
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.setenv("GITHUB_REF_NAME", "feature-branch")
    assert detect_ref() == "feature-branch"


def test_detect_ref_default_is_main(monkeypatch):
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.delenv("GITHUB_REF_NAME", raising=False)
    assert detect_ref() == "main"
