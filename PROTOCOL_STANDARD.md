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
   * **Strictly 1 `method_origin_citation`:** A single DOI/PMID naming the primary literature where the method was originally published — the paper that *proposed* it, not one that applied it.
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
That is the normal case for a protocol written here rather than transcribed from a paper, and it is a
claim rather than a gap:

*   `protocol_citation` ≠ `collection_doi` — an external publication describes this procedure.
*   `protocol_citation` = `collection_doi` — **a first definition, published here.**

An absent field could mean either of those, or that nobody filled it in. Requiring the field forces the
distinction to be stated, and CI can check the answer is one of the two legal shapes.

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

These rules are enforced by `scripts/validate-protocol.R`, which runs on every pull request.

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
collection_doi: ~
protocol_citation: ~

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


