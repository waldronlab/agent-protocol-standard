# 0018. Resolve Dependencies from the Composite, Not the Index

- **Status:** Accepted
- **Date:** 2026-10-23
- **Deciders:** Levi Waldron

## Context and Problem Statement

A composite pins each constituent in `protocols_used` by `name`, `repository`, and exact
`version`. The runner resolves the pin by looking the triple up in the federation's merged index
(ADR 0004, ADR 0008). Each repository's `PROTOCOLS.yaml` lists one entry per protocol, describing
the file at the head of the default branch, with a `protocol_url` that points there, usually at a
branch name rather than a commit.

So the index can resolve a pin only while the pin equals the newest version. The day an atomic
protocol bumps from 1.0.0 to 1.1.0, every composite pinning 1.0.0 stops resolving, in its own
repository and in every other one. Nothing in the composite changed and nothing about 1.0.0 became
wrong; the index simply no longer has an entry for it. Issue #36 noticed this and proposed that
the `update-protocol` skill move every pin on every bump. Pull request #51 implemented that, and
reviewing it showed where the idea leads: the skill would have to find dependents in other
repositories through the registry, and then open issues against them, because a new release of an
atomic protocol in one repository would be a breaking event for composites in all the others.

That is backwards. A pin means "this composite was written against this version". A newer release
of the dependency is information, not breakage, and the composite's authors decide when to move.
The index is doing two jobs, discovery and resolution, and is only good at the first.

A second observation settles the shape of the fix. An agent executing a composite fetched it from
somewhere: a raw file at a git commit, a release archive, a Zenodo record. Each of those is a
snapshot of a whole repository at one moment, so a sibling protocol in the same snapshot is already
unambiguous. Only a dependency in another repository needs anything more.

## Decision

**The index is for discovery.** `PROTOCOLS.yaml` describes what a repository offers now: the newest
version of each protocol, with the metadata an agent or an MCP server needs to find relevant
protocols and rank them by `trust_tier` and `status`. It is not consulted to resolve a pin.

Two fields are added to the index so that it can name a snapshot and help a composite author pin:
the top level carries `commit`, the commit the index was generated from, and each entry carries
`sha256`, the digest of that protocol's file at that commit. `protocol_url` points at the commit,
not at a branch, so that what the index describes and what the URL returns cannot diverge.

**A same-repository dependency resolves from the snapshot the composite came from.** Its
`protocols_used` entry carries `name`, `repository`, and `version`, as today, and nothing else. The
runner fetches `protocols/<name>/protocol.md` from the same snapshot it fetched the composite from:
the same commit for a raw URL, the same archive for a release or a Zenodo record, the index's
`commit` when the composite came through the index. A branch name is never a snapshot; a runner
that is given one resolves it to a commit before fetching anything, and fetches the composite and
every sibling at that commit. The runner records the snapshot identity (a commit, a tag, a DOI) in
the provenance it emits.

For this to be correct, a repository's head must be self-consistent: at any commit, a composite's
pin on a sibling must equal the sibling's `version` at that commit. The validator already enforces
this (pull request #48). The consequence is that bumping an atomic protocol moves the pins of its
sibling composites in the same change, which is what `update-protocol` does. A composite released
earlier still resolves at its own commit, so no released composite goes stale.

**A cross-repository dependency names a `source`.** Its entry carries a fourth field, `source`,
which is either a file slot in the vocabulary ADR 0016 already defines for remote files, or a DOI:

```yaml
protocols_used:
  - name: humann4-sgb-aggregation
    repository: waldronlab/agent-protocols
    version: 1.0.0
  - name: some-method
    repository: otherlab/protocols
    version: 2.1.0
    source:
      url: https://raw.githubusercontent.com/otherlab/protocols/some-method-v2.1.0/protocols/some-method/protocol.md
      sha256: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
  - name: another-method
    repository: thirdlab/protocols
    version: 1.3.0
    source:
      doi: 10.5281/zenodo.1234567
```

A `url` source is the markdown file itself, and `sha256` is required: the runner fetches the file,
checks the digest, and then checks that the frontmatter's `name` and `version` match the entry.
Matching frontmatter alone is not integrity, since a re-pointed URL can carry forged frontmatter
with the right name and version and different steps; the digest is what makes a URL safe to
accept. A `doi` source is a Zenodo version DOI, which identifies one immutable deposit; `sha256`
may accompany it and is checked when present. The name and version check applies to both.

The digest is stored in the depending protocol, not looked up in the index. The index describes
only the newest version, and it is fetched from the same place as the file, so a digest there would
prove nothing. The composite's digest is a statement by its authors about what they validated
against, frozen with the composite. The index's per-entry `sha256` is where that value comes from:
`create-protocol` and `update-protocol` copy it from the dependency's index at the moment the pin
is written or moved, so nobody computes a digest by hand.

**Resolving a DOI.** For a Zenodo DOI the runner resolves the record through the Zenodo records
API, reads the file list, and takes `protocols/<name>/protocol.md` from the deposit: directly, if
the deposit holds the file, or from inside an archive of the repository, as the GitHub integration
produces. No other DOI host is supported until a repository needs one; a DOI that does not resolve
to Zenodo is an error, and the repository should give a `url` source instead.

`source` is not permitted on a same-repository dependency. Allowing it would let a composite pin an
older sibling, and then its `source` could not exist until that sibling was released, so the
composite could not be validated before merge. The simple rule covers every case that exists today.

**How a repository produces a `source` is its own business.** A git tag when a protocol's version
changes, a GitHub release, a Zenodo deposit through the GitHub integration, or any other stable
URL all satisfy the contract. The shared workflow in the template will create a tag named
`<name>-v<version>` when a protocol's `version` changes on the default branch, so a repository that
does nothing further still has a URL for every release. The standard recommends that convention and
does not require it.

**What "same repository" means.** A dependency is same-repository when its file exists in this
snapshot at `protocols/<name>/protocol.md`, which is the fact resolution relies on. The validator
uses the same test, not a comparison of `repository:` with the repository it happens to be running
in. That comparison fails in a fork, where a student validating locally would otherwise be told
that a sibling needs a `source`. `repository:` is still checked against the canonical name when the
validator can determine it, and a mismatch in a checkout whose remote is not the canonical one is a
warning, not an error.

**The validator** checks that `source` is present on every cross-repository entry and absent from
every same-repository one, and that it is a `{url, sha256}` mapping or a `{doi}` mapping by shape.
It does not fetch. Content integrity is the runner's check, made at execution time against the
digest the composite carries, and CI does not need the network to validate a protocol. The
same-repository check from #48 stays. The two checks are deliberately different: within a
repository the question is whether the pin equals the sibling's current version, because the
snapshot supplies the content; across repositories the question is whether the fetched content is
what the authors pinned, because nothing else does.

**The runner** gains the two resolution procedures above and stops resolving pins through the
index. **`update-protocol`** moves same-repository pins and nothing else. Both skills say which
repository a dependency came from and at which snapshot in the provenance block.

## Alternatives Considered

- **Index every released version.** Each `PROTOCOLS.yaml` would list every version of every
  protocol with a per-version URL and digest. Rejected. It makes the index carry release history
  it would have to reconstruct from git, grows without bound, and still leaves resolution dependent
  on the index being reachable and current. The composite can say where its dependency is without
  help.
- **`source` on every entry, same repository included.** One rule instead of two. Rejected for the
  release-ordering problem above: a pull request that adds or bumps an atomic and its sibling
  composite together would name a `source` that does not exist until after merge, so it could never
  be validated beforehand.
- **Move every pin on every bump, everywhere.** What #36 proposed and #51 implemented. Rejected.
  Across repositories it means a release in one repository obliges work in others, and the skill
  that bumps the atomic would have to find dependents through the registry and open issues against
  them. Within a repository the coupling is kept, because the authors are the same and the head must
  be self-consistent.
- **Store the digest in the index rather than the composite.** Rejected for the reasons given in
  the decision: the index knows only the newest version, and it is no more trustworthy than the
  file it describes.
- **A bare URL or DOI string for `source`, with the name and version match as the only check.**
  The first draft of this ADR. Rejected in review: it invents a weaker parallel to the file-slot
  vocabulary ADR 0016 already has, and the match check cannot detect substituted content.
- **Require a tag naming convention in the standard.** Rejected. A Zenodo deposit or a non-GitHub
  host is as good a `source` as a tag. The convention is recommended and automated, not required.
- **A commit SHA field instead of a URL or DOI.** Exact and immutable, but opaque to a reader, tied
  to git, and no help for a Zenodo record. The URL can carry a SHA where that is what the
  repository publishes, and the digest covers integrity either way.

## Consequences

- A released composite keeps resolving for as long as its sources exist. "Stale pin" stops being a
  failure mode across repositories.
- Cross-repository pins become checkable for the first time, by the runner against a digest the
  composite carries. Today they are checked by nobody until the runner fails.
- **Siblings on the default branch are coupled.** A composite cannot stay on an older version of a
  sibling in its own repository, because `source` is forbidden there and the validator requires the
  pin to equal the sibling's current version. A major bump of an atomic protocol obliges every
  sibling composite to follow in the same change, or to be revised to no longer depend on it. This
  is the price of resolving siblings from a snapshot with no further bookkeeping, and it is paid by
  the same authors who made the bump.
- Content repositories gain one obligation they did not have: a `source` for each cross-repository
  dependency, which means the dependency's repository must publish releases in some stable form.
  No content repository has a cross-repository dependency today, so there is nothing to migrate.
- The index generator publishes `commit` and per-entry `sha256`, and writes `protocol_url` at the
  commit. Indices generated before this change carry a branch URL and no commit; a runner reading
  one resolves the branch to a commit itself.
- The runner has to be updated across the federation. A copy of `protocol-runner` that predates
  this ADR ignores `source`, resolves through the index, and fails on the first cross-repository
  bump, which is the failure this ADR removes. The skill's version bumps, and the change is noted
  in its History.
- The template's workflow gains a tagging step, and the validator, models, runner, and
  `update-protocol` skill change as described. The runner's execution contract (#15) should state
  the two resolution procedures and the Zenodo procedure when it is promoted into the standard.
- The fully-qualified name question (#24) gets a natural form, `repository/name@version`, that is
  resolvable on its own once `source` is known.
- Issue #36's analysis of when a composite's own version should bump still applies within a
  repository, and is now the only place it applies. `update-protocol` bumps a sibling composite's
  patch version with a Changes line naming the new pin, so the History section records the change.
