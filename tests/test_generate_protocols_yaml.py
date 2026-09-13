import sys
from pathlib import Path

import pytest
import yaml

from scripts import generate_protocols_yaml


def write_protocol(path: Path, frontmatter: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n# Example Protocol\n", encoding="utf-8")


def test_generate_index_uses_detected_repository_ref_and_serializes_dates(tmp_path, monkeypatch):
    write_protocol(
        tmp_path / "protocols/example/protocol.md",
        "name: example\ndate: 2026-03-01\nreviews:\n  - name: Reviewer\n    date: 2026-02-01",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature-branch")
    monkeypatch.setattr(
        sys, "argv", ["generate_protocols_yaml.py", "protocols", "PROTOCOLS.yaml"]
    )

    generate_protocols_yaml.main()

    output = yaml.safe_load((tmp_path / "PROTOCOLS.yaml").read_text(encoding="utf-8"))
    protocol = output["protocols"][0]

    assert output["repository"] == "owner/repo"
    assert protocol["protocol_url"] == (
        "https://raw.githubusercontent.com/owner/repo/feature-branch/"
        "protocols/example/protocol.md"
    )
    assert protocol["date"] == "2026-03-01"
    assert protocol["reviews"][0]["date"] == "2026-02-01"


def test_generate_index_refuses_to_write_when_any_protocol_is_unreadable(tmp_path, monkeypatch):
    write_protocol(tmp_path / "protocols/ok/protocol.md", "name: ok\ndate: 2026-03-01")
    write_protocol(tmp_path / "protocols/bad/protocol.md", "name: [")

    output_path = tmp_path / "PROTOCOLS.yaml"
    output_path.write_text("sentinel\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature-branch")
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.setattr(
        sys, "argv", ["generate_protocols_yaml.py", "protocols", "PROTOCOLS.yaml"]
    )

    with pytest.raises(SystemExit, match="Refusing to write"):
        generate_protocols_yaml.main()

    assert output_path.read_text(encoding="utf-8") == "sentinel\n"


def test_generate_index_refuses_to_write_when_frontmatter_is_not_a_mapping(tmp_path, monkeypatch):
    write_protocol(tmp_path / "protocols/bad/protocol.md", "- item")

    output_path = tmp_path / "PROTOCOLS.yaml"
    output_path.write_text("sentinel\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature-branch")
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.setattr(
        sys, "argv", ["generate_protocols_yaml.py", "protocols", "PROTOCOLS.yaml"]
    )

    with pytest.raises(SystemExit, match="Refusing to write"):
        generate_protocols_yaml.main()

    assert output_path.read_text(encoding="utf-8") == "sentinel\n"


def test_generate_index_handles_non_mapping_reviews_items(tmp_path, monkeypatch):
    write_protocol(
        tmp_path / "protocols/example/protocol.md",
        "name: example\ndate: 2026-03-01\nreviews:\n  - date\n  - name: Reviewer\n    date: 2026-02-01",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature-branch")
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.setattr(
        sys, "argv", ["generate_protocols_yaml.py", "protocols", "PROTOCOLS.yaml"]
    )

    generate_protocols_yaml.main()

    output = yaml.safe_load((tmp_path / "PROTOCOLS.yaml").read_text(encoding="utf-8"))
    reviews = output["protocols"][0]["reviews"]
    assert reviews[0] == "date"
    assert reviews[1]["date"] == "2026-02-01"


def test_generate_index_exits_when_protocols_dir_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature-branch")
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.setattr(
        sys, "argv", ["generate_protocols_yaml.py", "protocols", "PROTOCOLS.yaml"]
    )
    with pytest.raises(SystemExit, match="No 'protocols' directory found"):
        generate_protocols_yaml.main()


def test_generate_index_exits_when_no_protocols_found(tmp_path, monkeypatch):
    (tmp_path / "protocols").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature-branch")
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    monkeypatch.setattr(
        sys, "argv", ["generate_protocols_yaml.py", "protocols", "PROTOCOLS.yaml"]
    )
    with pytest.raises(SystemExit, match="No 'protocol.md' files found"):
        generate_protocols_yaml.main()


def test_generate_index_exits_when_no_repository_detected(tmp_path, monkeypatch):
    write_protocol(tmp_path / "protocols/example/protocol.md", "name: example\ndate: 2026-03-01")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(
        sys, "argv", ["generate_protocols_yaml.py", "protocols", "PROTOCOLS.yaml"]
    )
    with pytest.raises(SystemExit, match="Could not determine which repository"):
        generate_protocols_yaml.main()
