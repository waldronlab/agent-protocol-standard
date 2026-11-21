"""Skills: what the tooling can hold constant about skills/*/SKILL.md."""
import re
from pathlib import Path

import yaml

SKILLS = Path(__file__).parent.parent / "skills"


def read_skill(name):
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    assert match, f"{name}: no frontmatter"
    return yaml.safe_load(match.group(1)), match.group(2)


def test_protocol_runner_states_its_version_in_the_body():
    # Agent software can strip frontmatter when it loads a skill, and the Skill
    # Execution Record must name the version, so the body repeats it. The two
    # must not drift apart.
    frontmatter, body = read_skill("protocol-runner")
    stated = re.search(r"\*\*Skill version: ([0-9][^*\s]*?)\.?\*\*", body)
    assert stated, "protocol-runner body does not state `**Skill version: X.**`"
    assert stated.group(1) == str(frontmatter["version"])


def test_protocol_runner_examples_cite_no_literal_doi():
    # Only DOIs from a protocol's frontmatter are ground truth (#62), so the
    # skill must not show an agent a DOI to copy.
    _, body = read_skill("protocol-runner")
    assert not re.findall(r"\b10\.\d{4,9}/[^\s`\"')\]]+", body)


def test_protocol_runner_template_omits_a_duplicate_publication_doi():
    # Step 5.1: a protocol_citation equal to artifact_doi or collection_doi is a first
    # definition, and the same DOI must not be cited twice. The template must say so for
    # both, so an agent following only the template cannot repeat either.
    _, body = read_skill("protocol-runner")
    line = next(ln for ln in body.splitlines() if ln.strip().startswith("Publication DOI:"))
    assert "Repository DOI" in line and "Protocol DOI" in line
