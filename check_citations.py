#!/usr/bin/env python3
"""Check the citations an agent gave when it ran a protocol.

Usage:
    check_citations.py PROTOCOL_DIR OUTPUT [--trust-tier N] [--protocols-dir DIR]
                       [--resolve] [--require-methods]

PROTOCOL_DIR is the directory holding the protocol's protocol.md. OUTPUT is a file
holding what the agent wrote: its method_provenance.md, or its whole reply.

The checker compares the agent's Method Provenance block against the protocol's
frontmatter, following the block format in skills/protocol-runner/SKILL.md:

  * the block and its Level 1 and Level 2 headings are present;
  * Level 1 names the protocol and version, and gives collection_doi, artifact_doi,
    and protocol_citation where the skill says it should, and only there;
  * Level 2 lists exactly the method_origin_citation values: the protocol's own,
    and for a composite, those of each protocol in protocols_used;
  * where the composite carries its own method_origin_citation, it is labelled as
    the composition's;
  * no DOI or PMID appears that the protocol does not carry, in the block or in
    the rest of OUTPUT. Only frontmatter DOIs are ground truth (#62), so any other
    identifier, software included, fails;
  * the Draft Methods Section cites nothing the block does not, cites every
    method origin and the attribution DOI (artifact_doi, else collection_doi),
    and, where the protocol has neither, leaves no empty "DOI:" behind;
  * with --resolve, every DOI and PMID cited resolves at doi.org or PubMed.

A check that does not apply, such as Methods checks on output with no Methods
section, or resolution without --resolve, is reported as `skip`. A run that
executed the protocol must have a Methods section: pass --require-methods to
make its absence a failure.

Known limit: in Level 2, a list item that mentions a Level 1 DOI only to say it
is not a method origin is still read as citing it. Read the flagged line.

It prints a YAML report and exits 0 if no check failed, 1 if any failed, and 2
if it could not run (for example, a missing protocol or dependency).

It checks what was written, not when. Whether the block came before the agent
touched the data can only be read from the agent's transcript.
"""
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_protocol import extract_frontmatter  # noqa: E402

CHECKER_NAME = "check_citations.py"
CHECKER_VERSION = "0.4.0"

# Square brackets are excluded so a Markdown link, [10.x/y](https://doi.org/10.x/y),
# reads as two mentions of one DOI, not as one long unknown identifier.
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"'<>`|\[\]]+", re.IGNORECASE)
PMID_RE = re.compile(r"\bPMID:?\s*(\d{1,9})\b", re.IGNORECASE)

BLOCK_HEADING = "## Method Provenance"
LEVEL1_HEADING = "### Protocol Citation (Level 1)"
LEVEL2_HEADING = "### Primary Literature to Cite (Level 2)"


class ContractError(Exception):
    """The checker was given something it cannot check."""


def normalize(identifier):
    """Lower-case a DOI or PMID and drop a `doi:` prefix or `https://doi.org/` form."""
    s = str(identifier).strip()
    s = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", s, flags=re.IGNORECASE)
    m = PMID_RE.fullmatch(s)
    if m:
        return f"pmid:{m.group(1)}"
    s = s.rstrip(".,;:]*_")
    # A closing parenthesis belongs to the DOI only if it has an opening one.
    while s.endswith(")") and s.count(")") > s.count("("):
        s = s[:-1].rstrip(".,;:]*_")
    return s.lower()


def find_identifiers(text):
    """Every DOI and PMID in text, normalized, in order of appearance, without repeats."""
    found = []
    for m in DOI_RE.finditer(text):
        found.append((m.start(), normalize(m.group(0))))
    for m in PMID_RE.finditer(text):
        found.append((m.start(), f"pmid:{m.group(1)}"))
    seen, out = set(), []
    for _, ident in sorted(found):
        if ident not in seen:
            seen.add(ident)
            out.append(ident)
    return out


def load_protocol(protocol_dir):
    path = Path(protocol_dir) / "protocol.md"
    if not path.is_file():
        raise ContractError(f"no protocol.md in {protocol_dir}")
    fm = extract_frontmatter(path)
    if not isinstance(fm, dict) or not fm.get("name"):
        raise ContractError(f"{path} has no readable frontmatter")
    return fm


def resolve_dependencies(fm, protocols_dir):
    """The frontmatter of each protocol in protocols_used, by name and exact version."""
    deps = []
    for dep in fm.get("protocols_used") or []:
        if protocols_dir is None:
            raise ContractError(
                f"{fm['name']} uses {dep.get('name')}: pass --protocols-dir to resolve it")
        dep_fm = load_protocol(Path(protocols_dir) / dep["name"])
        if str(dep_fm.get("version")) != str(dep.get("version")):
            raise ContractError(
                f"{fm['name']} pins {dep['name']} {dep.get('version')}, "
                f"but {protocols_dir} holds {dep_fm.get('version')}")
        deps.append(dep_fm)
    return deps


LABEL_LINE = re.compile(r"^\s*[-*]?\s*(\*\*)?[A-Z][A-Za-z ]{1,40}:")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
HEADING = re.compile(r"^#{1,6}\s")
RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


def _heading_line(lines, title, start=0):
    """Index of the first heading line whose text starts with `title`, at any heading
    level, or None. The level is not checked: agents nest the block under their own
    headings, and what matters is that the heading is there."""
    pattern = re.compile(r"^#{1,6}\s*" + re.escape(title))
    for i in range(start, len(lines)):
        if pattern.match(lines[i]):
            return i
    return None


def _section_end(lines, start, level2):
    """Index of the first line after `start` that does not belong to the section.

    A section holds `Label: value` lines and list items; Level 2 also holds its
    introductory sentence and indented continuation lines. Blank lines and code
    fences are skipped. Anything else, including any heading or rule, ends it, so
    prose that follows the block is not read as part of it.
    """
    i = start + 1
    seen_content = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if FENCE.match(line):
            # A fence closing after the section's content ends it: what follows a
            # fenced block is the agent's commentary, not part of the block.
            if seen_content:
                return i
            i += 1
            continue
        if not stripped:
            i += 1
            continue
        if HEADING.match(line) or RULE.match(line):
            return i
        if level2:
            # Level 2 is an introductory sentence and a list. A `Label:` line there,
            # such as "Notes on the citations:", starts the agent's commentary.
            ok = (LIST_ITEM.match(line) or line[:1] in (" ", "\t")
                  or stripped.lower().startswith("this protocol implements"))
        else:
            ok = LABEL_LINE.match(line) or LIST_ITEM.match(line)
        if not ok:
            return i
        seen_content = True
        i += 1
    return len(lines)


def split_block(text):
    """Return (heading_found, level1, level2, block, rest).

    `heading_found` says whether a `Method Provenance` heading exists. `level1` and
    `level2` are the text of the two sections, or None. `block` is everything from
    the block's first line to the end of its last section, and `rest` is the text
    outside it. Where the block heading is missing but a Level 1 heading exists,
    the sections are still read, so their content is checked as well.
    """
    lines = text.split("\n")
    top = _heading_line(lines, BLOCK_HEADING.lstrip("# "))
    l1 = _heading_line(lines, LEVEL1_HEADING.lstrip("# "), top or 0)
    if top is None and l1 is None:
        return False, None, None, None, text
    first = top if top is not None else l1
    l2 = _heading_line(lines, LEVEL2_HEADING.lstrip("# "), (l1 if l1 is not None else first) + 1)

    level1 = level2 = None
    end = first + 1
    if l1 is not None:
        # Level 1 runs to the Level 2 heading where there is one: agents put a
        # sentence of explanation between the two sections.
        l1_end = l2 if l2 is not None else _section_end(lines, l1, level2=False)
        level1 = "\n".join(lines[l1:l1_end])
        end = l1_end
    if l2 is not None:
        l2_end = _section_end(lines, l2, level2=True)
        level2 = "\n".join(lines[l2:l2_end])
        end = l2_end
    block = "\n".join(lines[first:end])
    rest = "\n".join(lines[:first] + lines[end:])
    return top is not None, level1, level2, block, rest


METHODS_HEADING = re.compile(r"^\s*(#{1,6}\s*|\*\*|[-*]\s+)?\s*Draft Methods( Section)?\b",
                             re.IGNORECASE)
SKILL_RECORD = re.compile(r"Skill executed", re.IGNORECASE)
DECLINED = re.compile(r"\b(not (yet )?(produced|generated|written)|neither exists|nothing was "
                      r"(run|executed)|no (step|execution|analysis) (was|has been) (run|performed))",
                      re.IGNORECASE)


def split_methods(text):
    """The Draft Methods Section of `text`, or None. It runs from its heading (a
    Markdown heading or a bold line) to the next heading of the same or a higher
    level, or to the Skill Execution Record, whichever comes first."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if METHODS_HEADING.match(line):
            m = re.match(r"^\s*(#{1,6})\s", line)
            level = len(m.group(1)) if m else 6
            end = len(lines)
            for j in range(i + 1, len(lines)):
                h = re.match(r"^(#{1,6})\s", lines[j])
                if (h and len(h.group(1)) <= level) or SKILL_RECORD.search(lines[j]):
                    end = j
                    break
            section = "\n".join(lines[i:end])
            # A heading followed only by a statement that no Methods were written,
            # as when a run stops before execution, is not a Methods section.
            content = [ln for ln in lines[i + 1:end] if ln.strip()]
            if DECLINED.search(line) or (
                    len(content) <= 3 and content and DECLINED.search(content[0])):
                return None
            if not content:
                continue
            return section
    return None


def resolves(identifier, timeout=15):
    """True if the identifier resolves, False if the resolver says it does not, and
    None if the resolver could not be reached. A DOI is asked of doi.org without
    following its redirect, which is enough to know it is registered."""
    import urllib.error
    import urllib.request

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    if identifier.startswith("pmid:"):
        url = f"https://pubmed.ncbi.nlm.nih.gov/{identifier[5:]}/"
    else:
        url = f"https://doi.org/{identifier}"
    opener = urllib.request.build_opener(NoRedirect)
    try:
        status = opener.open(urllib.request.Request(url, method="HEAD"), timeout=timeout).status
    except urllib.error.HTTPError as e:
        status = e.code
    except (urllib.error.URLError, OSError):
        return None
    if status < 400:
        return True
    # Only "not found" says the identifier is unregistered. A refusal, a rate limit
    # or a server error says nothing about it.
    return False if status in (404, 410) else None


def labelled_line(section, label):
    """The value after `label:` in section, or None if no such line."""
    if section is None:
        return None
    m = re.search(rf"^\s*[-*]?\s*(?:\*\*)?{re.escape(label)}\s*:(?:\*\*)?(.*)$", section,
                  flags=re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else None


def check(protocol_dir, output_text, trust_tier=None, protocols_dir=None, resolve=None,
          require_methods=False):
    fm = load_protocol(protocol_dir)
    deps = resolve_dependencies(fm, protocols_dir)

    collection = normalize(fm["collection_doi"]) if fm.get("collection_doi") else None
    artifact = normalize(fm["artifact_doi"]) if fm.get("artifact_doi") else None
    publication = normalize(fm["protocol_citation"]) if fm.get("protocol_citation") else None
    first_definition = publication is not None and publication in {collection, artifact}

    expected_l2 = []
    for d in deps:
        if d.get("method_origin_citation"):
            expected_l2.append(normalize(d["method_origin_citation"]))
    if fm.get("method_origin_citation"):
        expected_l2.append(normalize(fm["method_origin_citation"]))
    expected_l2 = list(dict.fromkeys(expected_l2))

    level1_ids = {x for x in (collection, artifact, publication) if x}
    for d in deps:
        for key in ("collection_doi", "artifact_doi", "protocol_citation"):
            if d.get(key):
                level1_ids.add(normalize(d[key]))
    known = level1_ids | set(expected_l2)

    heading_found, l1, l2, block, rest = split_block(output_text)
    results = []

    def record(check_id, passed, message):
        result = "skip" if passed is None else "pass" if passed else "fail"
        results.append({"check": check_id, "result": result, "detail": message})

    record("block_present", heading_found,
           "`Method Provenance` heading found" if heading_found else
           "no `Method Provenance` heading" +
           ("" if block is None else ", though a Level 1 section was found and is checked below"))
    if block is not None:

        record("level1_heading", l1 is not None,
               f"`{LEVEL1_HEADING}` found" if l1 else f"no `{LEVEL1_HEADING}` heading")

        if l1 is not None:
            repo_line = labelled_line(l1, "Repository") or ""
            def whole(token):
                return re.search(rf"(?<![\w.-]){re.escape(str(token))}(?![\w-]|\.\d)", repo_line)
            names_it = bool(whole(fm["name"]) and (whole(fm["version"]) or whole(f"v{fm['version']}")))
            record("level1_protocol_version", names_it,
                   f"Repository line names {fm['name']} v{fm['version']}" if names_it else
                   f"Repository line should name {fm['name']} and version {fm['version']}, "
                   f"found: {repo_line or '(no Repository line)'}")

            def doi_line(label, expected, required):
                value = labelled_line(l1, label)
                ids = find_identifiers(value or "")
                check_id = "level1_" + label.lower().replace(" ", "_")
                if required:
                    ok = expected in ids
                    record(check_id, ok,
                           f"{label} is {expected}" if ok else
                           f"{label} should be {expected}, found: {value or '(no line)'}")
                else:
                    ok = not ids
                    record(check_id, ok,
                           f"{label} correctly gives no DOI" if ok else
                           f"{label} should give no DOI, found: {', '.join(ids)}")

            if collection:
                doi_line("Repository DOI", collection, True)
            doi_line("Protocol DOI", artifact, artifact is not None)
            if first_definition:
                doi_line("Publication DOI", None, False)
            elif publication:
                doi_line("Publication DOI", publication, True)

            if trust_tier is not None:
                value = labelled_line(l1, "Trust tier") or ""
                ok = re.search(rf"\b{re.escape(str(trust_tier))}\b", value) is not None
                record("level1_trust_tier", ok,
                       f"Trust tier is {trust_tier}" if ok else
                       f"Trust tier should be {trust_tier}, found: {value or '(no line)'}")
            if fm.get("license"):
                value = labelled_line(l1, "License") or ""
                ok = str(fm["license"]).lower() in value.lower()
                record("level1_license", ok,
                       f"License is {fm['license']}" if ok else
                       f"License should be {fm['license']}, found: {value or '(no line)'}")

        if expected_l2:
            if l2 is None:
                record("level2_heading", False, f"no `{LEVEL2_HEADING}` heading, but "
                       f"{len(expected_l2)} method origin citation(s) are expected")
            else:
                found = find_identifiers(l2)
                missing = [x for x in expected_l2 if x not in found]
                misplaced = [x for x in found if x in level1_ids and x not in expected_l2]
                extra = [x for x in found if x not in expected_l2 and x not in level1_ids]
                record("level2_complete", not missing,
                       "every method origin citation is listed" if not missing else
                       f"missing from Level 2: {', '.join(missing)}")
                record("level2_no_level1_dois", not misplaced,
                       "no Level 1 citation is listed as Level 2" if not misplaced else
                       f"Level 1 citation(s) listed as Level 2: {', '.join(misplaced)}")
                record("level2_no_unknown", not extra,
                       "no citation the protocol does not carry" if not extra else
                       f"not carried by the protocol: {', '.join(extra)}")
                own = fm.get("method_origin_citation")
                if fm.get("type") == "composite" and own:
                    own = normalize(own)
                    lines = [ln for ln in l2.split("\n") if own in find_identifiers(ln)]
                    labelled = any(re.search(r"compos", ln, re.IGNORECASE) for ln in lines)
                    record("level2_composite_own_labelled", labelled,
                           f"{own} is labelled as the composition's own method" if labelled else
                           f"{own} is the composite's own method origin, but its Level 2 line does "
                           f"not say so (expected a mention of the composite or composition)")
        else:
            ids = find_identifiers(l2 or "")
            record("level2_absent", not ids,
                   "no Level 2 citation given, and the protocol carries none" if not ids else
                   f"the protocol carries no method origin citation, but Level 2 lists: "
                   f"{', '.join(ids)}")

        unknown_in_block = [x for x in find_identifiers(block) if x not in known]
        record("block_no_unknown", not unknown_in_block,
               "every identifier in the block is one the protocol carries" if not unknown_in_block
               else f"not carried by the protocol: {', '.join(unknown_in_block)}")

    unknown_elsewhere = [x for x in find_identifiers(rest) if x not in known]
    record("text_no_unknown", not unknown_elsewhere,
           "every identifier outside the block is one the protocol carries"
           if not unknown_elsewhere else
           f"outside the block, not carried by the protocol: {', '.join(unknown_elsewhere)}. "
           f"Each is either a citation the agent added, such as software, or one it invented. "
           f"Only frontmatter DOIs are ground truth (#62).")

    attribution = artifact or collection
    methods = split_methods(rest)
    if methods is None:
        for check_id in ("methods_matches_block", "methods_cites_level2", "methods_attribution"):
            record(check_id, False if require_methods else None,
                   "no Draft Methods Section in the output, or one that says it was not written")
    else:
        block_ids = set(find_identifiers(block or ""))
        m_ids = find_identifiers(methods)
        not_in_block = [x for x in m_ids if x not in block_ids]
        record("methods_matches_block", not not_in_block,
               "the Methods section cites nothing the Provenance block does not"
               if not not_in_block else
               f"cited in Methods but not in the Provenance block: {', '.join(not_in_block)}")
        missing = [x for x in expected_l2 if x not in m_ids]
        record("methods_cites_level2", not missing,
               "every method origin citation appears in Methods" if not missing else
               f"method origin citation(s) missing from Methods: {', '.join(missing)}")
        sentences = [x for x in re.split(r"(?<=[.!?])\s+|\n\s*\n", methods)
                     if "agent protocol" in x.lower()]
        if not sentences:
            record("methods_attribution", False,
                   "no AI Agent Protocol attribution sentence in Methods")
        elif attribution:
            ok = any(attribution in find_identifiers(x) for x in sentences)
            record("methods_attribution", ok,
                   f"attribution sentence cites {attribution}" if ok else
                   f"attribution sentence should cite {attribution} "
                   f"({'artifact_doi' if artifact else 'collection_doi'})")
        else:
            # The runner says to omit the DOI clause entirely, so "DOI: N/A" fails
            # as "DOI:" with nothing after it does.
            clause = any(re.search(r"\bDOI\b", x, re.IGNORECASE) for x in sentences)
            record("methods_attribution", not clause,
                   "the protocol has no artifact or collection DOI, and the attribution "
                   "sentence correctly has no DOI clause" if not clause else
                   "the protocol has no artifact or collection DOI, so the attribution "
                   "sentence should have no DOI clause at all")

    cited = list(dict.fromkeys(find_identifiers(block or "") + find_identifiers(methods or "")))
    if resolve is None:
        record("identifiers_resolve", None, "not checked; pass --resolve")
    else:
        status = {x: resolve(x) for x in cited}
        bad = [x for x, ok in status.items() if ok is False]
        unknown = [x for x, ok in status.items() if ok is None]
        if bad:
            record("identifiers_resolve", False, f"do not resolve: {', '.join(bad)}")
        elif unknown:
            record("identifiers_resolve", None,
                   f"resolver unreachable for: {', '.join(unknown)}")
        else:
            record("identifiers_resolve", True, f"all {len(cited)} cited identifier(s) resolve")

    return fm, results


def main(argv):
    import argparse
    parser = argparse.ArgumentParser(
        prog=CHECKER_NAME, description="Check the citations an agent gave when it ran a protocol.")
    parser.add_argument("protocol_dir", help="directory holding the protocol's protocol.md")
    parser.add_argument("output", help="file holding what the agent wrote")
    parser.add_argument("--trust-tier", help="the repository's trust_tier in the registry")
    parser.add_argument("--protocols-dir", help="where a composite's constituents are found")
    parser.add_argument("--resolve", action="store_true",
                        help="check that each cited DOI or PMID resolves (needs network)")
    parser.add_argument("--require-methods", action="store_true",
                        help="fail, not skip, when there is no Draft Methods Section")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    protocol_dir, output = args.protocol_dir, args.output
    try:
        text = Path(output).read_text(encoding="utf-8")
        fm, results = check(protocol_dir, text, args.trust_tier, args.protocols_dir,
                            resolves if args.resolve else None, args.require_methods)
    except (ContractError, OSError, UnicodeDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    failed = [r for r in results if r["result"] == "fail"]
    report = {
        "checker": f"{CHECKER_NAME} {CHECKER_VERSION}",
        "protocol": fm["name"],
        "version": str(fm["version"]),
        "output": str(output),
        "result": "fail" if failed else "pass",
        "checks": results,
    }
    yaml.safe_dump(report, sys.stdout, sort_keys=False, allow_unicode=True, width=100)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
