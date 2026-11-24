# 0021. Show Every Test of a Protocol the Same Result Shape

- **Status:** Accepted
- **Date:** 2026-11-23
- **Deciders:** Levi Waldron, Otto Infield-Harm

Amends ADR 0016 and ADR 0019.

## Context

Issue #63. A diagnostic test's `shape.yaml` gives the executor the only accepted outcome, such as `refused_for_missing_values`, and the keys to leave out, all before the executor opens the input. Passing only shows that it copied the label. All 8 Claude models passed all 5 diagnostic tests of `prevalence-filtering`. `mode`, `expected_absent`, test names and input file names also give answers away.

The shape has to say how to write a result. It does not have to say which result is right.

## Decision

Every test of a protocol shows the executor the same result shape. Only the inputs differ.

1. **Two outcome kinds.** Every `result.yaml` has `outcome: completed | refused` and `observation`. In `test.yaml`, an accepted outcome's protocol-specific name moves to `label`, which only the checker reads. An optional `expected_reason` is a phrase that must appear in `observation`, checked like `expected_warning` (ADR 0017). When several accepted outcomes share a kind, any match passes, and `run.yaml` records the label of the one that matched. Corrections such as `orientation_corrected` are `completed` outcomes, told apart by their evidence.
2. **One output schema per protocol.** `tests/outputs.yaml` declares each output key and its type or types, and each table's header rule. The shape shows this schema to every test. The validator checks each test's expected keys and values against it. A correct execution still cannot fail on a key name (ADR 0016).
3. **Left out of the shape:** `mode`, `numeric_tolerance`, accepted outcomes, `expected_absent`, `name` and `description`. They stay in `test.yaml` for the checker.
4. **Opaque test IDs.** `--shape --bundle` names tests `test_01`, `test_02` and so on, in random order, and names input files after their input key. The mapping goes in `source.yaml`, which the executor never sees, and `run.yaml` keeps the real names.
5. **One-step migration.** Checker and skill 0.5.0 read only the new format and refuse a `tests/` directory without `outputs.yaml`. `waldronlab/agent-protocols` converts in the same release. `run_record` stays at 1.

The exact format of `outputs.yaml` goes in `PROTOCOL_STANDARD.md` with the implementation.

## Alternatives Considered

- **Hide only the labels.** Rejected: `mode`, `expected_absent` and the key sets still give the answer away.
- **Withhold the shape.** Rejected for ADR 0016's reason: a correct execution could fail on a key name.
- **Grade `observation` with a model.** Rejected: the thing under test would be grading itself.
- **Accept both formats for one version.** Rejected: only one repository has tests, and its conversion is mechanical.

## Consequences

- A diagnostic pass shows that the executor found the problem. Diagnostic passes from checker 0.3.0 and 0.4.0 are not evidence for #5 or for a `verified-with-benchmark` review.
- Authors maintain `outputs.yaml`, and the validator catches drift.
- Diagnostic tests can be benchmarked (#64). Offering `refused` tells an agent without the protocol that refusing is allowed, so the measured benefit of the protocol is a lower bound.
- **Limits:** a blind shape does not stop an executor from reading the checkout. Isolation does that (ADR 0019). A refusal test is still easier than an exact one. If an optional input appears in only some tests, which inputs are present can still give the answer away, so authors should supply the same input keys to every test.

Drafted with Claude Code. Read and approved by Otto Infield-Harm. Shortened by Levi Waldron with Claude Code.
