# agent-protocol-standard

This repository defines the standard for AI agent-compatible scientific protocols, publishes the tooling that enforces it, and hosts the central federation registry. Protocols themselves live in federated content repositories, registered in [`registry.yaml`](registry.yaml).

*   [`PROTOCOL_STANDARD.md`](PROTOCOL_STANDARD.md) — the specification a `protocol.md` must conform to.
*   [`actions/`](actions/) — composite GitHub Actions that validate protocols and generate a repository's `PROTOCOLS.yaml` index.
*   [`registry.yaml`](registry.yaml) — the federated repositories agents discover protocols from.
*   [`skills/`](skills/) — the `protocol-runner` agent skill, whose behaviour the standard defines.
*   [`docs/adr/`](docs/adr/) — the decisions behind the standard.

This repository hosts no protocols of its own. The Waldron Lab's protocols are in [`waldronlab/agent-protocols`](https://github.com/waldronlab/agent-protocols), an ordinary federation node with no special standing — see [ADR 0006](docs/adr/0006-separate-standard-from-protocol-content.md).

*This repository was named `waldronlab/ai-agent-protocols` until September 2026. GitHub redirects the old name, but please update pinned references.*

## What is an AI Agent Protocol?

An "AI Agent Protocol" is related to but different than an [AI Skill](https://github.com/bioconductor/ai-agent-skills).

*   **AI Skill**: A specific capability given to an AI agent (e.g., how to query a specific biological database, or how to use a particular R package). Skills teach the AI *how* to perform specific actions.
*   **AI Agent Protocol**: A scientific workflow, experimental plan, or analytical pipeline designed to be executed by or in collaboration with an AI agent. Protocols in this registry are **designed around provenance to published methods**. Protocols:
    - are formal records providing citation both to primary scientific literature and to publication of protocols (#4). Atomic protocols have a single purpose with a single citation to primary literature; composite protocols may be composed of multiple atomic protocols.
    - will record **human reviews** (#2)
    - will support **formal unit tests/benchmarks** (#3) to verify correct execution by different AI agents and models. 

## Utility and Core Use Cases

Some likely use cases include:

1. **Constraining Coding Agents to Established Methods**: Forces AI agents to adhere strictly to vetted, peer-reviewed analytical protocols rather than drifting, inventing parameters, or inventing plausible but untested methodology during automated script generation. Protocols are expected to create more uniform behavior by different AI agents and models.
2. **Cross-Language and Pipeline Translation**: Serves as an unambiguous English-language specification for translating computational workflows across programming languages and pipeline frameworks (e.g., Nextflow ↔ Snakemake, R ↔ Python) without losing domain-specific logic or parameter integrity.
3. **Discrepancy Auditing (Paper vs. Code vs. Protocol)**: Acts as an explicit benchmark to systematically detect inconsistencies between high-level descriptions in published manuscript Methods sections, formal protocol documentation, and actual codebase implementations. Protocols should be easier for people with domain expertise to review than codebase or even Methods sections which are less structured, can be split across main manuscript and supplementary materials, and may lack necessary details for full implementation.
4. **Filling the Methodological Reproducibility Gap**: Provides the granular operational, environment, and parameter-level details that traditional journal Methods sections often omit, facilitating computational reproducibility with less susceptbility to bitrot or dependency issues.
5. **A federated registry of AI agent-compatible protocols**: This repository serves as a central registry for AI agent-compatible protocols, designed to allow researchers to independently create their own protocol repositories and federate them into this central registry. 

## Using this standard in your own protocol repository

Protocol repositories federate into the registry here, and need no copy of the tooling: validation
and index generation are published from this repository as GitHub composite actions, so both stay in
lockstep with [`PROTOCOL_STANDARD.md`](PROTOCOL_STANDARD.md). The template references them at
`@main`; see [below](#the-template-references-main-not-a-release-tag).

**Copy the contents of [`template/`](template/) into a new empty repository.** It is a complete
content node: the two workflows, a README and CONTRIBUTING that name this standard as the authority
on format, and a starter protocol at `protocols/example-protocol/protocol.md` to rename and edit.

The starter conforms in every respect but one: its required `protocol_citation` is the placeholder
`10.0000/replace-with-a-real-doi`, which the validator rejects by name. **Your first CI run is red
until you replace it**, deliberately — a real citation is the one thing the template cannot supply,
and it is DOI-shaped, so nothing but naming it would catch a template copied as-is. This
repository's own test suite asserts the starter fails on exactly that and nothing else, so it still
cannot quietly fall behind the standard it demonstrates.

Then:

1. Replace the placeholders in `README.md` and edit `protocols/example-protocol/` into your first
   real protocol — the directory name must match the frontmatter `name`.
2. Add a `LICENSE`. The template deliberately ships none, because the choice is yours; its README
   suggests the arrangement this project uses (CC-BY-4.0 for protocols, MIT for everything else)
   without assuming it.
3. **If `main` is protected, create a GitHub App so the index can be written.** A ruleset requiring
   pull requests blocks `github-actions[bot]`, and GitHub Actions itself cannot be granted a bypass —
   bypass actors of type `Integration` must be GitHub Apps installed on the organisation, and Actions
   is not one. A purpose-built App is. Create one owned by your organisation with **Contents: Read and
   write** and no other permission, install it on this repository only, and add it as a bypass actor
   on the ruleset. Its tokens expire after an hour, which a deploy key's would not.

   Hold its App ID and private key as **environment** secrets named `INDEX_APP_ID` and
   `INDEX_APP_PRIVATE_KEY`, in an environment called `index-generation` whose deployment branch policy
   allows only `main`. Repository secrets would be readable from a pull request branch — same-repo
   pull requests do receive secrets — and these mint a token that bypasses the protection you just
   configured. The template's workflow already declares the environment and passes both to
   `actions/create-github-app-token`.
4. Push to `main` and let the index generate.
5. **Open a pull request adding your repository to [`registry.yaml`](registry.yaml).** Until that
   entry exists nothing points at your index, so no agent will ever fetch it — a repository with a
   perfectly valid `PROTOCOLS.yaml` is still invisible.

Both actions take a `protocols-path` input if your protocols live somewhere other than `protocols/`.
Neither hardcodes a repository name: `protocol_url` values are built from the repository the workflow
runs in, so nothing in the template needs editing to point at you.
Both also take `python-version` (default `3.11`).

### The template references `@main`, not a release tag

A node validating
against a snapshot conforms to a version of the standard nobody publishes any more, and the failure
is silent: a green check produced by a validator older than the rule it claims to enforce. Tracking
`main` means a change that breaks you breaks you loudly, at a time when the spec is `0.y.z` and says
so.

This is a live question rather than a settled one. Pinning is the ordinary answer for a *library*,
where a consumer reasonably freezes a dependency; it is a stranger answer for a *standard*, where
conforming to last year's version is not obviously conformance at all. If you have a reason to pin —
a node you cannot update promptly, say — pin a commit SHA rather than a tag, since a tag can itself
be retargeted, and tell us, because the answer should be driven by what federated nodes actually
need.

Note that `generate-index` runs with `contents: write` where no App is configured, since GITHUB_TOKEN
does the push in that case.

## Development

*   `pytest tests/` runs the whole suite. With no protocols in this repository, it is
    the tooling's only coverage:
    *   the validator against the conforming and deliberately malformed fixtures in
        `tests/fixtures/`, and against the starter protocol in `template/`. Each invalid fixture
        asserts the specific error it is supposed to provoke, so adding a rule to the standard means
        adding a fixture.
    *   `tests/test_repo_utils.py` — the repository and ref detection helpers, across the remote URL
        forms git actually produces. A local path must yield `None` rather than a plausible but
        invented slug, since every `protocol_url` in a generated index is built from that answer.
    *   `tests/test_generate_protocols_yaml.py` — that the index names the detected repository and ref, copies
        frontmatter through whole, and **refuses to write at all** when it finds no protocols or
        cannot determine the repository. The index-generation action commits its output, so a wrong
        or empty index would be published without anyone looking at it.
*   `python3 scripts/validate_protocol.py <dir>` runs the validator against a protocols directory
    directly — point it at a checkout of a content repository to reproduce a CI failure locally.

### Releasing

Tag `vX.Y.Z`, then publish a GitHub Release for that tag. `retarget-major-tag.yml` moves `v0` onto
it, so nothing needs moving by hand — which is what the first four releases required, and one of them
drifted a merge behind `main` before anyone noticed.

Releases are now a record rather than a distribution channel: the template consumes the actions at
`@main`, so nothing is waiting on a tag to move. The versioned `v0.x.y` release tags remain the thing
to reference if you have a reason to hold a fixed version — `v0` itself is not one, since it is
retargeted onto every qualifying release (see Releasing below for which ones qualify) and is
therefore no more fixed than `main`. Note that a release tag is only fixed by
convention: a git tag can be retargeted, so a commit SHA is still the only genuinely immutable
reference.

The workflow declines to move the tag, with a notice rather than a failure, for a pre-release, for a
tag that is not `vX.Y.Z`, and for a release that is not the highest on its line — so republishing an
old patch release does not walk `v0` backwards. If a release is published while the workflow is
broken, dispatch it manually against the release tag to reconcile.

## License

This repository is dual-licensed:

*   **Software & Scripts** (e.g., contents of the `scripts/` directory): [MIT License](LICENSE)
*   **Scientific Protocols & Documentation** (e.g., `PROTOCOL_STANDARD.md`, unless otherwise specified): [Creative Commons Attribution 4.0 International (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0/)
