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

Three things were undefined: the shape of a test, the shape of the thing a test checks, and what a
run leaves behind.

## Decision

### 1. A test is a directory

`protocols/<name>/tests/<test-name>/` holds `test.yaml` and any local data files. `test.yaml` has
`name` (matching the directory), `description`, `inputs`, and `evaluation`; in `exact` mode it also
has `expected_outputs` at the top level, and in `diagnostic` mode the expectations sit under each
accepted outcome instead. A file is always a mapping, `{path: ...}` inside the test directory or `{url: ...,
sha256: ...}` for data too large to commit, so that a bare string is never mistaken for one. The
full schema is in `PROTOCOL_STANDARD.md`.

### 2. Two evaluation modes

`exact`: every entry in `expected_outputs` must match the result, numbers within
`numeric_tolerance`. `diagnostic`: the executor must reach one of the listed `accepted_outcomes`,
each of which carries checkable evidence: `expected_outputs`, or `expected_absent` for a refusal,
which the checker verifies by the absence of the protocol's outputs. A label alone is not evidence.
The second mode exists for inputs that violate the protocol's stated requirements, where refusing
and repairing are both correct and silently proceeding is the failure.

Tables are CSV only, and the first column is an identifier compared as a string. Both are the
simplest rule that fits the existing fixtures; a second format or a per-column type declaration
waits for a test that needs one.

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

### 4. A run produces a run record, not a review

A review is a named person's judgement of a protocol. A run is a fact about one execution: which
agent, which model, which day, which tests passed. There will be many runs per version and they
say something different, so a run is not a review and nothing is added to the protocol when one
completes.

The checker writes a run record, `run.yaml`, naming the protocol and version, each test with its
result, the executing agent and model, the date, and the checker version. The format is in
`PROTOCOL_STANDARD.md` because the checker produces it. Where run records are kept is deferred to
#44: while runs are few, the person attaches the record to the pull request or issue they are
working on, and a collection is defined when the benchmarking study in #5 produces volume.

`verified-with-benchmark` keeps its ADR 0005 meaning. A human who has run the tests, or their own
benchmark, may record it once, as a judgement, citing the run record in Notes. No CI credential
and no automatic review: anyone runs the tests on their own machine with their own agent.

#22 proposes that trust tier 4 read that review, and #10 asks the runner to surface it. Both
continue to read reviews; neither reads run records.

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
- Running a protocol's tests becomes one way for a reviewer to earn `verified-with-benchmark`,
  with the same meaning the status has had since ADR 0005.
- Run records accumulate outside the protocol; their home is #44.
