"""check_citations.py over every valid fixture protocol, with output built from its frontmatter.

For each protocol, the correct output must pass; each way of breaking it that #62 names
must fail the check that names it. This is what makes the checker's verdict trustworthy:
it is exercised on every shape of protocol the standard defines (atomic, composite, first
definition, PMID origin, no origin), not only on hand-picked examples.
"""
import re
from pathlib import Path

import pytest

from scripts import check_citations as cc

FIXTURES = Path(__file__).parent / "fixtures" / "valid"
PROTOCOLS = sorted(p for p in FIXTURES.glob("*/protocols/*") if (p / "protocol.md").is_file())
REPO = "example-org/example-protocols"


def canonical(fm, deps):
    """The output `protocol-runner` should give for this protocol."""
    n = cc.normalize
    col, art, pub = fm.get("collection_doi"), fm.get("artifact_doi"), fm.get("protocol_citation")
    first = pub and n(pub) in {n(col) if col else None, n(art) if art else None}
    l1 = [f"Following: A Author \"{fm['name']}\"",
          f"Repository: {REPO}, protocol: {fm['name']} v{fm['version']} ({fm['date']})"]
    if col:
        l1.append(f"Repository DOI: {col}")
    if art:
        l1.append(f"Protocol DOI: {art}")
    if pub and not first:
        l1.append(f"Publication DOI: {pub}")
    l1.append(f"License: {fm['license']}")
    origins = list(dict.fromkeys(str(d["method_origin_citation"]) for d in deps
                                 if d.get("method_origin_citation")))
    own = fm.get("method_origin_citation")
    block = "## Method Provenance\n\n### Protocol Citation (Level 1)\n" + "\n".join(l1) + "\n"
    if origins or own:
        items = [f"- {x}" for x in origins]
        if own:
            items.append(f"- {own}" + (" (the composition's own method)"
                                       if fm.get("type") == "composite" else ""))
        block += ("\n### Primary Literature to Cite (Level 2)\nThis protocol implements methods "
                  "from:\n" + "\n".join(items) + "\n")
    cited = origins + ([str(own)] if own else [])
    attribution = art or col
    methods = ("\n## Draft Methods Section\n"
               + ("Methods followed " + " and ".join(f"(DOI: {x})" for x in cited) + ".\n\n"
                  if cited else "Done.\n\n")
               + f"Computational analysis was automated using the AI Agent Protocol "
                 f"`{fm['name']}` (v{fm['version']}"
               + (f", DOI: {attribution}" if attribution else "")
               + f") from `{REPO}`.\n\nSkill executed: protocol-runner v2.2.0\n")
    return block, methods, origins, own, first


def failing(protocol, text):
    _, results = cc.check(str(protocol), text, protocols_dir=str(protocol.parent))
    return {r["check"] for r in results if r["result"] == "fail"}


@pytest.fixture(params=PROTOCOLS, ids=lambda p: p.parent.parent.name)
def case(request):
    path = request.param
    fm = cc.load_protocol(path)
    deps = cc.resolve_dependencies(fm, str(path.parent))
    block, methods, origins, own, first = canonical(fm, deps)
    return path, fm, block, methods, origins, own, first


def test_correct_output_passes(case):
    path, fm, block, methods, *_ = case
    assert failing(path, block + methods) == set()


def test_correct_output_passes_in_the_shapes_agents_use(case):
    path, fm, block, methods, *_ = case
    assert failing(path, "Some text.\n\n```markdown\n" + block + "```\n" + methods) == set()
    as_links = re.sub(r"(10\.\d{4,9}/[^\s)]+)", r"[\1](https://doi.org/\1)", block + methods)
    assert failing(path, as_links) == set()


def test_no_block_fails(case):
    path, _, _, methods, *_ = case
    assert "block_present" in failing(path, methods)


def test_wrong_version_or_name_fails(case):
    path, fm, block, methods, *_ = case
    text = (block + methods).replace(f"v{fm['version']} (", "v9.9.9 (", 1)
    assert "level1_protocol_version" in failing(path, text)
    text = (block + methods).replace(f"protocol: {fm['name']}", "protocol: other", 1)
    assert "level1_protocol_version" in failing(path, text)


def test_dropped_repository_doi_fails(case):
    path, fm, block, methods, *_ = case
    if not fm.get("collection_doi"):
        pytest.skip("no collection_doi")
    assert "level1_repository_doi" in failing(path, re.sub(r"Repository DOI:.*\n", "", block) + methods)


def test_invented_doi_fails_wherever_it_is(case):
    path, fm, block, methods, *_ = case
    fake = "10.9999/invented"
    assert "block_no_unknown" in failing(path, block.replace("License:", f"Notes: {fake}\nLicense:") + methods)
    assert "text_no_unknown" in failing(path, block + methods + f"\nSee also {fake}.\n")
    assert "text_no_unknown" in failing(path, methods + f"\nSee {fake}.\n")  # no block, unknown still seen
    assert failing(path, f"I did the analysis (DOI: {fake}).") >= {"block_present", "text_no_unknown"}


def test_wrong_license_fails(case):
    path, fm, block, methods, *_ = case
    assert "level1_license" in failing(path, (block + methods).replace(f"License: {fm['license']}", "License: MIT"))


def test_level2_must_match_the_method_origins(case):
    path, fm, block, methods, origins, own, first = case
    everything = origins + ([str(own)] if own else [])
    if everything:
        no_l2 = block.split("\n### Primary")[0] + "\n" + methods
        assert "level2_heading" in failing(path, no_l2)
        target = everything[0]
        assert "level2_complete" in failing(path, (block + methods).replace(f"- {target}", "- (none)", 1))
        assert "methods_cites_level2" in failing(path, block + methods.replace(f"(DOI: {target})", ""))
    else:
        invented = block + "\n### Primary Literature to Cite (Level 2)\n- 10.9999/invented\n" + methods
        assert "level2_absent" in failing(path, invented)
        assert "level2_absent" in failing(path, block + "\n### Primary Literature to Cite (Level 2)\nNone.\n" + methods)


def test_attribution_sentence(case):
    path, fm, block, methods, *_ = case
    assert "methods_attribution" in failing(path, block + methods.split("Computational analysis")[0])
    doi = fm.get("artifact_doi") or fm.get("collection_doi")
    if doi:
        assert "methods_attribution" in failing(path, block + methods.replace(f"DOI: {doi}", "DOI: 10.9999/invented"))
    else:
        assert "methods_attribution" in failing(path, block + methods.replace(") from", ", DOI: N/A) from"))


def test_first_definition_must_not_repeat_its_doi_as_publication(case):
    path, fm, block, methods, _, _, first = case
    if not first:
        pytest.skip("not a first definition")
    text = block.replace("License:", f"Publication DOI: {fm['protocol_citation']}\nLicense:") + methods
    assert "level1_publication_doi" in failing(path, text)


def test_composite_own_method_origin_must_be_labelled(case):
    path, fm, block, methods, _, own, _ = case
    if fm.get("type") != "composite" or not own:
        pytest.skip("not a composite with its own method origin")
    assert "level2_composite_own_labelled" in failing(path, (block + methods).replace(" (the composition's own method)", ""))
