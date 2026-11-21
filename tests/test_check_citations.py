"""check_citations.py: an agent's Method Provenance block against the protocol's frontmatter."""
from pathlib import Path

import pytest

from scripts import check_citations as cc

VALID = Path(__file__).parent / "fixtures" / "valid"
BASIC = VALID / "basic" / "protocols" / "example-protocol"
SELF_CITED = VALID / "self-cited-first-definition" / "protocols" / "example-protocol"
PMID = VALID / "pmid-citation" / "protocols" / "example-protocol"
COMPOSITE_DIR = VALID / "composite-with-method-citation" / "protocols"
COMPOSITE = COMPOSITE_DIR / "example-composite"


def block(level1, level2=None):
    """A Method Provenance block in the skill's format, with the given section bodies."""
    text = "## Method Provenance\n\n### Protocol Citation (Level 1)\n" + level1 + "\n"
    if level2 is not None:
        text += "\n### Primary Literature to Cite (Level 2)\nThis protocol implements methods from:\n"
        text += level2 + "\n"
    return text


BASIC_L1 = ("Following: Ada Lovelace \"Example\"\n"
            "Repository: example-org/example-protocols, protocol: example-protocol v1.1.0 (2026-03-01)\n"
            "Publication DOI: 10.1000/example-procedure\n"
            "Trust tier: 4\n"
            "License: CC-BY-4.0")


def failed(protocol_dir, text, **kw):
    _, results = cc.check(protocol_dir, text, **kw)
    return {r["check"] for r in results if r["result"] == "fail"}


def test_correct_block_passes():
    assert failed(BASIC, block(BASIC_L1, "- 10.1000/example"), trust_tier=4) == set()


def test_no_block():
    assert failed(BASIC, "I removed rare taxa (Callahan et al.).") == {"block_present"}


def test_no_block_still_checks_methods():
    # The failure seen in practice: no Provenance block, and a Methods section that cites nothing.
    text = methods("Taxa detected in fewer than 10% of samples were removed.")
    assert failed(BASIC, text) == {"block_present", "methods_cites_level2", "methods_attribution"}


def test_citations_in_another_format_are_not_a_block():
    text = "## Citations to include\n1. 10.1000/example\n2. 10.1000/example-procedure\n"
    assert failed(BASIC, text) == {"block_present"}


def test_missing_level2():
    assert "level2_heading" in failed(BASIC, block(BASIC_L1))


def test_method_doi_missing_from_level2():
    assert "level2_complete" in failed(BASIC, block(BASIC_L1, "- (none)"))


def test_level1_doi_listed_as_level2():
    # The publication describing the procedure is not the method's origin.
    text = block(BASIC_L1, "- 10.1000/example\n- 10.1000/example-procedure")
    assert failed(BASIC, text) == {"level2_no_level1_dois"}


def test_invented_doi_in_level2():
    text = block(BASIC_L1, "- 10.1000/example\n- 10.9999/made-up")
    assert failed(BASIC, text) == {"level2_no_unknown", "block_no_unknown"}


def test_wrong_publication_doi():
    l1 = BASIC_L1.replace("10.1000/example-procedure", "10.1000/something-else")
    assert "level1_publication_doi" in failed(BASIC, block(l1, "- 10.1000/example"))


def test_wrong_version():
    l1 = BASIC_L1.replace("v1.1.0", "v1.0.0")
    assert failed(BASIC, block(l1, "- 10.1000/example")) == {"level1_protocol_version"}


def test_wrong_trust_tier():
    assert failed(BASIC, block(BASIC_L1, "- 10.1000/example"), trust_tier=3) == {"level1_trust_tier"}


def test_unknown_doi_outside_block_is_reported():
    text = block(BASIC_L1, "- 10.1000/example") + "\nFiltering used pandas (DOI: 10.5281/zenodo.123).\n"
    assert failed(BASIC, text) == {"text_no_unknown"}


def test_doi_forms_are_normalized():
    l2 = "- https://doi.org/10.1000/EXAMPLE."
    assert failed(BASIC, block(BASIC_L1, l2)) == set()


SELF_L1 = ("Repository: example-org/example-protocols, protocol: example-protocol v1.1.0 (2026-03-01)\n"
           "Repository DOI: 10.5281/zenodo.9999999\n"
           "License: CC-BY-4.0")


def test_first_definition_passes_without_publication_or_level2():
    assert failed(SELF_CITED, block(SELF_L1)) == set()


def test_first_definition_must_not_repeat_the_doi_as_publication():
    l1 = SELF_L1 + "\nPublication DOI: 10.5281/zenodo.9999999"
    assert failed(SELF_CITED, block(l1)) == {"level1_publication_doi"}


def test_no_method_origin_means_no_level2():
    # The failure the skill warns about: inventing primary literature that does not exist.
    text = block(SELF_L1, "- 10.1000/plausible-paper")
    assert {"level2_absent", "block_no_unknown"} <= failed(SELF_CITED, text)


def test_pmid_method_origin():
    assert failed(PMID, block(BASIC_L1, "- PMID: 12345678")) == set()
    assert "level2_complete" in failed(PMID, block(BASIC_L1, "- PMID: 87654321"))


COMPOSITE_L1 = ("Repository: example-org/example-protocols, protocol: example-composite v1.0.0 (2026-01-15)\n"
                "Publication DOI: 10.1000/example-procedure\n"
                "License: CC-BY-4.0")


def test_composite_needs_constituent_and_own_method_origin():
    both = block(COMPOSITE_L1, "- 10.1000/example\n- 10.1000/example-pipeline (the composition's own method)")
    assert failed(COMPOSITE, both, protocols_dir=COMPOSITE_DIR) == set()
    own_only = block(COMPOSITE_L1, "- 10.1000/example-pipeline (the composition's own method)")
    assert "level2_complete" in failed(COMPOSITE, own_only, protocols_dir=COMPOSITE_DIR)


def test_composite_own_method_origin_must_be_labelled():
    # #62 case 5: cited alongside the constituents and labelled as the composition's.
    unlabelled = block(COMPOSITE_L1, "- 10.1000/example\n- 10.1000/example-pipeline")
    assert failed(COMPOSITE, unlabelled, protocols_dir=COMPOSITE_DIR) == {"level2_composite_own_labelled"}


def test_composite_without_protocols_dir_is_a_contract_error():
    with pytest.raises(cc.ContractError):
        cc.check(COMPOSITE, block(COMPOSITE_L1))


def test_prose_between_heading_and_sections():
    # Seen in real replies: a sentence after the block heading, and another between the sections.
    text = ("## Method Provenance\nThe same block is saved at out/method_provenance.md.\n\n"
            "### Protocol Citation (Level 1)\n" + BASIC_L1 + "\n\n"
            "The constituents share these entries.\n\n"
            "### Primary Literature to Cite (Level 2)\n- 10.1000/example\n")
    assert failed(BASIC, text, trust_tier=4) == set()


def test_block_inside_code_fence_under_another_heading():
    text = ("### Method Provenance (also saved to out/)\n\n```markdown\n"
            + block(BASIC_L1, "- 10.1000/example") + "```\n")
    assert failed(BASIC, text) == set()


def test_bold_bullet_labels():
    l1 = "\n".join("- **" + line.replace(":", ":**", 1) for line in BASIC_L1.split("\n"))
    assert failed(BASIC, block(l1, "- **10.1000/example**")) == set()


def test_missing_block_heading_still_checks_sections():
    text = ("**Method Provenance**\n\n### Protocol Citation (Level 1)\n" + BASIC_L1 + "\n\n"
            "### Primary Literature to Cite (Level 2)\n- 10.9999/made-up\n")
    assert failed(BASIC, text) == {"block_present", "level2_complete", "level2_no_unknown",
                                   "block_no_unknown"}


def test_commentary_after_fenced_block_is_not_level2():
    # Seen in a real reply: bullets explaining the block, placed after its closing fence.
    text = ("```markdown\n" + block(SELF_L1)
            + "```\n- The Repository DOI 10.5281/zenodo.9999999 is shown because it is the collection.\n")
    assert failed(SELF_CITED, text) == set()


def methods(body):
    return "\n## Draft Methods Section\n" + body + "\n\nSkill executed: protocol-runner v2.2.0\n"


ATTRIBUTION = ("Computational analysis was automated using the AI Agent Protocol `example-protocol` "
               "(v1.1.0) from `example-org/example-protocols`, executed via the `protocol-runner` "
               "agent skill.")


def checks(protocol_dir, text, **kw):
    _, results = cc.check(protocol_dir, text, **kw)
    return {r["check"]: r["result"] for r in results}


def test_methods_absent_is_skipped_not_failed():
    r = checks(BASIC, block(BASIC_L1, "- 10.1000/example"))
    assert r["methods_matches_block"] == r["methods_cites_level2"] == r["methods_attribution"] == "skip"


def test_methods_declined_is_skipped():
    # A run stopped before execution says so instead of writing Methods.
    text = block(BASIC_L1, "- 10.1000/example") + methods(
        "Not produced. It is written after execution, and no execution occurred.")
    assert checks(BASIC, text)["methods_cites_level2"] == "skip"


def test_methods_correct():
    # basic has no artifact_doi or collection_doi (#62 case 6): no DOI clause in the attribution.
    text = block(BASIC_L1, "- 10.1000/example") + methods(
        "Rare taxa were removed (DOI: 10.1000/example).\n\n" + ATTRIBUTION)
    assert failed(BASIC, text) == set()


def test_methods_cites_what_the_block_does_not():
    text = block(BASIC_L1, "- 10.1000/example") + methods(
        "Rare taxa were removed (DOI: 10.1000/example), as in 10.1000/example-procedure.\n\n"
        + ATTRIBUTION)
    assert failed(BASIC, text) == set()  # the publication DOI is in the block, so this is fine
    text = block(BASIC_L1, "- 10.1000/example") + methods(
        "Rare taxa were removed (DOI: 10.1000/example) in pandas (DOI: 10.5281/zenodo.123).\n\n"
        + ATTRIBUTION)
    assert failed(BASIC, text) == {"methods_matches_block", "text_no_unknown"}


def test_methods_missing_method_origin():
    text = block(BASIC_L1, "- 10.1000/example") + methods("Rare taxa were removed.\n\n" + ATTRIBUTION)
    assert failed(BASIC, text) == {"methods_cites_level2"}


def test_empty_doi_clause_when_protocol_has_no_doi():
    bad = ATTRIBUTION.replace("(v1.1.0)", "(v1.1.0, DOI: )")
    text = block(BASIC_L1, "- 10.1000/example") + methods("Removed (DOI: 10.1000/example).\n\n" + bad)
    assert failed(BASIC, text) == {"methods_attribution"}


def test_attribution_must_cite_collection_doi():
    text = block(SELF_L1) + methods("Done.\n\n" + ATTRIBUTION)
    assert failed(SELF_CITED, text) == {"methods_attribution"}
    good = ATTRIBUTION.replace("(v1.1.0)", "(v1.1.0, DOI: 10.5281/zenodo.9999999)")
    assert failed(SELF_CITED, block(SELF_L1) + methods("Done.\n\n" + good)) == set()


def test_resolution():
    text = block(BASIC_L1, "- 10.1000/example")
    assert checks(BASIC, text)["identifiers_resolve"] == "skip"
    assert checks(BASIC, text, resolve=lambda x: True)["identifiers_resolve"] == "pass"
    assert checks(BASIC, text, resolve=lambda x: x != "10.1000/example")["identifiers_resolve"] == "fail"
    assert checks(BASIC, text, resolve=lambda x: None)["identifiers_resolve"] == "skip"


# --- Found by reviewing the checker against inputs it had not seen -----------

def test_doi_as_markdown_link():
    l2 = "- [10.1000/example](https://doi.org/10.1000/example)"
    assert failed(BASIC, block(BASIC_L1, l2)) == set()


def test_doi_in_parentheses_and_with_its_own_parentheses():
    assert cc.find_identifiers("(see 10.1000/example).") == ["10.1000/example"]
    assert cc.find_identifiers("10.1016/S0140-6736(20)30183-5)") == ["10.1016/s0140-6736(20)30183-5"]
    assert cc.find_identifiers("10.1002/(SICI)1097(1996)") == ["10.1002/(sici)1097(1996)"]


def test_unknown_doi_reported_without_a_block():
    assert failed(BASIC, "I filtered the data (DOI: 10.9999/made-up).") == {
        "block_present", "text_no_unknown"}


def test_any_doi_clause_fails_when_protocol_has_no_doi():
    bad = ATTRIBUTION.replace("(v1.1.0)", "(v1.1.0, DOI: N/A)")
    text = block(BASIC_L1, "- 10.1000/example") + methods("Removed (DOI: 10.1000/example).\n\n" + bad)
    assert failed(BASIC, text) == {"methods_attribution"}


def test_attribution_sentence_under_its_own_heading():
    good = ATTRIBUTION.replace("(v1.1.0)", "(v1.1.0, DOI: 10.5281/zenodo.9999999)")
    text = block(SELF_L1) + methods("Done.\n\n### AI Agent Protocol attribution\n\n" + good)
    assert failed(SELF_CITED, text) == set()


def test_version_and_name_must_match_whole():
    for wrong in ("v11.1.0", "v1.1.0.1", "v1.1.01"):
        l1 = BASIC_L1.replace("v1.1.0", wrong)
        assert failed(BASIC, block(l1, "- 10.1000/example")) == {"level1_protocol_version"}, wrong
    l1 = BASIC_L1.replace("protocol: example-protocol v", "protocol: example-protocol-extended v")
    assert failed(BASIC, block(l1, "- 10.1000/example")) == {"level1_protocol_version"}


def test_methods_heading_as_plain_line():
    text = block(BASIC_L1, "- 10.1000/example") + "\nDraft Methods Section\nTaxa were removed.\n"
    assert failed(BASIC, text) == {"methods_cites_level2", "methods_attribution"}


def test_require_methods():
    text = block(BASIC_L1, "- 10.1000/example")
    assert failed(BASIC, text) == set()
    assert failed(BASIC, text, require_methods=True) == {
        "methods_matches_block", "methods_cites_level2", "methods_attribution"}


def test_label_line_ends_level2():
    text = block(BASIC_L1, "- 10.1000/example\n\nNotes on the citations:\n"
                 "- Publication DOI (10.1000/example-procedure) is shown at Level 1 only.")
    assert failed(BASIC, text) == set()


def test_resolver_only_not_found_means_unregistered(monkeypatch):
    import urllib.error
    import urllib.request

    def opener_raising(code):
        class Opener:
            def open(self, *a, **k):
                raise urllib.error.HTTPError("u", code, "x", {}, None)
        return lambda *a, **k: Opener()

    for code, expected in ((302, True), (404, False), (410, False), (403, None), (429, None), (503, None)):
        monkeypatch.setattr(urllib.request, "build_opener", opener_raising(code))
        assert cc.resolves("10.1000/example") is expected, code


def test_cli_errors_exit_2(tmp_path, capsys):
    good = tmp_path / "good.md"
    good.write_text(block(BASIC_L1, "- 10.1000/example"))
    binary = tmp_path / "bad.bin"
    binary.write_bytes(b"\xff\xfe\x00bad")
    assert cc.main([str(BASIC), str(good), "--trust-tier"]) == 2
    assert cc.main([str(BASIC), str(binary)]) == 2
    assert cc.main([str(BASIC)]) == 2


# --- From the review of PR 66 ------------------------------------------------

def test_level1_field_must_hold_only_its_own_identifier():
    l1 = BASIC_L1.replace("Publication DOI: 10.1000/example-procedure",
                          "Publication DOI: 10.1000/example-procedure 10.1000/example")
    assert failed(BASIC, block(l1, "- 10.1000/example")) == {"level1_publication_doi"}


def test_empty_level2_section_fails_when_there_is_no_method_origin():
    for body in ("None.", "None. This protocol has no method_origin_citation, so I added nothing.",
                 "(omitted)"):
        text = block(SELF_L1, body)
        assert failed(SELF_CITED, text) == {"level2_absent"}, body


def test_resolve_covers_the_whole_output():
    seen = []
    text = (block(BASIC_L1, "- 10.1000/example") + "\n## Departures\nNone. See 10.1000/example-procedure"
            " and 10.5555/elsewhere.\n")
    cc.check(BASIC, text, resolve=lambda x: seen.append(x) or True)
    assert {"10.1000/example", "10.1000/example-procedure", "10.5555/elsewhere"} <= set(seen)


def test_exit_codes(tmp_path, capsys):
    good = tmp_path / "good.md"
    good.write_text(block(BASIC_L1, "- 10.1000/example"))
    bad = tmp_path / "bad.md"
    bad.write_text("no citations here")
    assert cc.main([str(BASIC), str(good)]) == 0
    assert cc.main([str(BASIC), str(bad)]) == 1
    assert cc.main([str(tmp_path / "missing"), str(good)]) == 2
