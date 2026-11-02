---
name: test-protocol
description: Execute a protocol's tests from a bundle that holds only what the executor may see, by default in a fresh executor, then check the results once with the deterministic checker
version: 0.3.0
category: protocols
author: waldronlab
tags: [protocol, tests, benchmark, verification, provenance]
---

# test-protocol

Runs the tests a protocol carries under `protocols/<name>/tests/`, following the result contract
in the "Tests" section of `PROTOCOL_STANDARD.md`. The executor performs the protocol from a
**bundle** that holds the protocol, its inputs and the result shape, and nothing else. Whoever
invoked the executor checks the results, once. The checker decides pass or fail. See
[ADR 0019](../../docs/adr/0019-isolate-the-executor-from-the-checker.md).

## Rules

These hold in both modes, for you and for the executor. A run that breaks one is reported as
such, not repaired.

1. Never open `test.yaml`, any expected-output file, or anything else under a protocol's
   `tests/` directory. The checker reads them; nobody else needs to.
2. The executor works only from the bundle.
3. Run the checker once. After a failure, report it. Do not edit results, check again, or start
   another executor. Another attempt is a new run, from step 2 in new directories, and only when
   the person asks for one.
4. Take every timestamp from the clock, `date -u +%Y-%m-%dT%H:%M:%SZ`. Never write one by hand.
5. Change nothing in the protocol, its tests, or the bundle's `protocol.md`.

## Usage

- "Run the tests for independent-filtering-variance"
- "Test the prevalence-filtering protocol in waldronlab/agent-protocols"
- "Run only the variance_rows test"
- "Run the tests in a single session"

## Prerequisites

- A local checkout of the content repository holding the protocol, at a known commit.
- A local checkout of `waldronlab/agent-protocol-standard` for `scripts/check_test_result.py`,
  with Python 3.10+, `pydantic`, and `pyyaml`.
- Any language or tools needed to perform the protocol. The protocol says what it needs in
  `## Materials`.

## Modes

- **Isolated** (the default). A fresh executor with no context from this session performs the
  protocol: a subagent, a separate agent session, or an agent in a container. It is told only
  where the bundle is, so it does not know where the tests are, and it never sees checker
  output, so it cannot learn an answer from a failure. Use it whenever your agent software can
  start one. Record `isolation: subagent`, or `isolation: container` when the executor runs
  where only the bundle is mounted.
- **Single session**, when no fresh executor can be started or the person asks for it. You
  perform the protocol yourself from the bundle. Record `isolation: none`.

## Process

### 1. Locate the protocol and choose two directories

1. Find `protocols/<name>/protocol.md` and check that `protocols/<name>/tests/` exists. If it
   does not, say so and stop; there is nothing to run. Do not open anything inside it.
2. Choose a **results directory** and a **bundle directory**: new, empty, outside the checkout,
   and neither inside the other. For example, `$(mktemp -d)/<name>-results` and
   `$(mktemp -d)/<name>-bundle`. Every run gets its own pair.
3. Record the prompt that started this run, verbatim.

### 2. Shape and bundle

Run, from the standard repository:

```sh
python3 scripts/check_test_result.py --shape <protocol>/tests <results directory> --bundle <bundle directory>
```

Add `--test <name>` to run one test. This writes `source.yaml` into the results directory, the
snapshot the run is attributed to, and fills the bundle:

```text
<bundle>/
├── protocol.md
├── protocols/<name>/protocol.md   # each protocol it uses, for a composite
├── shape.yaml                     # inputs, mode, tolerance, and result shape per test
├── inputs/<test>/                 # the files each test's inputs name
└── results/                       # empty; the executor writes here
```

If the command refuses a directory, choose another and run it again. If it refuses a dependency
that is not in the checkout, stop and say so: bundling a dependency from another repository
waits on `waldronlab/agent-protocol-standard#55`.

### 3. Execute

**Isolated:**

1. Record `started` from the clock, immediately before you start the executor.
2. Start the executor with the [executor brief](#executor-brief), `<BUNDLE>` replaced by the
   bundle's absolute path, and nothing else. Do not add the repository's path, hints, or a
   summary of the protocol. If you choose the executor's model, note which.
3. When it replies, record `finished` from the clock.
4. Do not read, fix, or complete its results. What it wrote is the run.

**Single session:** record `started`, follow the executor brief yourself, then record
`finished`.

### 4. Write `executor.yaml`

At the top of the **results** directory, before invoking the checker:

```yaml
started: 2026-10-18T14:02:11Z
finished: 2026-10-18T14:09:40Z
executor:
  agent: claude-code
  harness: Claude Code 2.1.0
  model: claude-sonnet-5-5       # the executor's model
  language: Python               # as the executor reported it
  isolation: subagent            # subagent | container | none
  invocation:
    kind: skill
    skill: test-protocol 0.3.0
  prompt: |
    Run the tests for independent-filtering-variance.
```

`agent` is required. Fill the rest when you know it. `prompt` is the person's prompt; the
executor brief is fixed by this skill's version, so it is not recorded again. Do not write
`run_record`, `protocol`, `version`, `repository`, `protocol_commit`, `uncommitted`,
`source_digest`, `shaped`, `checked`, `checker`, or `tests`; the checker owns those.
Additional keys, such as token counts or an experimental condition, are kept.

### 5. Check, once

```sh
python3 scripts/check_test_result.py <protocol>/tests <results directory>
```

The checker reads the results from the bundle, compares every test that has a result
subdirectory, prints each as PASS, FAIL, or NOT_RUN with the failing comparisons, and writes
`run.yaml` into the results directory. Exit status 0 means every compared test passed, and 1
means at least one failed.

Exit status 2 means the contract was not met and no record was written:

- A problem in `executor.yaml`, such as a missing field: correct it, using only the times you
  recorded from the clock, and check again.
- The protocol or tests changed since `--shape`: the checkout moved during the run. Start again
  from step 2 in new directories.
- The run was already checked: you broke rule 3. Report the existing record as it stands.

## Executor brief

Send this verbatim, with `<BUNDLE>` replaced. In single-session mode, follow it yourself.

```text
You are executing the tests of a scientific protocol. Everything you may use is in <BUNDLE>:

- protocol.md: the protocol. Read it in full before anything else.
- protocols/<name>/protocol.md: the protocols it uses, if it uses any.
- shape.yaml: for each test, its inputs, mode, numeric tolerance, and the shape of the result
  to write. Expected values are withheld.
- inputs/<test>/: each test's input files. An input written {path: ...} is relative to that
  test's directory, which shape.yaml names.

Read nothing outside <BUNDLE>, and do not look for the protocol's repository or its tests. Keep
any scripts or scratch files in <BUNDLE>/work/.

For each test in shape.yaml, in any language:

1. Check every condition in the protocol's ## Materials against the inputs before Step 1. A
   failed *must* condition is a refusal. A failed *should* condition is a warning: proceed,
   and keep the warning.
2. Perform the protocol on the inputs exactly as written. Where it says to record a quantity,
   that quantity is what a top-level key in the shape asks for.
3. Write <BUNDLE>/results/<test>/result.yaml:
   - exact mode: one key per top-level key in the shape. A file slot is {path: <file name>},
     and the file goes beside result.yaml as CSV, with the header the shape gives, or the
     header the protocol prescribes when the shape says withheld.
   - diagnostic mode: outcome, one of the accepted labels; observation, one sentence saying
     what you found; and the keys that outcome expects present. If you refused, say why in
     observation and write nothing the protocol would have produced.
   - either mode: warnings, a list of strings, one per should condition not met, naming the
     condition and the consequence the protocol gives. Omit it when there is nothing to warn
     about.
   Inside a nested mapping, record exactly the entries the protocol produces; an extra entry
   is a wrong answer. Extra top-level keys are allowed.

Do not run any checker. When every test is written, reply with one line per test: its name and
what you wrote, then the language you used.
```

## Output Format

1. The mode, and the results and bundle directories.
2. For each test, what the executor did, from its reply, and where its `result.yaml` is.
3. The checker's report, verbatim.
4. The contents of `run.yaml`, so the person can attach it to the pull request or issue it
   belongs to. A run is not a review; do not add anything to `protocol.md`.
5. On failures, no verdict on whose fault it is and no second attempt. Say which comparisons
   failed and what the executor observed; whether the executor, the environment, the protocol,
   or the test is wrong is found out afterwards.
6. A closing line naming this skill and its version:

   > 🛠️ Skill executed: `test-protocol` v`0.3.0` (`waldronlab/agent-protocol-standard`)

## Notes

- The bundle and a fresh executor prevent accidents, not intent. An executor that can read
  the filesystem can still go looking for the checkout. For a run offered as evidence, such as
  one cited by a `verified-with-benchmark` review or the benchmarking study in
  `waldronlab/agent-protocol-standard#5`, run the executor where only the bundle is mounted and
  record `isolation: container`.
- This skill tests execution, not conformance. Whether `protocol.md` conforms to the standard is
  the validator's job (`scripts/validate_protocol.py`).
- Where run records are kept is not yet defined (`waldronlab/agent-protocol-standard#44`).
  Until it is, the record travels with the pull request or issue it is relevant to.
- The skill is language-agnostic. Perform the protocol in whatever language suits it; only
  `result.yaml` and the CSV files have a fixed form.
