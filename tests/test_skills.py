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


def _template_lines():
    _, body = read_skill("protocol-runner")
    fenced = re.search(r"```markdown\n(.*?)```", body, re.DOTALL)
    assert fenced and "## Method Provenance" in fenced.group(1), "provenance template not found"
    return [ln.strip() for ln in fenced.group(1).splitlines() if ln.strip()]


# The checks below read the skill's wording. They cannot show what an agent does with it;
# that was measured by running the skill, and is checked by scripts/check_citations.py.

def test_protocol_runner_template_omits_a_duplicate_publication_doi():
    # Step 5.1: a protocol_citation equal to artifact_doi or collection_doi is a first
    # definition, and the same DOI must not be cited twice. The template must say so for
    # both, so an agent following only the template cannot repeat either.
    line = next(ln for ln in _template_lines() if ln.startswith("Publication DOI:"))
    assert re.search(r"omit this line when it equals the Repository DOI or the Protocol DOI", line)


def test_protocol_runner_level2_heading_is_conditional_everywhere():
    # An unconditional "reproduce the Level 2 heading exactly" next to "omit it when there
    # is no method origin" lets an agent write an empty Level 2 section, which #62 case 2
    # forbids. Every place the heading is required must say when.
    _, body = read_skill("protocol-runner")
    exact = next(ln for ln in body.splitlines() if "Reproduce the template's headings" in ln)
    assert re.search(r"Level 2\)`[^.]*\bonly\b", exact), exact
    lines = _template_lines()
    heading = next(i for i, ln in enumerate(lines) if ln.startswith("### Primary Literature"))
    note = lines[heading - 1]
    assert "only when" in note and "method_origin_citation" in note and "Otherwise" in note, note
