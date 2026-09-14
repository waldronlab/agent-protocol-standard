# 0011. Pre-release Tags for the Tooling

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Levi Waldron (User), AI Agent
- **Amends:** [ADR-0009](0009-name-metadata-fields-by-what-they-identify.md) — settles the tag question it raised and deferred

> **Amended by the template's move to `@main` (2026-09-14).** Everything below about what a *consumer*
> should reference is historical — the Decision's "`@v0` keeps the moving-tag behaviour… a consumer that
> cannot accept this pins a release tag", and the Consequences' "Consumers must reference `@v0`… a new
> repository starts on `@v0`". The shipped template references `@main`, so that a node cannot validate
> against a standard older than the one it claims to follow.
>
> What still stands is this ADR's actual subject: the tooling is versioned `v0.x`, `@v0` exists and is
> retargeted onto qualifying releases, and the two version axes are separate. Whether a federated node
> should ever pin is deliberately left open; if it settles, it warrants an ADR superseding these
> consequences and ADR 0006 §3.

## Context and Problem Statement

ADR 0009 dropped `spec_version` to `0.1.0`, on the grounds that `1.0.0` claimed a stability commitment
the standard has not made. It noted in passing that the repository's release tags version the *tooling*
on a separate axis, make the same overclaim, and should be reconsidered — but deferred the question.

Deferring it produced exactly the contradiction the earlier decision was meant to remove. The format
announced itself as unstable while the actions consumers reference announced a stable `v1` line. Worse,
`v1` was then moved twice in one day onto changes that break anyone pinned to it: `v1.1.0` renamed four
frontmatter fields and made the validator reject the old spellings, and `v1.2.0` reverted a rule that
`v1.1.0` had added. A moving major tag exists to promise that this will not happen.

Nothing external consumes these actions. The promise was being broken in private, which is the cheapest
moment to stop making it.

## Decision

The tooling is versioned `v0.x`, and the moving tag is `@v0`.

| Was | Now | Commit |
|---|---|---|
| `v1.0.0` | `v0.1.0` | first tagged release |
| `v1.1.0` | `v0.2.0` | field rename |
| `v1.2.0` | `v0.3.0` | composite `method_citation` correction |
| `v1` | `v0` | moving, currently `v0.3.0` |

Release notes are carried across. The `v1.*` tags and their Releases are deleted once the one consumer is
on `@v0`, so that nothing is left resolving a tag mid-migration. Both axes now agree
that this is pre-1.0 software: `spec_version: 0.1.0` for the format, `v0.x` for the tooling. They remain
separate numbers, because they change for different reasons — a release that only fixes a validator bug
moves the tooling and not the format.

`@v0` keeps the moving-tag behaviour: a consuming repository tracks the standard without a pull request
per release. Under `0.y.z` that tracking may bring a breaking change, which is what `0.y.z` means. A
consumer that cannot accept this pins a release tag.

Reaching `v1.0.0` is a deliberate act, taken when there are outside consumers owed stability — the same
condition ADR 0009 set for `spec_version` reaching `1.0.0`. The two need not arrive together.

## Alternatives Considered

- **Keep `v1` and accept the overclaim.** Rejected: the tag had already been moved twice across breaking
  changes, so the promise was not merely inaccurate but actively false.
- **Open a `v2` line instead.** Rejected: semver-correct for the rename, but it asserts a stable major
  version, which is the thing being retracted.
- **Leave the `v1.*` tags in place as historical aliases.** Rejected: two schemes side by side invite the
  question of which is current. The commits are unchanged and the notes are carried over, so nothing is
  lost by deleting them.

## Consequences

Consumers must reference `@v0`. The one that exists, `waldronlab/agent-protocols`, is updated in a companion
pull request, and the `v1.*` tags survive until that lands. The template shipped to future consumers is
updated here, so a new repository starts on `@v0`.

Anything holding `@v1` breaks rather than silently receiving a stale validator. Given that the tag was
17 commits behind `main` until today, and that the staleness had been hiding a real validation failure in
`agent-protocols`, a loud break is the better failure.
