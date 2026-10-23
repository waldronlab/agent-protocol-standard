# agent-protocol-standard 0.4.0 (2026-10-23)

Tooling release. The format changed as well (ADRs 0012, 0014, 0016, 0017);
`spec_version` in the generated index remains `0.1.0`.

## SIGNIFICANT USER-VISIBLE CHANGES

* Two citation questions, asked separately (ADR 0014). `protocol_citation`,
  who published these instructions, is required. `method_citation` is renamed
  `method_origin_citation`, who invented the method, and is optional: a protocol
  that originates no method omits it rather than guessing. The validator rejects
  the old name and names the replacement.

* A protocol must carry `## Materials`, `## Steps` with at least one `### Step`
  heading, and a `protocol_citation` that is a DOI or PubMed ID rather than the
  template placeholder (ADR 0012).

* `stable` is an assertion by the authors, not something the validator infers
  from reviews (ADR 0013). `status` must be one of `draft`, `stable`,
  `deprecated`, `superseded`.

* Conditions on inputs live in `## Materials` and nowhere else (ADR 0017).
  A *must* condition that fails stops the executor before Step 1; a *should*
  condition that fails warns and proceeds, and the warning is recorded with the
  run. The `protocol-runner` skill (2.1.0) and `test-protocol` skill (0.2.0)
  apply this.

* The validator is Python and Pydantic (ADR 0015), replacing the R script.
  Run it as `python3 scripts/validate_protocol.py <protocols dir>`; the actions
  are unchanged for consumers. `DEVELOPMENT.md` describes how to change the
  schema.

* The template's workflows reference the actions at `@main` rather than `@v0`
  (#42), so a content repository always validates against the current standard.
  The moving tag `@v0` still exists and is retargeted on every qualifying
  release by `retarget-major-tag.yml` (#30), for anyone who has a reason to
  hold it.

* Index generation in a content repository authenticates as a GitHub App (#41),
  so it can push to a protected default branch.

* `protocols_used.version` on a dependency in the same repository must equal
  that dependency's current `version` (#48). A pin that drifted used to pass CI
  and fail in the runner at resolution time.

* `protocol-runner` 2.1.0 reads `protocol_citation` and `method_origin_citation`
  under their ADR 0014 meanings, emits a composite's own method citation when it
  carries one, and checks `## Materials` conditions before Step 1.

* The validator checks that `name` is kebab-case and matches its directory,
  that every ORCID has the right form, and that an atomic protocol declares no
  `protocols_used` while a composite declares at least one (#31).

* ADR 0018 is accepted: a composite resolves same-repository dependencies from
  the snapshot it came from and cross-repository dependencies from a `source`
  it carries, and the index is used for discovery only. The implementation is
  not in this release; it is tracked in #53, #54, #55, and #56.

## NEW FEATURES

* Protocol tests (ADR 0016). A protocol may carry `tests/<name>/test.yaml`
  with inputs and expected outputs, in `exact` or `diagnostic` mode. The
  validator checks the schema; `scripts/check_test_result.py` prints the result
  shape with values withheld, compares an executor's results, and writes a run
  record; the `test-protocol` skill is the executor side.

* `validate-protocol` skill (#37). Runs the validator, fixes every error that
  has exactly one correct answer, and states the judgement calls without
  guessing at them. It never invents a citation, author, date, status, or
  review, and never edits Materials, Steps, or Changes text.

* `create-protocol` skill (#35). Copies the template, fills the frontmatter from
  the current schema, asks the two citation questions separately, walks every
  optional item, and validates before reporting.

* `update-protocol` skill (#36). Bumps `version` and `date`, inserts the History
  entry, and updates the pin in every same-repository composite, checking
  everything before editing anything.

* Every optional item in the template is marked `Optional, delete if
  unneeded.`, so deleting the unused ones is a search rather than a judgement.

## BUG FIXES

* Malformed frontmatter no longer aborts the whole validation run. A `name` or
  `type` that is null or a list is reported for that protocol and the run
  continues (#32).

* `@v0` had drifted 22 commits behind `main`, so content repositories were
  validating with the R tooling after the Python rewrite had merged, and CI was
  green throughout. Tracking `@main` removes that failure mode (#42).

# agent-protocol-standard 0.3.1 (2026-09-12)

* `README.md` and the shipped template reference `@v0`, so a new consuming
  repository starts on the pre-1.0 moving tag.

* The "pin a fixed version" example names the current release rather than the
  oldest.

* Corrects the `protocol-runner` version example, which a blanket rename had
  rewritten to a tooling release.

* Adds ADR 0011, recording why the tooling is versioned `v0.x`.

# agent-protocol-standard 0.3.0 (2026-09-12)

* A composite may carry a `method_citation` (ADR 0010, amending ADR 0009). A
  sequence of methods can itself be published as a method; the validator checks
  only that the field is a single string, as for an atomic protocol.

* The runner's provenance block emits a composite's own `method_citation` when
  present.

* Removes the unused `protocol_type` inference from the validator.

# agent-protocol-standard 0.2.0 (2026-09-12)

* Renames the four provenance fields so each name says what it identifies
  (ADR 0009): `citation` to `method_citation`, `publication_doi` to
  `protocol_citation`, `protocol_doi` to `artifact_doi`, `repository_doi` to
  `collection_doi`. The validator rejects the old names and names the
  replacement.

* `spec_version` becomes `0.1.0`; the previous `1.0.0` claimed a stability the
  standard had not made.

# agent-protocol-standard 0.1.0 (2026-09-12)

* First tagged release of the standard, its validator, index generator, and
  the `protocol-runner` skill.
