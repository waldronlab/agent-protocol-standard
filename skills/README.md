# Agent Skills

Agent skills that are defined by the protocol standard rather than by any one community, and so
version with it.

*   [`protocol-runner`](protocol-runner/SKILL.md) — discovers protocols across the federation,
    ranks them by trust and status, resolves dependencies, emits a two-level provenance block before
    executing anything, and drafts a Methods section afterwards.
*   [`test-protocol`](test-protocol/SKILL.md) — runs the tests a protocol carries under `tests/`,
    writes results in the standard's result contract, and hands them to
    `scripts/check_test_result.py`, which decides pass or fail and writes the run record.
*   [`update-protocol`](update-protocol/SKILL.md): bumps a protocol's version and date, inserts
    the matching `## History & Reviews` entry from the author's change description, and updates
    the pin in every same-repository composite that depends on it, each with its own patch bump.

## Why these live here

Everything the runner does — how it ranks by `trust_tier`, what it does with a `draft`,
`superseded`, or `deprecated` protocol, which fields it reads from `PROTOCOLS.yaml`, the shape of
the provenance block — is meaningful only in terms of the vocabulary
[`PROTOCOL_STANDARD.md`](../PROTOCOL_STANDARD.md) defines, and none of it is any one community's to
decide. A runner that lags the standard silently changes what "executed this protocol" means, so
keeping them in one repository means one pull request changes both.

Note that the standard currently defines that *vocabulary* — statuses, schema, index fields — but
not the execution rules built on it, which live here in the `SKILL.md`. Promoting them into the
standard is follow-up work that this move makes possible. See
[ADR 0007](../docs/adr/0007-host-the-runner-with-the-standard.md).

## Installing

Skills are plain markdown; there is no package to install. Clone this repository and make the skill
directory visible to your agent. For Claude Code, symlink it:

```sh
git clone https://github.com/waldronlab/agent-protocol-standard.git
ln -s "$PWD/agent-protocol-standard/skills/protocol-runner" ~/.claude/skills/protocol-runner
```

A symlink rather than a copy, so `git pull` is the whole update process.

## Format

The frontmatter follows [Bioconductor's `SKILL_STANDARD.md`](https://github.com/Bioconductor/ai-agent-skills/blob/devel/SKILL_STANDARD.md)
— `name`, `description`, `version`, `category`, `author`, plus optional `tags` — so a skill from here
drops into a collection that follows that convention without modification. The directory name must
match the frontmatter `name`.
