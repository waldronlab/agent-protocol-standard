# 0019. Isolate the Executor from the Checker

- **Status:** Proposed
- **Date:** 2026-11-02
- **Deciders:** Levi Waldron, Otto Infield-Harm

## Context and Problem Statement

ADR 0016 defined a result contract in which the executor is given the inputs, the result shape
and `protocol.md`, and "does not read `expected_outputs` itself". Nothing enforced that beyond a
sentence in the `test-protocol` skill, and two other parts of the contract undercut it. Issue
#59 reports three Claude Code runs of `test-protocol` 0.2.0 against `shannon-diversity`, each
with a run record showing nine passes. Auditing their transcripts showed two of the records
were not what the contract describes:

- One executor failed a test, read the checker's failure line, `expected 2 within 1e-12`,
  corrected its result by hand and checked again in the same results directory. The checker
  overwrote `run.yaml`, as the standard specified, and the record shows a clean pass.
- Another wrote `finished` as a literal eleven minutes in the future. The checker validated
  only that it was a timestamp with a timezone.

No executor opened a `test.yaml` or an expected file, but each was directed into `tests/` to
read its inputs, where the expected files sit beside them. The benchmarking study in #5
compares executors across capability tiers, and a record like these makes that comparison
meaningless.

## Decision

### 1. A bundle holds what the executor may see

`check_test_result.py --shape` takes `--bundle <directory>` and copies into it `protocol.md`, the
`protocol.md` of every protocol it uses, transitively, the files each test's inputs name, and
the shape as `shape.yaml`. Nothing else: no `test.yaml`, no expected file, no dependency's tests.
The executor writes into `<bundle>/results/`, and the checker reads from there. The bundle must
be outside the checkout and separate from the results directory, which caches remote expected
files.

Dependencies are copied from the checkout, found by file presence at
`<protocols directory>/<name>/protocol.md` and required to be at the pinned version, as #54
proposes for same-repository resolution. A dependency that is not in the checkout cannot be
bundled until #55 defines cross-repository resolution; the checker refuses it rather than
guessing.

The copying is in the checker, not in the skill, so that it is tested code and the same for
every agent.

### 2. The executor is not the one who checks

The `test-protocol` skill (0.3.0) defaults to an **isolated** mode wherever the agent software
can start a fresh agent: the invoking agent makes the bundle, starts an executor with a fixed
brief that names only the bundle, takes `started` and `finished` from the clock on either side,
writes `executor.yaml`, and runs the checker. The executor never sees checker output, so it
cannot learn an answer from a failure, and it is never told where the tests are. Where no
fresh executor can be started, a **single-session** mode follows the same brief from the bundle.

### 3. A run is checked once

The checker refuses a results directory that already holds `run.yaml`. A failed run is reported
as it stands; another attempt is a new run. A contract error writes no record, so a malformed
`executor.yaml` can still be corrected. Failure messages keep naming expected values, since
reviewers need them, and once a run cannot be checked twice that does no harm.

### 4. The checker's own times bound the run

`run.yaml` gains `shaped`, when `--shape` took the snapshot, and `checked`, when the results
were compared, both reserved. The checker refuses `started` after `finished`, `finished` before
`shaped`, and `finished` after `checked`.

### 5. The record says how the executor was isolated

`executor.isolation` is `subagent`, `container`, or `none`. Like `invocation.kind`, two runs that
differ only there are different experiments.

`run_record` stays at 1. It is incremented when a defined key changes meaning, and these
changes add keys without changing any.

## Alternatives Considered

- **Withhold expected values from failure messages.** Rejected: a reviewer diagnosing a failure
  needs them, and with checking once they can no longer be used to repair a run.
- **Keep every check, numbering attempts in the record.** Rejected for now: it preserves the
  evidence but still lets an executor iterate to a pass, and the record would need a rule for
  which attempt counts. A study that wants attempts can make several runs.
- **Copy the inputs in the skill rather than the checker.** Rejected: an agent following prose
  can copy the wrong thing, such as the whole `tests/` directory, and prose is not tested.
- **Make the isolated mode opt-in.** Rejected: the default should be the mode whose records mean
  what they say.

## Consequences

- None of this makes cheating impossible. An executor that can read the filesystem can still
  look for the checkout, or delete `run.yaml` and check again. These are now deliberate
  violations of the contract rather than permitted paths, and a transcript audit shows them.
  A run offered as evidence, such as one cited by a `verified-with-benchmark` review or the
  study in #5, should run the executor where only the bundle is mounted.
- A protocol whose dependencies live in another repository cannot be bundled until #55 is done.
  Its tests can still be run without `--bundle`, recorded as `isolation: none`.
- Executors and harnesses written against checker 0.2.0 that check a results directory more
  than once, or write timestamps that do not fit, now get exit status 2.
- The skill's executor brief is fixed by the skill's version, so it is not recorded per run;
  `prompt` remains the person's prompt.
