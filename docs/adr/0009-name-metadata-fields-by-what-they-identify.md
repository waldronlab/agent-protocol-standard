# 0009. Name Metadata Fields by What They Identify

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Levi Waldron (User), AI Agent
- **Amends:** [ADR-0001](0001-protocol-standard.md), [ADR-0003](0003-protocol-provenance-and-resource-metadata-refinements.md), [ADR-0004](0004-atomic-and-composite-protocols.md) — field names only; the decisions those records make are unchanged


> **Corrected by [ADR-0010](0010-composites-may-carry-a-method-citation.md) (2026-09-12).** The claim below that a composite has no `method_citation` is wrong — a sequence of methods can itself be published as a method. The rename this ADR records is unaffected.

> **Amended by [ADR-0014](0014-two-citation-questions.md) (2026-09-13).** `method_citation` below is renamed `method_origin_citation` and is no longer required; `protocol_citation` is now the required field. The decisions recorded here otherwise stand; the names are preserved as written for the historical record.

## Context and Problem Statement

ADR 0001 established a four-field DOI taxonomy: `protocol_doi` for the artifact, `repository_doi` for the
parent collection, `publication_doi` for a paper describing the protocol, and `citation` for the paper the
protocol is based on. The distinctions are sound. The names do not express them.

Three of the four end in `_doi`, which separates nothing — all four hold a DOI. What differs is the
*relationship* each encodes, and no name states it. Meanwhile `citation`, the most specific concept of the
four, carries the most generic available name: every one of these fields is a citation of something, so
`citation` alone cannot say which.

The names also mix two categories with no signal of which is which. Two fields point outward at other
works; two name this thing. A reader meeting the schema for the first time has no way to see that split.

The consequence showed up in practice. Contributors drafting protocols could not tell whether a paper
belonged in `citation` or `publication_doi`, and the standard's own text made the ambiguity explicit for
composites: an overarching pipeline publication "may be listed in `citation` or `publication_doi`" — two
legal encodings of one fact, which defeats the purpose of machine-readable frontmatter.

## Decision

Rename all four fields so that each says what it identifies.

| Was | Now | Identifies |
|---|---|---|
| `citation` | `method_citation` | The **method** this protocol performs — the primary literature that proposed it |
| `publication_doi` | `protocol_citation` | A publication that **describes or validates this protocol**, including its parameterization |
| `protocol_doi` | `artifact_doi` | **This document**, as a citable artifact |
| `repository_doi` | `collection_doi` | The **repository or collection** housing it |

The two categories are now visible in the names: `*_citation` fields reference other works, `*_doi` fields
identify things.

We further settle two semantic points the old names left open.

**`method_citation` describes the method in general; `protocol_citation` describes precise usage.** A method
is a general idea; a protocol fixes parameters, thresholds and choices. **One method can therefore be the
basis of several protocols** — different published parameterizations of random forest classification are
genuinely different procedures that yield different results from the same inputs, and each is its own
protocol. Sibling protocols share a `method_citation` and are distinguished by their `protocol_citation`.
This is what keeps the one-method-one-citation rule from forcing unlike procedures into one document.

**A composite has no `method_citation`.** It proposes no method; it composes protocols that do, and inherits
their citations. A paper describing the pipeline as a whole is a `protocol_citation`. This removes the
"`citation` or `publication_doi`" ambiguity by leaving only one legal field.

### Versioning: the specification is pre-1.0

`spec_version` was `1.0.0`, which claimed a stability commitment the standard has not made and cannot yet
honour. Nothing outside these two repositories consumes the format; the field names, as this ADR
demonstrates, are still being worked out.

`spec_version` therefore becomes `0.1.0`. SemVer reserves `0.y.z` for initial development, where anything may
change at any time and the format is explicitly not stable. That is an accurate description of where the
standard is, and it removes the need to treat every correction as a migration event with deprecation windows
and compatibility shims.

`1.0.0` becomes a deliberate act rather than a starting point: the moment the standard takes on an obligation
to outside consumers. It should be reached when there are consumers to owe it to.

The field is kept rather than dropped. A federation index is parsed by tools that need some way to know what
they are reading, and `0.1.0` communicates instability far more usefully than an absent field, which reads as
unknown rather than unstable.

Old names are **rejected** by the validator with a message naming the replacement, rather than accepted with a
deprecation warning: no protocol predates the rename, so there is nothing to migrate and no reason to carry
two spellings.

## Alternatives Considered

- **Rename only `publication_doi`.** Cheapest, and fixes the pair that actually gets confused. Rejected
  because it leaves `citation` unable to say what it cites, which is half the original problem.
- **`proposed_in` / `described_in`.** Reads as a sentence and is arguably clearer still. Rejected narrowly:
  verbal names sit oddly beside `name`, `version`, `authors`, and the `*_citation` / `*_doi` split makes the
  reference-versus-identifier categories legible in a way prepositional names do not.
- **Keep the names, fix the documentation.** Rejected because field names are read far more often than
  specifications are, and because documentation cannot resolve the composite ambiguity — only removing one
  of the two legal fields can.
- **A pre-release version such as `2.0.0-alpha`.** Rejected: valid SemVer, but it asserts a target major
  version and keeps the breaking-change framing, when the point is that no compatibility promise exists yet.
- **Drop `spec_version` entirely.** Rejected: a consumer needs a way to detect what it is parsing, and an
  absent field reads as unknown rather than as unstable.
- **Defer until after Phase 2.** Rejected on cost. The rename currently touches 14 files and 7 protocols,
  all in-house, with no external consumers. Thirty-one protocol issues are now open; every protocol written
  against the old names becomes migration work. The cost will never be lower than it is today.

## Consequences

Contributors can tell which field a DOI belongs in by reading the field name. The reference/identifier
distinction is visible without consulting the specification. The composite provenance ambiguity is gone.
Sibling protocols sharing a method now have a principled way to express the relationship.

Dropping to `0.1.0` costs nothing today and buys room to keep correcting the format while it is still being
designed. The risk it introduces is the obvious one: `0.y.z` is a licence that can be over-used. Reaching
`1.0.0` should be a decision taken on purpose, not something that happens when someone gets tired of the zero.

Any agent or tool carrying the old field names will produce protocols that fail validation. The validator
names the replacement field in its error, so the correction is mechanical.

Note that the repository's release tags (`v1`, `v1.0.0`) version the *tooling* that consumers reference from
workflows, which is a separate axis from `spec_version`. Those tags make the same overclaim and should be
reconsidered alongside the outstanding work to retarget `v1`, not here.

> That reconsideration happened later the same day. See [ADR-0011](0011-pre-release-tags-for-the-tooling.md):
> the tooling is versioned `v0.x` with a moving `@v0` tag.
