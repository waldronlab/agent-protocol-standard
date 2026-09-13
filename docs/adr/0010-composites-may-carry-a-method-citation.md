# 0010. Composites May Carry a `method_citation`

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Levi Waldron (User), AI Agent
- **Amends:** [ADR-0009](0009-name-metadata-fields-by-what-they-identify.md) — corrects one claim; the rename it records stands

> **Amended by [ADR-0014](0014-two-citation-questions.md) (2026-09-13).** `method_citation` below is renamed `method_origin_citation` and is no longer required; `protocol_citation` is now the required field. The decisions recorded here otherwise stand; the names are preserved as written for the historical record.

## Context and Problem Statement

ADR 0009 asserted that a composite protocol has no `method_citation`, on the reasoning that a composite
proposes no method — it composes protocols that do, and inherits their citations. The validator was changed
to reject the field on any `type: composite` document, and the claim was written into the specification, the
runner skill, and the authoring template.

The reasoning was wrong. A sequence of methods can itself be published as a method. Pipelines are proposed,
named, and cited as contributions in their own right: a two-stage hierarchical meta-analysis design is a
method, and so is a published end-to-end database construction pipeline, even though each is a composition
of steps that have their own prior sources.

Rejecting the field forced a real protocol to misfile a citation. `humann4-database-build` carried the
bioBakery paper as `method_citation`; the new rule failed validation, and the citation was moved to
`protocol_citation` to get CI green. That paper arguably does propose the pipeline as a method, so the rule
produced a worse record rather than a better one — the failure mode a validator should never have.

## Decision

A composite protocol **may** carry a `method_citation`. The validator no longer rejects it, and checks only
that the value is a single string, exactly as for an atomic protocol.

The guidance, which is where this belongs, is that most composites omit it. A composite that sequences
existing protocols proposes nothing new; a paper describing such a pipeline is a `protocol_citation`, and the
method citations come from the constituents. Where the composition is *itself* a published method,
`method_citation` names the paper that proposed it.

The distinguishing question is about the literature, not the file: **does the paper propose this combination
as a method others would cite as an approach, or does it merely describe running these steps?** That is a
judgement for an author and a reviewer. It is not mechanically checkable, and the validator should not
pretend otherwise.

## Alternatives Considered

- **Keep the rejection.** Rejected: it is false, and it demonstrably corrupted a citation to satisfy a rule.
- **Warn instead of reject.** Rejected: a warning on legitimate usage trains authors to ignore warnings, and
  the legitimate case is not rare enough to flag.
- **Require `protocol_citation` whenever a composite omits `method_citation`.** Rejected: many composites
  have no publication of any kind, which is fine.

## Consequences

The specification now says less about composites and leaves more to review, which is the correct division:
this is a question about what a paper claims, and no schema check can read a paper.

More generally, the episode is worth recording as a caution. The rejected rule was derived from a plausible
definition rather than from looking at the protocols in the repository. The single composite that existed
already contradicted it. A rule about content is worth testing against the content before it is enforced.
