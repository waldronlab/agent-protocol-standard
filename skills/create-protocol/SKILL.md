---
name: create-protocol
description: Scaffold a new protocol from the standard's template, fill its frontmatter from the current schema, ask the two citation questions separately, write Materials and Steps, and validate before reporting
version: 0.1.0
category: protocols
author: waldronlab
tags: [protocol, authoring, scaffold, frontmatter, citation, validation]
---

# create-protocol

Writes a new `protocols/<name>/protocol.md` that conforms to `PROTOCOL_STANDARD.md`, starting from
the template the standard ships. The schema and the template are read from a local checkout of the
standard at run time, never from a copy held in this skill, so the two cannot drift. The skill asks
for every fact it does not have; it never invents an author, an ORCID, a date, a DOI, or a tool
version. A claim about a tool's default, such as "the default of common implementations", is a
fact too: attribute it to the user or the repository, or drop it.

## Usage

- "Create a protocol for Shannon diversity from issue #50"
- "Scaffold a new atomic protocol called prevalence-filtering"
- "Write a composite protocol that runs prevalence-filtering then independent-filtering-variance"

## Prerequisites

- A local checkout of `waldronlab/agent-protocol-standard`, with Python 3.10+, `pydantic`, and
  `pyyaml`, for `template/`, `scripts/models.py`, and `scripts/validate_protocol.py`.
- A local checkout of the content repository the protocol will live in, on a branch.
- `GITHUB_REPOSITORY` set to the content repository's `owner/name` when validating.

## Process

### 1. Read the current schema and template

1. Find the standard checkout (ask if it is not obvious). Read `PROTOCOL_STANDARD.md`, then the
   `ProtocolFrontmatter` class in `scripts/models.py`: its fields are the schema, its validators
   are the rules, and `TEMPLATE_PLACEHOLDER_CITATION` is the value the validator rejects by name.
   Read every file under `template/protocols/example-protocol/`. Do not work from memory of an
   earlier version of any of these.
2. Read the content repository's existing protocols for house style: how Materials bullets are
   grouped, how parameters are named, what `collection_doi` and `license` the collection uses.
   Reuse those values; do not ask for what the repository already states.
3. If the user pointed at an issue, read its full body and every comment. Treat values it gives
   as the user's answers, and its checklist as acceptance criteria to meet in the text.

### 2. Name and scaffold

1. Settle `name`: kebab-case, matching `^[a-z0-9]+(-[a-z0-9]+)*$`, describing the operation. The
   directory is `protocols/<name>/` and must equal `name` exactly. If a directory with that name
   already exists, stop; this skill does not revise. If an open pull request or issue already
   carries a protocol by that name, say so and continue only if the user confirms a fresh one is
   wanted. Do not read the other draft: a second independent writing is the point of asking.
2. Copy the whole template directory, `tests/` included, to `protocols/<name>/`. Delete every
   comment in the frontmatter except the marker comments, which step 7 handles; they are
   instructions, not metadata.

### 3. Fill the required frontmatter

Fill `name`, `description` (one sentence), `version: 1.0.0`, `authors`, `date`, and `status`.
`date` is today's date in `YYYY-MM-DD` unless the user gives another, and the same date goes in
the `### Version 1.0.0 (...)` heading, which the validator checks against it. `status` is
`draft`. Do not write `stable`: it is an assertion the authors make about readiness (ADR 0013),
not a default.
Ask for every author's name; include `orcid` only when the user supplies one, since a malformed or
guessed ORCID names nobody. Keep the frontmatter key order of the template and quote strings as
the repository's other protocols do.

### 4. Ask the two citation questions, separately

Ask each in its own words and do not define one against the other (ADR 0014).

1. **Who published these instructions?** That is `protocol_citation`, required, a DOI
   (`10.1000/xyz`) or `PMID:12345678`. Where a publication describes this procedure as written
   here, parameters included, name it. A paper that merely *applies* the method is not an answer.
   Where no publication describes it, the answer is this protocol's own concept DOI:
   `artifact_doi` if it has one, otherwise `collection_doi`. That is a first definition, a claim
   the author makes after looking for the paper and finding none, so write it only when the
   user confirms it; say so in the report. A collection with no DOI cannot host one.
2. **Who invented the method?** That is `method_origin_citation`, optional: the primary literature
   where the method was first proposed. Where the protocol originates no method, delete the field
   entirely. Never set it to null, and never fill it to satisfy the validator.

If the user does not know an answer, or has not confirmed a first definition, leave
`protocol_citation` as the template placeholder, which the validator will reject, and record the
question as an open judgement call. Never search for a DOI and write it in on the user's behalf.

### 5. Decide `type` and `protocols_used`

`type: atomic` with `protocols_used: []` (or the field deleted) for a single operation.

For `type: composite`, fill `protocols_used` with one entry per constituent: `name`,
`repository` as `owner/name`, and `version` copied exactly from that protocol's current
frontmatter `version`, read from its `protocol.md`, not from memory or an index. An atomic
protocol may not list constituents and a composite must list at least one.

### 6. Write the body

1. **Title and overview.** One or two sentences: what the protocol produces and what it is for.
   Statements about what it does not do belong here or in Notes, not in Materials.
2. **`## Materials`.** Every input (data, parameters, software, reference data) and every condition
   on an input, in the bullet groups the template shows. Write each condition with **must** or
   **should** in the RFC 2119 sense (ADR 0017): a *must* violation stops execution, a *should*
   violation proceeds with a warning, so a *should* condition says what the warning is about. Each
   parameter states what it controls, its default or why it has none, and the values it may take.
   Steps may not add conditions on inputs; if one belongs in a step, it belongs here. A check that
   is only possible during computation, such as a sample whose total is zero, stays in the step
   where it arises, with what the executor does about it. Name a software version only when the
   user or the repository states one; otherwise write the tool without a version rather than
   guess.
3. **`## Steps`.** At least one `### Step N: <action>` heading. Plain prose an agent in any
   language can follow without guessing: explicit parameter values, and the reason for any value
   that is not obvious. No validation step restating Materials; the executor checks Materials
   before Step 1. Say what is recorded as output in the final step.
4. **`## History & Reviews`.** One entry, `### Version 1.0.0 (<date>)` with the frontmatter date,
   `#### Changes` with `- Initial protocol creation.`, and `#### Reviews` with `*No reviews yet.*`.
   No `reviews:` frontmatter field. This section stays last; any other section the repository's
   house style adds, such as `## Out of scope`, goes above it.

### 7. Walk every optional marker

Search the new directory for the literal string `Optional, delete if unneeded.`. Every hit is an
item the template ships in case it is wanted. For each, either fill the item with a real value
or delete it, then delete the marker. Note each deletion for the report. An item is one of:

- a frontmatter field. An empty list or null is not a filled value; delete the field instead,
  unless the repository's other protocols keep empty lists, in which case follow them and say
  in the report which fields were kept empty for that reason.
- the `## Notes` section: keep it when there are caveats, compute requirements, or
  troubleshooting to record; otherwise delete the whole section.
- `tests/`: keep the directory only when the user supplies a real test, that is known inputs and
  the outputs a correct execution produces. Rewrite `test.yaml` and the data files to match. The
  example test is for a different protocol and never ships as is. Otherwise delete `tests/`.

Finish by searching again; the string must not appear anywhere under `protocols/<name>/`. Also
confirm no template comment such as `# Replace every value below` survives.

### 8. Validate

From the standard checkout:

```sh
GITHUB_REPOSITORY=<owner/name> python3 scripts/validate_protocol.py <path to protocols dir>
```

Resolve what it reports: fix every mechanical error, re-run, and leave only judgement calls, each
stated in the report. A placeholder `protocol_citation` left on purpose
is one such call. Do not report done while a fixable error remains.

## Output Format

1. The path created, and the directory listing under it.
2. The filled frontmatter, verbatim.
3. **Optional items deleted**: one line each, so the author can see the choice and reverse it,
   and the fields kept empty to match house style.
4. **First definition**: stated when `protocol_citation` names the protocol's own DOI.
5. **Open judgement calls**: anything left unfilled or chosen by the skill where the author may
   disagree, such as a parameter default or a *must* versus *should* decision, and any unusual
   implementation choice made in Steps that the user did not ask for, such as re-seeding a
   random number generator per sample.
6. The validator's final run, verbatim.
7. A closing line naming this skill and its version:

   > 🛠️ Skill executed: `create-protocol` v`0.1.0` (`waldronlab/agent-protocol-standard`)

## Notes

- This skill writes a protocol that does not exist yet. Fixing one that exists is
  `validate-protocol` (`waldronlab/agent-protocol-standard#37`); bumping a version is
  `update-protocol` (`waldronlab/agent-protocol-standard#36`). Both are sibling skills in
  progress, so the names are forward references.
- The template is the authority on what is optional, and the marker is literal so that deciding
  about it is a search, not a judgement. If a field in `scripts/models.py` has no marked line in
  the template, other than `reviews`, which reviewers add later and a new protocol never carries,
  the two have drifted; report that rather than guessing which is right.
- An issue's "frontmatter starting point" is an author's answer to some of the questions above,
  not to all of them. The citation questions are still asked, and a citation the issue says to
  cite "only as an application" is not a `protocol_citation`.
- A new content repository's validation stays red until the placeholder citation is replaced.
  That is intended; the one thing the template cannot supply is the citation.
