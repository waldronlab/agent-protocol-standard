---
name: validate-protocol
description: Run the standard's validator on a protocol, fix what is mechanically wrong, and state the judgement calls that remain without guessing at them
version: 0.1.0
category: protocols
author: waldronlab
tags: [protocol, validation, conformance, frontmatter, history]
---

# validate-protocol

Runs `scripts/validate_protocol.py` on a protocol, reads every error it reports, fixes the ones
that have exactly one correct answer, and names the rest. The validator says what is wrong; this
skill says what to do about it. It never invents a DOI, an author, a date, a review, or a status.

## Usage

- "Validate the shannon-diversity protocol"
- "Fix whatever the validator complains about in protocols/prevalence-filtering"
- "Why does CI reject my protocol?"

## Prerequisites

- A local checkout of `waldronlab/agent-protocol-standard` for `scripts/validate_protocol.py`,
  with Python 3.10+, `pydantic`, and `pyyaml`.
- A local checkout of the content repository holding the protocol.
- `GITHUB_REPOSITORY` set to the content repository's `owner/name`. Without it the validator
  falls back to the `origin` remote of the directory it runs from. Run from the standard checkout,
  that resolves to the standard's own name, so same-repository dependencies are never checked and
  no warning says so. The `[WARN]` appears only when neither source yields a name.

## Process

### 1. Locate the standard and the protocol

1. Find the standard checkout (ask if it is not obvious) and the content repository's
   `protocols/` directory. The protocol lives at `protocols/<name>/protocol.md`, with optional
   `protocols/<name>/tests/`.
2. Note the content repository's `owner/name` for `GITHUB_REPOSITORY`.

### 2. Run the validator

From the standard checkout:

```sh
GITHUB_REPOSITORY=<owner/name> python3 scripts/validate_protocol.py <path to protocols dir>
```

`No '<dir>' directory found` and `No 'protocol.md' files found under` mean the path is wrong:
fix the argument and re-run; they are not errors in the protocol. Keep the full output. The
validator checks every `protocol.md` under the directory, so other protocols' errors appear too;
work on the one the user asked about and report the others.

### 3. Classify every error

Each `[ERROR]` line is either **mechanical** (one correct fix, apply it and say what changed) or
**judgement** (state the choice in one or two sentences and stop). Where unsure, treat it as
judgement. The tables quote the distinguishing words of each message. Schema errors print as
`'<field>' Value error, <message>` or `'<field>' Input should be ...`; nested fields read
`authors.0.orcid` or `reviews.2.status`, where the number is the zero-based position in the list.

**Order matters.** Some errors mask others, so fix the first of these, re-run, and only then read
anything later:

- A `Failed to parse YAML frontmatter` error hides every other check.
- When the frontmatter fails schema validation, every review block also reports `has no matching
  entry in the frontmatter 'reviews' array`, because the validator could not read `reviews`.
- A missing, duplicated, or entry-less `## History & Reviews` stops all History checks.
- A version missing `#### Reviews` is skipped past, so its review-block errors appear only after
  the subsection exists.

#### Frontmatter

| Message | Class | What to do |
|---|---|---|
| `Failed to parse YAML frontmatter: <yaml error>` | mechanical if the repair is quoting a value or fixing indentation and the visible text stays the same; else judgement | Quote the value (an unquoted colon or `#` in `description` is the usual cause) or replace tabs with spaces. Anything that changes what the text says is judgement. |
| `Failed to parse YAML frontmatter: missing or invalid` / `document is not a mapping` | judgement | There is no frontmatter block, or it is not a key-value mapping. Say what is at the top of the file and stop. |
| `Field 'publication_doi'`, `'protocol_doi'`, or `'repository_doi'` `was renamed to 'Y'` | mechanical | Rename the key, keep the value. If the value is `null`, delete the field instead. |
| `Field 'citation'` or `'method_citation'` `was renamed to 'method_origin_citation'` | mechanical if `protocol_citation` is already present; else judgement | Rename the key. Otherwise ADR 0014 inverted which citation is required, and the old value usually answers "who published these instructions", which is now `protocol_citation`. Quote the old value and ask which of the two questions it answers. |
| `Deprecated 'citations' field found` | judgement | A list cannot become one `method_origin_citation`. Say which entries it holds; the author picks one or omits the field (ADR 0014). |
| `Explicit null for 'type'` / `'type' Input should be 'atomic' or 'composite'` | mechanical | Delete the key; the standard derives `type` from `protocols_used` when it is absent. If the value is a case variant such as `Atomic`, lower-case it instead. |
| `Explicit null for 'method_origin_citation'` / `must be omitted when unknown` | mechanical | Delete the field. Absence is the correct value when no method was originated. |
| `'type: atomic' cannot declare 'protocols_used'` | judgement | Either the type or the dependency list is wrong; which one is a question about the protocol. |
| `'type: composite' requires a non-empty 'protocols_used'` | judgement | Same: the composite composes nothing named, or it is atomic. |
| `'name' must be kebab-case` / `Directory name 'X' does not match protocol name` / `'name' Input should be a valid string` / `Missing required fields: name` | mechanical if the directory name is kebab-case; else judgement | Set `name` to the directory name, which is the protocol's identity. Renaming a non-kebab-case directory changes the protocol's URL, so stop and say so. |
| `Missing required fields: version` or `date` | mechanical if the top `### Version X.Y.Z (YYYY-MM-DD)` heading parses; else judgement | Copy the value from the heading. |
| `Missing required fields:` any other top-level field | judgement | `description`, `authors`, `status`, `protocol_citation` are facts about the protocol; name the field and stop. |
| `'date' Value error, Must be YYYY-MM-DD date` / `Must be a YYYY-MM-DD date` | mechanical if the value is unambiguous, such as a timestamp (the second wording) or `2026/03/01`; else judgement | Rewrite as `YYYY-MM-DD`. `03/04/2026` is judgement. |
| `'version' Input should be a valid string` | judgement | YAML read `version: 1.0` as a number. Quoting it gives `"1.0"`, which is not semver either; ask what the third component is, or copy the top History heading if it parses. |
| `'version' Value error, must not be blank` | mechanical if the top History heading parses; else judgement | Copy the version from the heading. |
| `'description' Value error, must not be blank` | judgement | The description is the author's statement of what the protocol does. |
| `'status' Input should be 'draft', 'stable', 'deprecated' or 'superseded'` | judgement | `stable` is an assertion by the authors (ADR 0013). Say what value is there and stop. |
| `Malformed ORCID` on `authors.N.orcid` | mechanical if the value is an ORCID URL or has surrounding whitespace; else judgement | Strip to the bare identifier. Never correct a digit. |
| `'authors.N' Input should be a valid dictionary or instance of Author` | mechanical | `authors` is a list of strings. Rewrite each as `- name: <string>`. |
| `'authors' Value error, must be a non-empty list of objects` / `'authors' Input should be a valid list` | judgement | The list is empty or is a single scalar; who the authors are is a fact about the protocol. |
| `'reviews.N.date'`, `'reviews.N.status'`, `'reviews.N.orcid'` errors / `Missing required fields: reviews.N.<field>` | mechanical if the `**Review by` block for that reviewer and version carries a valid value denoting the same thing; else judgement | Copy the block's value, normalised as the review-block rows below describe (`Approved` to `approved`, `15 Jan 2026` to `2026-01-15`, ORCID URL to bare ID). A different value, or no block, is judgement. |
| `must be a DOI ('10.1000/xyz') or a PubMed ID` | mechanical if the value is a DOI URL, a `doi:` prefix, or `PMID: 123` with a space; else judgement | Strip to the bare form. Free text such as `see the HUMAnN 4 paper` is judgement. Do not look the paper up and fill it in. |
| `is still the template placeholder '10.0000/replace-with-a-real-doi'` | judgement | For `protocol_citation`: which publication describes these instructions, or the protocol's own `artifact_doi` or `collection_doi` if none does. For `method_origin_citation`: whether the protocol originates a method at all; if not, omit (ADR 0014). |
| `Dependent protocol 'X' not found at` | judgement | The name, the repository, or the version may be wrong, or the dependency may be missing. List the directories under `protocols/` with similar names. |
| `[WARN] Cannot determine this repository` | mechanical | Set `GITHUB_REPOSITORY` and run again. |

#### Body sections

| Message | Class | What to do |
|---|---|---|
| `Missing required '## Materials' section` | mechanical if a section plainly holds the inputs under another name (`## Inputs`, `## Requirements`, `## Prerequisites`); else judgement | Rename the heading. If no such section exists, what the protocol consumes and what conditions apply (ADR 0017) is scientific content. |
| `Missing required '## Steps' section` | mechanical if the procedure is under another name (`## Procedure`, `## Method`); else judgement | Rename the heading. |
| Either of the above when the heading is visibly there | mechanical if the unclosed fence has one plausible closing point, the blank line before the next prose or heading; else judgement | An unclosed code fence hides everything after it; a closing fence followed by text does not close. Close the fence there. Deciding which lines are code is judgement. |
| `'## Steps' contains no '### Step' heading` | mechanical if the steps are there as `### 1.`, `### Validate`, or similar; else judgement | Retitle each as `### Step N: <title>`, keeping the title. If the only `### Step` headings sit under a later `## ` section, moving that boundary is judgement. |

Materials and Steps content is never edited beyond heading names. Which inputs a protocol needs,
which conditions are *must* or *should*, and what a step does are the author's.

#### History & Reviews

| Message | Class | What to do |
|---|---|---|
| `Missing required '## History & Reviews' section` | mechanical if a `## History` or `## Changelog` section already holds `### Version` entries; else judgement | Rename the heading. Otherwise the section needs a `#### Changes` entry stating what this version is, which only the author can write. |
| `Found multiple '## History & Reviews' headings` | judgement | Which one is the record. |
| `'## History & Reviews' has no '### Version X.Y.Z (YYYY-MM-DD)' entries` | judgement | The section exists but records no release. Say so and stop. |
| `must be the last section, but '## X' appears after it` | mechanical | Move the later section above `## History & Reviews`. |
| `Malformed version heading` | mechanical if a semver version and a `YYYY-MM-DD` date can both be read from the line and nothing else is on it, such as `### Verson 1.0.0 (2026-01-15)`; else judgement | Rewrite as `### Version X.Y.Z (YYYY-MM-DD)`. A date in another form (`01/15/2026`), a missing part, or extra words after the date (`initial release`) is judgement: dropping words loses content and moving them into Changes is authoring. |
| `is not semantic versioning` / `Invalid date 'X' in heading` | judgement | What the version or date should be. |
| `Top entry ... is version 'X', but frontmatter declares version 'Y'` | mechanical if the frontmatter version is lower than the heading or is not semver; else judgement | Set frontmatter `version` to the heading: the author forgot to update it. When the frontmatter is ahead, the author bumped the version and has not written the History entry; setting it back would silently revert the bump. Say that an entry with `#### Changes` is needed and stop. |
| `Top entry ... is dated 'X', but frontmatter declares date 'Y'` | mechanical if the version row above is mechanical or absent; else judgement | Set frontmatter `date` to the heading date, which is the release date. When the frontmatter version is ahead, the date belongs to the unwritten entry; leave both. |
| `Version entries must be in descending order` | mechanical | Reorder the `### Version` entries, each with its whole body, newest first. |
| `Duplicate version entry` | judgement | Two bodies claim one version. |
| `Version X is missing a '#### Changes' subsection` | mechanical if bullet points sit directly under the version heading; else judgement | Insert `#### Changes` above them. Otherwise what changed is the author's statement. |
| `has an empty '#### Changes' subsection` | mechanical if the subsection holds `* ` bullets or a numbered list; else judgement | The validator accepts only `- ` bullets; change the marker and nothing else. Paragraph text or nothing at all is judgement. Never write the bullets. |
| `Version X is missing a '#### Reviews' subsection` | mechanical if nothing review-like sits after Changes and frontmatter `reviews` has no entry with that `protocol_version`; else judgement | Add `#### Reviews` after Changes containing `*No reviews yet.*`. If review-like text is there, add only the heading above it. If the frontmatter lists a review for this version, the placeholder would be a false provenance claim; stop. |
| `has no review blocks; its '#### Reviews' subsection must contain '*No reviews yet.*'` | mechanical if the subsection is empty and frontmatter `reviews` has no entry for that version; else judgement | Add the placeholder line. Text the regex did not recognise (`Review by Jane` without `**`) is a review the author must reformat; a frontmatter entry for the version means a review exists. |
| `has review blocks but is also marked '*No reviews yet.*'` | mechanical | Delete the placeholder line. |
| `Malformed review heading` | mechanical if the reviewer name is evident, such as a missing closing `**`; else judgement | Rewrite as `**Review by <Name>**`. |
| `Review by 'X' ... is missing a '- **Date:**' line` / `'- **Status:**' line` | mechanical if the frontmatter `reviews` entry for that version and reviewer has the value; else judgement | Copy it. |
| `must give a backtick-quoted status` | mechanical if the Status line holds one of the four values without backticks; else judgement | Wrap the existing word in backticks. Do not fetch a value from the frontmatter. |
| `is missing a '- **Notes:**' line` | judgement | The notes are the reviewer's words. |
| `has invalid status 'X'` (review) / `has an invalid date` (review) / `Invalid ORCID ... in review block` | mechanical if the value denotes the same thing as a valid frontmatter value (`Approved` versus `approved`, `15 Jan 2026` versus `2026-01-15`, ORCID URL versus bare ID); else judgement | Replace it with the frontmatter value. `accepted` versus `approved` is two claims, not a formatting slip. The paired `disagrees` message for the same field clears with the fix. |
| `Review block for version X, reviewer 'Y' has no matching entry in the frontmatter 'reviews' array` | mechanical if no `Frontmatter review ... has no matching block` error exists for the same version and the block's Date and Status are valid; else judgement | Add the entry from the block: `name`, `date`, `protocol_version`, `status`, and `orcid` when the block has one. A paired error means one reviewer spelled two ways; say both spellings and stop rather than duplicate the reviewer. |
| `Frontmatter review for version X, reviewer 'Y' has no matching '**Review by ...**' block` | judgement | With a paired `Review block ... has no matching entry` for that version, it is a spelling mismatch; say both. Otherwise the block needs a `Notes` line that exists nowhere. Offer the Date and Status from the frontmatter and stop. |
| `declares protocol_version 'X', which has no matching entry` | judgement | Which version was reviewed. |
| `disagrees between the markdown block and the frontmatter: <field> is 'X' in the section but 'Y' in 'reviews'` | judgement | Two values, one of them right. Say both and stop. |

#### Tests

| Message | Class | What to do |
|---|---|---|
| `'tests' exists but is not a directory` | judgement | A file named `tests` sits where the directory belongs. |
| `tests/X/test.yaml: failed to parse YAML` / `document is not a mapping` | mechanical if the repair is quoting or re-indenting and the visible text stays the same; else judgement | Same rule as the frontmatter parse error. |
| `tests/X/test.yaml: 'name' is 'A' but the directory is 'B'` / `'name' must be lower-case words joined by - or _` | mechanical if the directory name is valid; else judgement | Set `name` to the directory name. |
| `only test directories belong directly under tests/` | mechanical if a test's `test.yaml` names the stray file by path; else judgement | Move it into that test's directory. Never delete it. |
| `names 'X', which does not exist in tests/Y/` | judgement | The file is missing or the path is wrong. |
| `no test.yaml; every directory under tests/ is a test` / `tests/ exists but contains no tests` | judgement | Remove the directory or write the test. |
| `unsupported value of type date` or `datetime` | mechanical | Quote the text exactly as written in the file so YAML reads it as a string. |
| Any other `test.yaml` schema message: `missing required field`, `needs evidence`, `a test that checks nothing is invalid`, `must be a CSV table`, `may not use the reserved key`, `'expected_warning' must not be blank`, `a file is either {path} or {url, sha256}`, `'header' is only allowed on`, `mode 'diagnostic' puts expectations under each accepted outcome` | judgement | Each is a statement about what the test expects. Quote the message and stop. |

### 4. Apply the mechanical fixes

Edit `protocol.md` and `test.yaml` in place. Record each change as "file: what was changed, from
what to what". Do not touch anything the tables above do not name: no edits to Materials or Steps
text, no edits to `#### Changes` bullets or review Notes, no new History entries, no version
bumps, no values the document does not already contain.

### 5. Re-run until only judgement calls remain

Run the validator again after every round of fixes. A fix can expose errors that were masked,
most often review errors hidden behind a frontmatter failure or a missing `#### Reviews`. Stop
when the output is `[OK] Valid.` or every remaining `[ERROR]` is a judgement call you have already
stated. Never report done while an error you could fix remains.

### 6. Report

Write the report in the output format below. Other protocols under the same directory that
failed are listed by name at the end, without fixes; the user asked about one protocol.

## Output Format

1. The validator's first run, verbatim.
2. **Fixed**: one line per mechanical change, naming the file and the before and after values.
3. **Needs a decision**: one entry per remaining error, quoting the validator's message and
   stating the choice in one or two sentences. No recommendation where the answer is a fact only
   the author knows.
4. The validator's final run, verbatim, so the reader can see what is still reported.
5. A closing line naming this skill and its version:

   > 🛠️ Skill executed: `validate-protocol` v`0.1.0` (`waldronlab/agent-protocol-standard`)

## Notes

- This skill checks conformance to `PROTOCOL_STANDARD.md`, not that the protocol works. Running
  a protocol's tests is `test-protocol`.
- Changing a protocol's version, with a new History entry and `#### Changes`, is `update-protocol`
  (waldronlab/agent-protocol-standard#36). Writing a protocol from scratch is `create-protocol`
  (waldronlab/agent-protocol-standard#35). This skill fixes a document that already exists and
  leaves its version where it is.
- The validator strips code fences and the frontmatter before looking for headings, so a heading
  inside a fence is invisible to it. An unclosed fence is the usual cause of a "missing section"
  error on a document that visibly has the section.
- The citation rules come from ADR 0014: `protocol_citation` is required and names who published
  these instructions; `method_origin_citation` is optional and is omitted, not nulled, where no
  method was originated. `## Materials` conditions follow ADR 0017. Tests follow ADR 0016.
