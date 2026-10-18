# 0016. Protocol Tests: Fixtures, a Result Contract, and a Review Status

- **Status:** Proposed
- **Date:** 2026-10-18
- **Deciders:** Levi Waldron (User), AI Agent

## Context and Problem Statement

Issue #3 proposed a `tests/` directory beside `protocol.md` so that an execution of a protocol can
be checked against known inputs and expected outputs. The first protocol with tests,
`independent-filtering-variance` in `waldronlab/agent-protocols`, now carries eight fixtures merged
ahead of any schema. Their `test.yaml` files agree on `inputs`, `expected_outputs`, and `evaluation`
but improvise the rest, and nothing validates or runs them.

Three things were undefined: the shape of a test, the shape of the thing a test checks, and where a
run is recorded.

## Decision

### 1. A test is a directory

`protocols/<name>/tests/<test-name>/` holds `test.yaml` and any local data files. `test.yaml` has
five keys: `name` (matching the directory), `description`, `inputs`, `expected_outputs`, and
`evaluation`. A file is always a mapping, `{path: ...}` inside the test directory or `{url: ...,
sha256: ...}` for data too large to commit, so that a bare string is never mistaken for one. The
full schema is in `PROTOCOL_STANDARD.md`.

### 2. Two evaluation modes

`exact`: every entry in `expected_outputs` must match the result, numbers within
`numeric_tolerance`. `diagnostic`: the executor must reach one of the listed `accepted_outcomes`,
each of which may carry its own `expected_outputs`. The second mode exists for inputs that violate
the protocol's stated requirements, where refusing and repairing are both correct and silently
proceeding is the failure.

Custom evaluation scripts, proposed in #3, are not defined. Nothing needs them yet.

### 3. A result contract

The executor writes `result.yaml` into a result directory. Its keys mirror `expected_outputs`;
file slots are filled with `{path: ...}` in the same directory. In diagnostic mode it also carries
`outcome` and a one-line `observation`. A deterministic checker compares the result to the test.
Without this contract there is nothing machine-checkable, and the agent's own report of success
would be the only evidence.

The executor is given `protocol.md`, `inputs`, and the result shape: the keys, nesting, file slots,
mode, and outcome labels of the test with every expected value withheld, printed by the checker.
It does not read `expected_outputs` itself. Without the shape a correct execution could fail on
a key name; with the values it would not be a test.

### 4. A run is recorded as a review

A passing run is recorded as a review with status `verified-with-benchmark`, whose Notes name the
executing agent, the model, and the number of tests passed. ADR 0005 defined the status as "executed
the protocol and verified the outputs against a benchmark or expected result", and that definition
stands: a reviewer who verified against their own data records the same status. The tests are the
reproducible form of that benchmark, and the first thing that produces the status routinely. No new
frontmatter field, no CI credential: anyone runs the tests on their own machine with their own agent
and records what happened.

This is also where two open questions land. #22 proposes that trust tier 4 mean "registered, and
the current version carries a `verified-with-benchmark` review"; a recorded run is the evidence that
tier would read. #10 asks the runner to surface review status at selection time; a recorded run is
what it would surface.

### 5. CI validates tests, it does not run them

`validate_protocol.py` checks each `test.yaml` against the schema and that local files exist. It
does not fetch URLs or execute anything. Running a test needs a model, and a model in CI is a
shared cost and a shared credential; see item 4.

## Alternatives Considered

- **Free-form `expected_outputs` compared by an evaluating model.** Rejected: the thing under test
  would be grading itself.
- **Hash matching of output files**, as #3 proposed for deterministic steps. Rejected as the primary
  mechanism: a trailing newline or a column order fails a correct result. Tables are compared as
  tables, with tolerance.
- **A `has_tests` flag in `PROTOCOLS.yaml` and the registry**, as #3 proposed. Deferred to the
  registry-schema work in #22. Test availability and a passing run are different facts: tests exist
  before anyone runs them. The review records the run; whether the index should also list the tests
  is #22's question.
- **Running tests in CI on every pull request.** Rejected for now, per item 5.

## Consequences

- Content repositories gain an optional `tests/` directory per protocol; CI rejects a malformed one.
- The eight existing fixtures are reformatted to the schema. Their expected values do not change.
- A `test-protocol` skill is written beside `protocol-runner`, implementing the result contract.
  #37 already distinguishes it from the `validate-protocol` skill: that one checks the document
  conforms, this one checks an execution gets the right answer.
- The benchmarking study in #5 needs this harness and nothing in it conflicts with #5's design.
- A checker script, `scripts/check_test_result.py`, is the only code that decides pass or fail.
- Running a protocol's tests becomes one way to earn `verified-with-benchmark`, with the same
  meaning the status has had since ADR 0005.
