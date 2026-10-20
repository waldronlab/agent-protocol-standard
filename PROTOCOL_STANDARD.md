# Protocol Standard

This document defines the standard for publishing AI agent-compatible protocols in any repository federated into this registry. Conforming to this standard ensures that your protocol can be discovered, executed, and correctly cited by the `protocol-runner` agent skill.

## File Structure

Each protocol must be housed in its own directory under `protocols/`. The directory name must exactly match the `name` field in the protocol's YAML frontmatter.

The protocol file itself must be named `protocol.md` and placed directly within its directory.

Example:
`protocols/humann4-sgb-aggregation/protocol.md`

## The `protocol.md` Format

A protocol file consists of two parts:
1. **YAML Frontmatter**: Machine-readable metadata (provenance, DOIs, dependencies).
2. **Markdown Content**: Human-readable instructions for the procedure.

## Protocol Types: Atomic vs. Composite

Protocols follow a modular two-tier design:

1. **Atomic Protocols**:
   * Implement a single, focused methodological operation.
   * **At most 1 `method_origin_citation`:** A single DOI/PMID naming the primary literature where the method was originally published — the paper that *proposed* it, not one that applied it. Omitted where the protocol originates no method; see [The two citation fields](#the-two-citation-fields).
   * Do not compose other protocols (`protocols_used: []`).
2. **Composite Protocols**:
   * Implement multi-step workflows or end-to-end pipelines by composing atomic protocols.
   * **Composition:** List all constituent atomic protocols in `protocols_used`.
   * **Provenance:** Automatically inherit and aggregate the `method_origin_citation` of every constituent atomic protocol upon execution. Most composites add no `method_origin_citation` of their own — they sequence methods rather than proposing one, and a paper describing the pipeline belongs in `protocol_citation`. Where the composition is *itself* a published method, `method_origin_citation` names the paper that proposed it.

### The two citation fields

Each answers one question. Answer them separately; do not define them against each other.

| Field | The question it answers | Example |
|---|---|---|
| `protocol_citation` *(required)* | **Who published these instructions?** | Pasolli et al. 2016, for a protocol written from that paper's procedure |
| `method_origin_citation` *(optional)* | **Who invented the method?** | Breiman 2001, for random forests |

**Where no publication describes the procedure, `protocol_citation` names this protocol's own DOI.**
This is the exception, and it should be rare: a protocol usually encodes a procedure someone has
published, and that paper is the answer. Reach for self-citation only after looking for the paper and
concluding there is none. When it does apply, it is a claim rather than a gap:

Compare against whichever DOI the protocol actually has — the protocol's own DOI — `artifact_doi` where it has one, otherwise `collection_doi`:

*   `protocol_citation` matches neither of this protocol's own DOIs — an external publication describes
    this procedure.
*   `protocol_citation` equals this protocol's own DOI — **a first definition, published here.**

An absent field could mean either of those, or that nobody filled it in. Requiring the field forces the
distinction to be stated, and CI can check the answer is a resolvable identifier.

**A collection with no DOI cannot yet host a first definition.** There is nothing for such a protocol to
cite: the procedure is unpublished and so is the collection. Deposit the collection — Zenodo mints a DOI
from a GitHub release — and write that DOI into `collection_doi`. Until then, only protocols transcribed
from an existing publication can conform. This is a deliberate consequence: a repository claiming to hold
citable protocols should be citable itself.

Use the **concept** DOI rather than a version DOI. A version DOI names the exact bytes, which sounds
more precise, but it cannot be written into a protocol before the release that mints it exists. Name,
version, and concept DOI together identify the exact protocol without that circularity.

**One method can be the basis of several protocols.** Random forest classification has a single origin,
but a published microbiome parameterization and a different published parameterization are genuinely
different procedures producing different results from the same inputs. Each is its own protocol. They
share a `method_origin_citation` and are distinguished by their `protocol_citation`.

**Not every protocol originates a method, and it is wrong to invent one.** A protocol documenting how to
build a tool's reference database performs no method that anybody proposed. Omit
`method_origin_citation` there; a field filled in to satisfy a validator is worse than an absent one.

Both fields must be a DOI (`10.1000/xyz`) or a PubMed ID (`PMID:12345678`) — something a reader or an
agent can resolve. Free text naming a paper is not enough, and neither is the placeholder the starter
protocol in `template/` ships: a new repository's validation stays red until a real citation replaces
it, because that is the one thing the template cannot supply.

### YAML Frontmatter Schema

All fields must use `snake_case`.

**Required Fields:**
*   `name`: (String) A unique, kebab-case identifier for the protocol.
*   `description`: (String) A brief, one-sentence summary of the protocol's purpose.
*   `version`: (String) Semantic versioning (e.g., "1.0.0").
*   `authors`: (Array of Objects) At least one author must be specified.
    *   `name`: (String) Author's name.
    *   `orcid`: (String, Optional) Author's ORCID. Recommended rather than required, but validated
        when present: a malformed ORCID is a claim about a named person that resolves to nobody.
*   `date`: (Date: YYYY-MM-DD) Creation or last modification date.
*   `protocol_citation`: (String) DOI or PMID answering **who published these instructions**. Where a
    publication describes this procedure as written here — parameters included — name it. Where none
    does, name this protocol's own DOI: `artifact_doi` if it has one, otherwise `collection_doi`.
*   `status`: (String: `draft` | `stable` | `deprecated` | `superseded`) The protocol's own lifecycle.
    *   `draft`: still being worked out; expect it to change.
    *   `stable`: there is reasonable confidence in the protocol and no further changes are immediately
        planned. It is an assertion by the authors about the protocol's readiness, not a count of reviews
        — the `reviews:` feed records what others think of it, separately.
    *   `deprecated`: should not be used. The runner refuses to execute a deprecated protocol.
    *   `superseded`: replaced by another protocol, which the `## Notes` section should name.

**Optional Fields:**
*   `type`: (String: `atomic` | `composite`) Protocol architectural type (defaults to `atomic` if `protocols_used` is empty).
*   `license`: (String) License identifier (e.g., "CC-BY-4.0").
*   `method_origin_citation`: (String) DOI or PMID answering **who invented the method** — the primary literature where it was *first proposed*, not a paper that applies an already-established method. Omit it entirely where the protocol originates no method: documenting how to operate a tool is not a method someone proposed. A composite may carry one where the composition was itself published as a method.
*   `artifact_doi`: (String) DOI identifying **this document** as a citable artifact (e.g., from protocols.io).
*   `collection_doi`: (String) DOI identifying the **repository or collection** housing this protocol (e.g., a Zenodo record).
*   `upstream_repositories`: (Array of Strings) URLs to source code repositories containing upstream tools or pipeline implementations.
*   `database_urls`: (Array of Strings) URLs for pre-computed, reference, or previous versions of database artifacts.
*   `protocols_used`: (Array of Objects) Sequential execution dependencies / constituent protocols (for composite workflows).
    *   `name`: (String) Name of the dependency protocol.
    *   `repository`: (String) The repository hosting the dependency.
    *   `version`: (String) Exact version required.
*   `key_packages`: (Array of Strings) Primary R/Bioconductor, Python, or software packages used.
*   `category`: (String) High-level domain category.
*   `tags`: (Array of Strings) Searchable keywords.
*   `reviews`: (Array of Objects) Human expert reviews of this protocol, newest first. Machine-readable
    counterpart of the review blocks in the `## History & Reviews` section; every entry must have a
    matching markdown block and vice versa. Omit the field entirely if the protocol has not been
    reviewed.
    *   `name`: (String) Reviewer's name.
    *   `orcid`: (String, Optional) Reviewer's ORCID. Optional in exactly the same way as it is for
        `authors`; when present it must match `^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$`.
    *   `date`: (Date: YYYY-MM-DD) The date the review was given.
    *   `protocol_version`: (String) The protocol version that was reviewed. This is frequently
        *older* than the current `version:` — a reviewer approves a specific release, and the
        protocol may have moved on since. It must correspond to a version documented in
        `## History & Reviews`.
    *   `status`: (String) One of the review statuses defined below.

#### Review Statuses

The `status` of a review is a controlled vocabulary, so that agents across the federation can
interpret reviews from repositories they have never seen before:

*   `approved`: A domain expert has read and vetted the protocol for scientific soundness.
*   `verified-with-benchmark`: A domain expert has actively executed the protocol and verified the
    outputs against a benchmark or expected result.
*   `changes-requested`: A domain expert has reviewed the protocol and found it broadly sound, but
    has requested revisions before it can be considered approved.
*   `deprecated`: A domain expert has reviewed the protocol and found it scientifically invalid,
    obsolete, or superseded.

Note that this vocabulary is **distinct from the protocol-level `status:` field**, which describes
the protocol's own lifecycle (`draft` | `stable` | `deprecated` | `superseded`) rather than any
individual's assessment of it.

There is deliberately no "unreviewed" status. Every status is a claim made by a named reviewer, so a
version that nobody has reviewed simply has no entry. A machine reader determines that the current
release is unreviewed when no `reviews:` entry carries a `protocol_version` equal to `version:`.


### Markdown Content Structure

The markdown body must contain a `## Materials` section and a `## Steps` section with at least one
`### Step` heading, and `## History & Reviews` must be the last section. A document with metadata but no
materials and no steps is not a protocol, however complete its frontmatter is, and CI rejects it.

The remaining structure is a recommendation rather than a requirement, and follows it for compatibility
with future export tools such as protocols.io integration:

```markdown
# [Title of Protocol]

Brief overview (1-2 sentences).

## Materials

- **Software & Repositories:**
  - `ToolName` ([Repository URL]) — Description/version.
- **Databases & Reference Data:**
  - `DatabaseName` ([Database URL]) — Baseline reference or previous build URL.

## Steps

### Step 1: [Action]
Explanation and code...

### Step 2: [Action]
Explanation and code...

## Notes

Additional context, caveats, computational/HPC requirements, or troubleshooting tips.

## History & Reviews
<!-- Newest versions at the top -->

### Version 1.0.0 (2026-08-08)

#### Changes
- Initial protocol creation.

#### Reviews
*No reviews yet.*
```

### History & Reviews

Every protocol must end with a `## History & Reviews` section. It is a NEWS.md-like feed serving two
purposes: recording what changed in each release, and recording which human experts vetted which
release. Keeping it inside `protocol.md` means a protocol remains a single self-contained, portable
file.

The section must be the **last** `##` section of the file, and its version entries are ordered
**reverse-chronologically, newest at the top**. Include the template comment beneath the heading so
that human authors and AI agents prepend rather than append:

```markdown
## History & Reviews
<!-- Newest versions at the top -->

### Version 1.1.0 (2026-08-18)

#### Changes
- Updated `MMseqs2` clustering parameter from `--min-seq-id 0.8` to `--min-seq-id 0.9` for UniRef90 consistency.
- Added HPC memory requirements to the Notes section.

#### Reviews
*No reviews yet.*

### Version 1.0.0 (2026-08-08)

#### Changes
- Initial protocol creation.

#### Reviews

**Review by Jane Doe ([0000-0002-1825-0097](https://orcid.org/0000-0002-1825-0097))**
- **Date:** 2026-08-10
- **Status:** `verified-with-benchmark`
- **Notes:** I ran this protocol against the new MetaPhlAn 4.2 SGB release using the mock community
  dataset. The memory footprint on our SLURM cluster peaked at 120GB, which is within expected bounds.

**Review by John Roe**
- **Date:** 2026-08-08
- **Status:** `changes-requested`
- **Notes:** The method is sound, but Step 2 needs explicit parameter values before I can recommend it.
```

Rules:

*   Every level-3 heading in the section is a **version heading**, of the form
    `### Version X.Y.Z (YYYY-MM-DD)`. The date is the **version's release date** — the value of
    frontmatter `date:` when that version was published — *not* the date the entry was written.
*   The **topmost version entry must match the frontmatter `version:` and `date:` fields**, since it
    describes the current release. Bumping `version:` therefore always means adding a new entry.
*   Each version entry has a `#### Changes` subsection listing what changed as **at least one bullet
    point**, and a `#### Reviews` subsection.
*   **Review blocks** are headed `**Review by <Name>**`, optionally followed by a linked ORCID:
    `**Review by Jane Doe ([0000-0002-1825-0097](https://orcid.org/0000-0002-1825-0097))**`. Each
    requires a `- **Date:**` line, a `- **Status:**` line (backticked, from the vocabulary above),
    and a `- **Notes:**` line. Notes are free text and peer-review-style detail is encouraged.
*   Every review block must have a corresponding entry in the frontmatter `reviews:` array whose
    `protocol_version` is the version it appears under, and every frontmatter entry must have a
    corresponding block. Where the two representations record the same fact — the date, the status,
    and the ORCID when the markdown gives one — they must agree, so that a machine reader and a human
    reader of the same protocol never draw different conclusions.

A brand-new protocol, or a release nobody has reviewed yet, still carries the section — only the
`#### Reviews` body is a placeholder, and the `reviews:` frontmatter field is omitted entirely:

```markdown
## History & Reviews
<!-- Newest versions at the top -->

### Version 1.0.0 (2026-08-08)

#### Changes
- Initial protocol creation.

#### Reviews
*No reviews yet.*
```

These rules are enforced by `scripts/validate_protocol.py`, which runs on every pull request.

## Tests

*Proposed in ADR 0016. The validator, the checker, and the `test-protocol` skill described here
are not yet implemented; until they are, CI does not check `tests/` and the commands below do not
exist. This notice is removed when they do.*

A protocol may carry tests: known inputs with the outputs a correct execution produces. Tests are
optional. When present they live beside the protocol, one directory per test:

```text
protocols/<name>/
├── protocol.md
└── tests/
    └── <test-name>/
        ├── test.yaml
        ├── input.csv        # local data referenced from test.yaml
        └── retained.csv     # an expected output file
```

### `test.yaml`

```yaml
name: variance_rows                 # must match the directory name
description: Unbiased variance filtering with features in rows.
inputs:                             # everything the executor is given
  data: {path: input.csv}           # a file: path, or url + sha256 (below)
  filter: variance
  theta: 0.4
  tie_breaker: feature_id_ascending
expected_outputs:                   # what a correct execution produces
  summary:
    A: 0
    B: 1.3333333333333333
    C: 1.3333333333333333
    D: 33.333333333333336
    E: 48
  removed_features: [A, B]
  retained_matrix: {path: retained.csv}   # a file, compared as a table
evaluation:
  mode: exact                       # exact | diagnostic
  numeric_tolerance: 1.0e-12        # optional, default 0
```

*   `name`: (String) Kebab or snake case; must equal the directory name.
*   `description`: (String) One sentence.
*   `inputs`: (Mapping) Parameter values and data files. Keys are the protocol's own parameter
    names where it has them.
*   `expected_outputs`: (Mapping) Values and files a correct execution produces. Keys are the
    quantities the protocol says to record.
*   `evaluation`: (Mapping) `mode` is required. `numeric_tolerance` is an absolute tolerance applied
    to every numeric comparison, default `0`.

A **file** is a mapping with exactly one of two shapes: `{path: <relative path>}`, inside the test
directory with no `..`, or `{url: <https URL>, sha256: <hex digest>}`. Any other string is a
literal value, so `data: input.csv` is the string `input.csv`, not a file. The remote form is for
data too large to commit; the digest is verified after download and a mismatch fails the test. Keep
local files small. A table slot in `expected_outputs` may add `header: withheld` when the column
set is itself part of the answer, as in a test that selects columns; the executor then names the
columns as the protocol directs and the checker compares the header as it compares everything
else. The default is to show the header in the result shape.

### Evaluation modes

**`exact`**: every entry in `expected_outputs` must be present in the result and match.

**`diagnostic`**: the input violates a requirement the protocol states, and the test checks what the
executor does about it. `evaluation.accepted_outcomes` lists the outcomes that count as correct.
The top-level `expected_outputs` is omitted; each outcome carries its own evidence instead, at
least one of:

*   `expected_outputs`, compared as in `exact` mode when the executor reports that outcome;
*   `expected_absent`, keys that must not appear in the result. This is how a refusal is checked:
    an executor that refused did not produce the protocol's outputs.

An outcome with neither, or with both empty, is invalid, because a label alone is the executor's
word. The keys
`outcome` and `observation` are reserved for the executor's report and may appear in neither
`expected_outputs` nor `expected_absent`; the validator rejects a test that uses them.

```yaml
evaluation:
  mode: diagnostic
  accepted_outcomes:
    - outcome: orientation_corrected
      expected_outputs:
        removed_features: [A, B]
        retained_features: [C, D, E]
    - outcome: refused_for_orientation
      expected_absent: [removed_features, retained_features, retained_matrix]
```

### The result contract

An executor, human or agent, is given `inputs`, the **result shape**, and, unless the run is
deliberately unguided (`invocation.kind: unguided` in the run record), `protocol.md`. The result
shape is the top-level keys of `expected_outputs` with every value withheld, each file slot with
its format and, for a table, its header row in order unless the slot says `header: withheld`, the
evaluation mode, and in `diagnostic`
mode the outcome labels with the keys each one expects present or absent. Top-level keys are the
quantities the protocol says to record and are fixed by it. The keys of any nested mapping are
data, such as feature identifiers, and are withheld: the shape shows a nested mapping as
`{<key>: <type>}`, because its membership can itself be the answer. Data rows and scalar values
are never included. `scripts/check_test_result.py --shape <tests directory>` prints the shape of
every test, or of one with `--test <name>`.

The executor performs the protocol in any language and writes its results into a **results
directory** of its choosing, one subdirectory per test named after the test, each holding
`result.yaml` and any output files. It does not read `expected_outputs` itself.

*   In `exact` mode, `result.yaml` has one key per key of `expected_outputs`. A file slot is filled
    with `{path: <file in that test's result subdirectory>}`.
*   In `diagnostic` mode, `result.yaml` has `outcome`, one of the accepted outcomes, and
    `observation`, one sentence saying what was found. If that outcome carries `expected_outputs`,
    their keys follow.

`scripts/check_test_result.py <tests directory> <results directory>` compares every test that has a
result subdirectory, or one with `--test <name>`, and is the only thing that decides pass or fail. A
test with no result subdirectory is reported as not run, which is neither pass nor fail. Its
comparison rules:

*   Numbers match within `numeric_tolerance`. Strings, booleans and nulls match exactly. Lists match
    element by element, in order. At the top level of `result.yaml`, a key missing from the result
    fails and a key present only in the result is ignored, so an executor may record more than the
    test asks. A nested mapping must have exactly the expected key set, because its membership is
    data and an extra feature is a wrong answer.
*   Files are compared as tables. The only table format is CSV: UTF-8, comma delimited, double-quote
    quoting as in RFC 4180, with a header row. A file slot compared as a table must have a name
    ending in `.csv`, in `path` or in the URL; the validator rejects anything else, and no other
    file format is defined yet.
*   Two tables match when the header rows are identical as strings, the rows are in the same order,
    and every cell matches. The first column is the row identifier and is compared as a string, as
    is the header, so `001` and `1` differ. In every other column a cell is numeric, within
    tolerance, when the expected cell parses as a number, and a string otherwise. An empty cell is a
    missing value and matches only an empty cell.

### The run record

A run is not a review and adds nothing to the protocol. The checker writes `run.yaml` at the top of
the results directory, one record covering every test it compared, overwriting any earlier record
there:

```yaml
run_record: 1                   # schema version of this record
protocol: independent-filtering-variance
version: 1.2.1
repository: waldronlab/agent-protocols
protocol_commit: 844ce92        # commit the protocol and tests were read at
started: 2026-10-18T14:02:11Z   # UTC timestamps, from the executor
finished: 2026-10-18T14:09:40Z
executor:
  agent: claude-code            # the agent or person that performed the protocol
  harness: Claude Code 2.1.0    # the agent software and version, distinct from the model
  model: claude-fable-5-1       # omitted for a human executor
  language: R                   # what the execution was written in, if known
  invocation:                   # how the protocol reached the agent
    kind: skill                 # skill | in-context | unguided
    skill: test-protocol 0.1.0  # name and version, for kind: skill
  prompt: |                     # verbatim text that started the run
    Run the tests for independent-filtering-variance.
checker: check_test_result.py 0.1.0
tests:
  - name: variance_rows
    result: pass                # pass | fail
  - name: mean_columns
    result: pass
    outcome: orientation_corrected   # diagnostic mode only
```

The executor writes `executor.yaml` at the top of the results directory before invoking the checker,
containing the `executor` block and the `started` and `finished` timestamps; the checker copies
them into the record and fills the rest from the test directory and its own version. A missing
`executor.yaml` is an error, not a guess. `protocol_commit` is the commit of the checkout the
tests directory sits in; if the protocol directory has uncommitted changes, the checker records
no commit and marks the run `uncommitted: true`, so a record never names a commit that does not
contain what was executed. Within `executor`, `agent` is required; `harness`,
`model`, `language`, `invocation`, and `prompt` are optional, since a human executor has no prompt
and a prompt may hold paths or data its author does not want shared. An agent running a skill
fills all of them. `invocation.kind` distinguishes a run through a skill, a run with the protocol
text supplied in context, and a run given no protocol at all; two runs that differ only there are
different experiments. Additional keys, at the top level of `executor.yaml` or
under `executor`, are permitted and preserved, so a study that records cost, token counts,
attempts, or an experimental condition adds them without a schema change. The keys the checker
writes itself, `run_record`, `protocol`, `version`, `repository`, `protocol_commit`, `checker`, and
`tests`, are reserved: an `executor.yaml` that supplies any of them is rejected rather than
silently overridden. `run_record` is incremented when a defined key changes meaning.

Where run records are kept is not yet defined (issue #44). Attach the record to the pull request or
issue it is relevant to.

A reviewer who has run the tests may record a `verified-with-benchmark` review (see Review Statuses
above), citing the run record in Notes. That is a judgement by a named person, made once; it is not
made automatically and not made per run. A run with failures is reported where the record is
attached, with the failing comparisons. Which of the executor, its environment, the protocol, or
the test is at fault is found out, not assumed: an agent can execute a correct protocol wrongly,
and measuring how often is what the tests are for.

CI validates each `test.yaml` against this schema and checks that local files exist. It does not
fetch remote files or execute tests. The `test-protocol` skill in this repository implements the
result contract for an agent.

## Example Protocol

```yaml
---
name: humann4-sgb-aggregation
description: Download representative isolate genomes and MAGs for MetaPhlAn 4.2 SGBs and subsample overrepresented SGBs.
version: 1.0.0
authors:
  - name: Levi Waldron
    orcid: 0000-0003-2725-0694
reviews:
  - name: Jane Doe
    orcid: 0000-0002-1825-0097
    date: 2026-08-10
    protocol_version: 1.0.0
    status: verified-with-benchmark
date: 2026-08-08
status: draft
license: CC-BY-4.0
type: atomic

artifact_doi: ~
collection_doi: "10.5281/zenodo.0000000"
protocol_citation: "10.7554/eLife.65088"

method_origin_citation: "10.1016/j.cell.2019.01.001"

upstream_repositories:
  - "https://github.com/biobakery/metaphlan"

database_urls:
  - "http://cmprod1.cibio.unitn.it/databases/Metaphlan/mpa_vJan21_CHOCOPhlAnSGB_202103.tar"

protocols_used: []
key_packages: []
category: metagenomics
tags: [humann, metaphlan, sgb, pangenome, mash]
---

# SGB Genome Aggregation & Subsampling

Download representative isolate genomes and MAGs for MetaPhlAn 4.2 SGBs...

## History & Reviews
<!-- Newest versions at the top -->

### Version 1.0.0 (2026-08-08)

#### Changes
- Initial protocol creation.

#### Reviews

**Review by Jane Doe ([0000-0002-1825-0097](https://orcid.org/0000-0002-1825-0097))**
- **Date:** 2026-08-10
- **Status:** `verified-with-benchmark`
- **Notes:** Executed against the MetaPhlAn 4.2 SGB release; outputs matched the expected genome counts.
```


