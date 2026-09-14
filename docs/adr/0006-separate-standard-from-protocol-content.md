# 0006. Separate the Standard from Protocol Content

- **Status:** Accepted
- **Date:** 2026-09-11
- **Deciders:** Levi Waldron (User), AI Agent
- **Supersedes:** [0002. Combined Registry and Protocols Repository](0002-combined-registry-and-protocols.md), in part

> **Amended by the template's move to `@main` (2026-09-14).** §3 below describes content repositories consuming the actions pinned to a release tag. The shipped template references `@main` instead, so that a node cannot validate against a standard older than the one it claims to follow. The argument for distributing the tooling rather than vendoring it is unaffected. Whether a federated node should ever pin is deliberately left open; see the matching note on ADR 0011.

## Context and Problem Statement

ADR 0002 deliberately combined the federation registry with the Waldron Lab's own protocols in a
single repository, on the grounds that separation was easy to do later and premature at the time. It
explicitly anticipated revisiting the arrangement as the federation grew.

That repository has since accumulated four distinct roles: it defines the protocol standard
(`PROTOCOL_STANDARD.md`, these ADRs), implements the tooling (`scripts/`), hosts the federation
registry (`registry.yaml`), and hosts seven Waldron Lab protocols. With the `## History & Reviews`
work merged, the standard is specified and CI-enforced, and the cost of the combination has become
concrete:

1. **The tooling could not run anywhere else.** Both scripts hardcoded the repository name — the
   generator for every `protocol_url` it emitted, the validator to recognise a local dependency —
   and there was no distribution mechanism, so a second lab's only option was to copy the scripts
   and workflows outright.
2. **The name describes the wrong thing.** `ai-agent-protocols` names the content, but the content
   is the least of what the repository holds and the only part another lab would not use.
3. **Unrelated changes share a history.** A protocol revision and a change to the standard are
   reviewed, versioned, and released through the same repository, and the registry is coupled to
   both.

## Decision

We separate the standard from the content, and name each repository after what it holds.

### 1. This repository becomes `waldronlab/agent-protocol-standard`

It owns `PROTOCOL_STANDARD.md`, the ADRs, the tooling under `scripts/` and `actions/`, the test
suite under `tests/`, and `registry.yaml`. Once §2 completes it will host no protocols; the rename
lands first, so the seven existing protocols remain under `protocols/` until then.

### 2. Protocol content will move to `waldronlab/agent-protocols`

An ordinary federation node registered in `registry.yaml` like any other, with no special standing.
The unit of trust in the registry is the repository — `trust_tier` and `approved_by` are properties
of a repository, not of a domain — so one content repository per lab or community is the right
grain, rather than one per scientific domain.

### 3. The tooling is distributed, not copied

`actions/validate-protocols` and `actions/generate-index` publish the validator and the index
generator as versioned composite actions. A content repository consumes both in about ten lines of
YAML pinned to a release tag, and never holds a copy that can drift from the standard it enforces.

### 4. The registry stays here, for now

ADR 0002's decision about where `registry.yaml` lives carries forward unchanged, including its
expectation that it may later move to a neutral repository once governance requires it. Naming this
repository after the standard rather than the registry is what makes that later move cheap: the
repository's identity does not depend on holding the registry.

### 5. The rename happens first

Before the content repository exists, so that everything created afterwards — its workflows, its
`uses:` references, `registry.yaml`, the runner's registry URL — is born with the final name rather
than being written twice.

## Alternatives Considered

- **Keep everything in one repository.** Rejected: it is what ADR 0002 chose, and the reason it gave
  for choosing it (separation is easy later, and there is only one content repository) has expired.
- **Make the new repository the standard and keep this one as the content node.** Rejected: the
  substance of this repository — the ADRs, the specification, the tooling, the open issues — is the
  standard. The content is seven files. Keeping the identity with the standard preserves the history
  that matters.
- **One content repository per scientific domain.** Rejected: trust in the registry is expressed per
  repository, so splitting by domain would fragment a single lab's trust profile across several
  entries that all mean the same thing.
- **Vendor the scripts into each content repository.** Rejected: the validator enforces
  `PROTOCOL_STANDARD.md`, so a copy that drifts is a repository silently enforcing an older
  standard while claiming to conform to the current one.
- **Rename last, after the content split.** Rejected: the content repository, its workflows, and the
  runner's registry URL would all be created against a name we already knew was changing, and every
  one of them would need a second pass.

## Consequences

- **Old references keep working, but only by redirect.** GitHub 301-redirects the old repository
  name for git, web, and raw content. The one functional coupling was the registry URL hardcoded in
  the `bioc-protocol-runner` skill; that skill has since moved into this repository as
  `protocol-runner` and been rewritten against the final URLs, so nothing now depends on the
  redirect. See [ADR 0007](0007-host-the-runner-with-the-standard.md).
- **The validator loses its in-repository corpus.** With `protocols/` gone, the only thing exercising
  `scripts/validate-protocol.R` is the fixture suite under `tests/`, which is why that suite was
  built before the content moved rather than after.
- **Two repositories, two CI configurations.** The content repository's workflows are thin — they
  call the published actions — but they are a second place where a version can be pinned, and
  therefore a second place that can fall behind.
- **A federated repository can now adopt the standard without forking anything.** This is the point
  of the exercise: the Waldron Lab's content repository is the first consumer of the same mechanism
  any other lab will use, so the mechanism is exercised by its own authors.
- **ADR 0002 is superseded in part.** Its decision to combine registry and protocols no longer
  holds; its decision about where the registry lives does.
