# 0022. Show Every Test of a Protocol the Same Result Shape

- **Status:** Proposed
- **Date:** 2026-11-23
- **Deciders:** Levi Waldron, Otto Infield-Harm

Amends ADR 0016 and ADR 0019.

## Context and Problem Statement

Issue #63. In a diagnostic test, `shape.yaml` shows the executor the only accepted outcome before it opens the input:

```yaml
mode: diagnostic
accepted_outcomes:
- outcome: refused_for_missing_values
  expected_absent: [n_detected, prevalence, retained_features, removed_features, filtered_table]
```

That tells the executor the input is bad, what is wrong with it, that it should refuse, and which keys to leave out. Passing shows it copied a label. All 8 Claude models passed all 5 diagnostic tests of `prevalence-filtering`, and `shannon-diversity` has the same flaw.

Four parts of the shape give answers away:

| Part of the shape | What it reveals |
|---|---|
| `accepted_outcomes[].outcome` | the decision, and the condition that failed |
| `mode` | whether the input is valid |
| `expected_absent`, and which keys are present | whether to produce outputs |
| `name`, `description`, input file names | whatever the author wrote |

The shape has to say how to write a result. It does not have to say which result is right.

## Decision

Every test of a protocol shows the executor the same result shape. Only the inputs differ.

### 1. Two outcome kinds

Every `result.yaml` has `outcome: completed | refused` and `observation`. `warnings` is optional, as before.

In `test.yaml`, an accepted outcome's protocol-specific name moves to `label`, which only the checker reads, and `outcome` becomes its kind:

```yaml
evaluation:
  mode: diagnostic
  accepted_outcomes:
    - label: refused_for_missing_values
      outcome: refused
      expected_absent: [n_detected, prevalence, retained_features, removed_features, filtered_table]
      expected_reason: missing     # optional
```

- `expected_reason` is optional. It is a case-insensitive phrase that must appear in `observation`, checked like `expected_warning` (ADR 0017) and never shown in the shape. It checks that the executor refused for the right reason, without telling it the reason.
- An exact test keeps `expected_outputs` at the top level, and the executor writes `outcome: completed`.
- When several accepted outcomes share a kind, the test passes if any of them matches. `run.yaml` records the label of the one that matched.

Two kinds are enough. `orientation_corrected` and `computed_with_depth_warning` are `completed` outcomes, told apart by their evidence. A third kind waits for a test that needs one.

### 2. One output schema per protocol

`tests/outputs.yaml` declares every top-level output key the protocol produces, with its type:

```yaml
n_samples: [number, mapping]          # a list allows any of these types
n_detected: mapping
retained_features: [list, mapping]
cutoff: [number, "null"]
filtered_table: {file: csv, header: {input: data}}
result: {file: csv, header: [sample_id, shannon]}
```

- **Types** are `number`, `string`, `boolean`, `null`, `list` and `mapping`. A key may allow more than one, because types already vary within a protocol: under per-dataset scope `n_samples` is a mapping, and pooled it is a number. `cutoff` is null when nothing is removed.
- **A table's header** is one of three things:
  - a fixed list, as in `shannon-diversity`;
  - `{input: <key>}`, the header of that input table, as in the filtered tables of `prevalence-filtering` and `independent-filtering-variance`;
  - `withheld`, when the protocol prescribes it.

  This replaces taking the header from the expected file, which a refusal test does not have.
- **The validator checks that:**
  - every key in any `expected_outputs` or `expected_absent` is declared;
  - every expected value fits its declared type;
  - every expected table's header follows its rule.

The shape shows this schema, plus `outcome`, `observation` and `warnings`, once for the whole protocol. The executor writes the keys the protocol produces for its input. The checker compares only what each test expects and ignores extra top-level keys, as it does now. ADR 0016's guarantee holds: a correct execution cannot fail on a key name.

### 3. Left out of the shape

`mode`, `numeric_tolerance`, accepted outcomes, `expected_absent`, `name` and `description` are no longer shown. `numeric_tolerance` differs between tests now (0 in some, 1e-12 in others), so showing it would identify them. The executor writes numbers at full precision. `mode` and `numeric_tolerance` stay in `test.yaml` for the checker and the validator.

### 4. Opaque test IDs in the bundle

`--shape --bundle` gives each test an ID (`test_01`, `test_02`, ...), in random order:

- Inputs go in `inputs/<id>/<input key>.<extension>`, so the author's file names don't appear.
- The executor writes `results/<id>/`.
- The mapping from IDs to names goes in `source.yaml`, which the executor never sees. The checker maps the IDs back, and `run.yaml` keeps the real names.

Authors keep descriptive names and descriptions for reviewers.

### 5. Migrate in one step

`check_test_result.py` 0.5.0 reads only the new format. It refuses a `tests/` directory without `outputs.yaml` and says how to convert it. There is no format version field, because `outputs.yaml` marks the new format.

The only content repository with tests is `waldronlab/agent-protocols`: `independent-filtering-variance` and `shannon-diversity`, plus `prevalence-filtering` once it is submitted. Its conversion is mechanical, and it lands in a PR alongside the release:

- each `outcome:` becomes `label:`, and `outcome:` becomes the kind;
- `outputs.yaml` is collected from each protocol's tests.

### Versions

`check_test_result.py` 0.5.0 and the `test-protocol` skill 0.5.0. The executor brief describes `completed | refused` and the single shape. `run_record` stays at 1: test entries keep their names, and `outcome` still holds the protocol's label.

## Alternatives Considered

- **Revise ADR 0016 in place.** Rejected: an accepted ADR is amended, not rewritten, as 0019 and 0020 did.
- **Hide only the labels.** Rejected: `mode`, `expected_absent` and the key sets still give the answer away.
- **Show every test the union of the protocol's labels.** Rejected: the list still names the conditions the tests probe.
- **Withhold the shape.** Rejected for ADR 0016's reason: a correct execution would fail on a key name.
- **Grade `observation` with a model instead of `expected_reason`.** Rejected for ADR 0016's reason: the thing under test would be grading itself.
- **A third kind, `corrected`.** Not needed: corrections are `completed` outcomes told apart by evidence.
- **One type per key.** Rejected: existing protocols would have to change their output format to suit the test harness.
- **Accept both formats for one version.** Rejected: two code paths in the checker to spare one repository a mechanical change.

## Consequences

- A diagnostic pass shows that the executor found the problem.
- Diagnostic passes from checker 0.3.0 and 0.4.0 are not evidence for #5 or for a `verified-with-benchmark` review. The checker version in `run.yaml` tells them apart.
- Authors maintain `outputs.yaml`, and the validator catches drift.
- With a fixed outcome vocabulary, the output instruction in #64's benchmark runs is the same for every test, so diagnostic tests can be benchmarked too. If accepted, change #64's plan, which keeps diagnostic tests conformance-only. One caveat goes with the change: offering `refused` tells an agent without the protocol that refusing is allowed. That raises its baseline, so the protocol's measured benefit is a lower bound.
- **Limits:**
  - A blind shape does not stop an executor from reading the checkout. Isolation does that (ADR 0019).
  - A refusal test is still easier than an exact one, since its only evidence is what was not written. `expected_reason` raises the bar a little.

Drafted with Claude Code. Read and approved by Otto Infield-Harm.