# 0012. Require Materials, Steps, and a Resolvable Citation

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Levi Waldron (User), AI Agent

> **Amended by [ADR-0014](0014-two-citation-questions.md) (2026-09-13).** `method_citation` below is renamed `method_origin_citation` and is no longer required; `protocol_citation` is now the required field. The decisions recorded here otherwise stand; the names are preserved as written for the historical record.

## Context and Problem Statement

A `protocol.md` with no `## Materials`, no `## Steps`, and no `method_citation` — nothing but frontmatter
and a `## History & Reviews` stub — validated clean and exited 0. So did a protocol with a malformed author
ORCID, a non-kebab-case `name`, `type: atomic` declaring dependencies, and `type: composite` declaring
none. One probe file exercised six of these at once and passed.

The repository's stated purpose is citable scientific protocols. Citability and content were the two things
CI did not check, while the newest feature — review bookkeeping — was enforced to the character.

Some of this was unenforced specification, but part of it was absent specification.
`PROTOCOL_STANDARD.md` said the markdown body *should* follow a structure, so rejecting a protocol with no
steps was a new rule rather than an unenforced one, and had to be decided rather than merely implemented.

## Decision

**`## Materials` and `## Steps` with at least one `### Step` heading are required**, as is
`## History & Reviews` last. The rest of the documented body structure stays a recommendation. A document
with metadata but no materials and no steps is not a protocol, however complete its frontmatter is.

**`method_citation` must be a DOI or a PMID**, and is required on any protocol whose effective type is
atomic. Free text naming a paper is rejected: a citation a reader or an agent cannot resolve does not
discharge the obligation the field exists to create.

**The placeholder the starter protocol ships is rejected by name.**
`method_citation: "10.0000/replace-with-a-real-doi"` is DOI-shaped, so a pattern check passes it, and a
copied template is the likeliest wrong citation there is. A new content repository's validation is
therefore red until the adopter writes a real citation — the one thing the template cannot do for them.
`template/`'s own test inverts accordingly: it asserts the starter protocol fails on exactly this error
and no other, which still catches a template that has drifted from the standard.

**Both halves of the atomic/composite definition are enforced**: `type: atomic` may not declare
`protocols_used`, and `type: composite` must. Both were stated in ADR 0004 and neither was checked.

Dependency cycles and depth are deliberately **not** included. They are a graph traversal rather than a
single-condition check, the runner already catches them at execution time, and keeping this change to
single-condition checks is what makes one-fixture-per-rule reviewable.

## Alternatives Considered

- **Leave the new rules as warnings.** Rejected: advisory checks are ignored, and these are the rules that
  distinguish a protocol from a metadata stub.
- **Give the template a real DOI so it validates clean.** Rejected: it would ship a citation that is wrong
  for whatever the adopter actually writes, and wrong silently. A red first build naming the one missing
  thing is better onboarding than a green one that is quietly incorrect.
- **Require `## Materials` only of atomic protocols.** Rejected as arbitrary: the one real composite has
  one, and a composite still has to say what it runs on.
- **Reject free-text citations but accept the template placeholder**, on the grounds that special-casing a
  literal string is inelegant. Rejected: the inelegance buys the single most likely failure mode.

## Consequences

Rules that were stated and unenforced are now enforced, each with at least one fixture. All seven existing
protocols pass unchanged — unlike the field rename, this needs no content migration.

Six fixtures gained a `## Materials` section they had been written without; that is most of the diff.

A new content repository's first CI run fails until its starter citation is replaced. This is intended, and
`README.md` and `template/`'s documentation say so, but it is a real change to the adoption path and the
likeliest thing an adopter will report as a bug.

Two decisions that travelled with these in draft were removed from this record and are documented where
they belong instead: an author `orcid` being recommended rather than required is a field description in
`PROTOCOL_STANDARD.md`, and the validator collecting all errors before failing is an implementation choice
visible only inside the validator. Neither changes what a conforming protocol is. What `stable` means was
also split out, into [ADR-0013](0013-stable-is-an-assertion-by-the-authors.md).
