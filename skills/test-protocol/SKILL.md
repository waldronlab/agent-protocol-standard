---
name: test-protocol
description: Execute a protocol's tests from its tests/ directory, write results in the standard's result contract, and check them with the deterministic checker
version: 0.2.0
category: protocols
author: waldronlab
tags: [protocol, tests, benchmark, verification, provenance]
---

# test-protocol

Runs the tests a protocol carries under `protocols/<name>/tests/`, following the result contract
in the "Tests" section of `PROTOCOL_STANDARD.md`. The agent performs the protocol; the checker
decides pass or fail. The agent never reads the expected answers.

## Usage

- "Run the tests for independent-filtering-variance"
- "Test the prevalence-filtering protocol in waldronlab/agent-protocols"
- "Run only the variance_rows test"

## Prerequisites

- A local checkout of the content repository holding the protocol, at a known commit.
- A local checkout of `waldronlab/agent-protocol-standard` for `scripts/check_test_result.py`,
  with Python 3.10+, `pydantic`, and `pyyaml`.
- Any language or tools needed to perform the protocol. The protocol says what it needs in
  `## Materials`.

## Process

### 1. Locate the protocol and its tests

1. Find `protocols/<name>/protocol.md` and `protocols/<name>/tests/`. If there is no `tests/`
   directory, say so and stop; there is nothing to run.
2. Choose a **results directory** outside the protocol directory, new and empty, for example
   `$(mktemp -d)/<name>-results`. Every run gets its own.
3. Record the moment you start, in UTC, as `started`. Record the prompt that started this run,
   verbatim.

### 2. Take the shape and the source snapshot

Run, from the standard repository:

```sh
python3 scripts/check_test_result.py --shape <protocol>/tests <results directory>
```

This prints the **result shape** of every test (add `--test <name>` for one) and writes
`source.yaml` into the results directory. The shape gives you, per test: the inputs, the mode,
the tolerance, the top-level keys your `result.yaml` must contain with their types, each file
slot with its format and header, and in diagnostic mode the accepted outcome labels with the
keys each one expects present or absent. Values are withheld. Do not look for them anywhere
else.

If the command refuses because the results directory is not empty or lies inside the protocol
directory, pick another directory and run it again.

### 3. Perform each test

For each test in the shape, in any language:

1. Read `protocol.md` in full. Read the test's `inputs`; a file slot `{path: ...}` is relative
   to the test's directory, which the shape names.
2. Check every condition in `## Materials` against the inputs before Step 1. A *must* condition
   that fails is a refusal. A *should* condition that fails is a warning: proceed, and keep the
   warning text for `result.yaml`.
3. Perform the protocol on those inputs exactly as written. Where the protocol says to record a
   quantity, that quantity is what a top-level key in the shape asks for.
4. Write `<results directory>/<test name>/result.yaml`:
   - **exact mode**: one key per top-level key in the shape. A file slot is written as
     `{path: <file name>}` and the file goes in the same subdirectory as a CSV with the header
     the shape gave, or the header the protocol prescribes when the shape says `withheld`.
   - **diagnostic mode**: `outcome`, one of the accepted labels; `observation`, one sentence
     saying what you found; and whatever keys that outcome expects present. If you refused
     because the input violates a *must* condition, say so in `observation` and write nothing
     the protocol would have produced.
   - **either mode**: `warnings`, a list of strings, when a *should* condition was not met. Each
     entry names the condition and the consequence the protocol gives for it. Omit the key when
     there was nothing to warn about.
5. Record more than the shape asks for if it helps a reader; extra top-level keys are ignored.
   Inside a nested mapping, record exactly the entries the protocol produces; an extra entry is a
   wrong answer.

You do **not** read `test.yaml`, any `expected_outputs`, or any file in the test directory that
the inputs did not name. The checker compares; you execute.

### 4. Write `executor.yaml`

At the top of the results directory, before invoking the checker:

```yaml
started: 2026-10-18T14:02:11Z
finished: 2026-10-18T14:09:40Z
executor:
  agent: claude-code
  harness: Claude Code 2.1.0
  model: claude-fable-5-1
  language: R
  invocation:
    kind: skill
    skill: test-protocol 0.2.0
  prompt: |
    Run the tests for independent-filtering-variance.
```

`agent` is required. Fill the rest when you know it; `kind` is `skill` when this skill invoked
the run. Do not write `run_record`, `protocol`, `version`, `repository`, `protocol_commit`,
`uncommitted`, `source_digest`, `checker`, or `tests`; the checker owns those. Additional keys,
such as token counts or an experimental condition, are kept.

### 5. Check

```sh
python3 scripts/check_test_result.py <protocol>/tests <results directory>
```

The checker compares every test that has a result subdirectory, prints each as PASS, FAIL, or
NOT_RUN with the failing comparisons, and writes `run.yaml` at the top of the results directory.
Exit status 0 means every compared test passed, 1 means at least one failed, 2 means the
contract was not met (a missing `executor.yaml`, a changed checkout, a malformed test).

If the checker reports that the protocol or tests changed since `--shape`, the checkout moved
during the run. Start again from step 2 in a fresh results directory.

## Output Format

1. The result shape, as printed by `--shape`.
2. For each test, what you did and where its `result.yaml` is.
3. The checker's report, verbatim.
4. The contents of `run.yaml`, so the user can attach it to the pull request or issue it belongs
   to. A run is not a review; do not add anything to `protocol.md`.
5. On failures, no verdict on whose fault it is. Say which comparisons failed and what you
   observed; whether the executor, the environment, the protocol, or the test is wrong is found
   out afterwards.
6. A closing line naming this skill and its version:

   > 🛠️ Skill executed: `test-protocol` v`0.2.0` (`waldronlab/agent-protocol-standard`)

## Notes

- This skill tests execution, not conformance. Whether `protocol.md` conforms to the standard is
  the validator's job (`scripts/validate_protocol.py`).
- Where run records are kept is not yet defined (`waldronlab/agent-protocol-standard#44`).
  Until it is, the record travels with the pull request or issue it is relevant to.
- The skill is language-agnostic. Perform the protocol in whatever language suits it; only
  `result.yaml` and the CSV files have a fixed form.
