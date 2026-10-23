# 0017. Conditions on Materials: Where They Live and What a Violation Means

- **Status:** Proposed
- **Date:** 2026-10-23
- **Deciders:** Levi Waldron (User), AI Agent

## Context and Problem Statement

Reviewing a Shannon diversity protocol (waldronlab/agent-protocols#53), the rule about rarefaction
appeared in three places: a Materials bullet, a sentence in Step 2, and a Notes paragraph. None of
them said what an executor should do with a count table that had not been rarefied. The author had
no rule to follow: the standard required a `## Materials` heading and recommended two bullet
groups, software and reference data, and said nothing about where conditions on inputs belong.

Existing protocols had converged on a convention the standard never stated: conditions written as
prose under Materials, then a "Step 1: Validate" restating them. Steps could contain anything.
Diagnostic tests referred to "a requirement the protocol states" without saying where, and could
check only a refusal, through `expected_absent`. There was no way for a protocol to say "proceed,
but warn", which is what the rarefaction case needs: the index is computable, and the user needs to
know the values are not comparable across samples.

Issue #46 records the discussion.

## Decision

**Materials is the single home for conditions on inputs.** It lists every input the protocol
consumes (data, parameters, software, reference data) and every condition an input must or should
satisfy. Steps consume materials and do not introduce new conditions on them. Statements about what
the protocol does or does not do belong in the overview or Notes.

**Two severity tiers, written with RFC 2119 words.** A condition written with *must* is a
requirement: an executor that finds it violated stops, reports which condition failed, and produces
none of the protocol's outputs. A condition written with *should* is an advisory: the executor
proceeds, warns the user naming the condition and its consequence, and records the warning with the
execution.

**The check happens before Step 1.** Every condition in Materials is checked against the inputs
before the first step runs, so a protocol no longer needs a validation step for anything Materials
already states. A check that can only be made during computation, such as a sample whose total is
zero, stays in the step where it arises.

**Scope.** The RFC 2119 reading applies to conditions written in a protocol's Materials section.
The standard's own prose, which already uses *must* and *should* in their ordinary sense throughout,
is not reinterpreted.

**The test contract gains the warning tier.** A diagnostic outcome may carry `expected_warning`, a
phrase that must appear in the executor's `warnings`. It accompanies evidence (`expected_outputs`
or `expected_absent`) rather than replacing it, since a warning is the executor's word as much as
the outcome label is. `result.yaml` may carry `warnings`, a list of strings, in either mode;
`warnings` joins `outcome` and `observation` as a reserved key. The result shape shows that
`warnings` exists and withholds the phrase, so an executor warns because the protocol said to, not
because the shape did.

The protocol-runner skill checks Materials before Step 1 and lists warnings with the departures.
The test-protocol skill writes them into `result.yaml`.

## Alternatives Considered

- **One tier: every condition is a requirement.** Rejected. The rarefaction case is the common
  one in microbiome work: the computation is well defined on the input, and the problem is with
  what the user does with the output. Refusing would push authors to write the condition as a note,
  which is where it was.
- **A required "Step 1: Validate".** Rejected. It restates Materials, drifts from it, and puts the
  answer to "what are the inputs" in two places. Existing protocols that have one remain valid; the
  step is now redundant rather than wrong.
- **A structured schema for materials** (one YAML block per input with typed constraints). Rejected
  for now. Conditions like "samples should share a sequencing depth" are prose, and a schema that
  cannot express them would be worked around. Prose with two reserved words is checkable by an
  agent and reviewable by a person. A schema waits for a validator that would use it.
- **Adopt RFC 2119 for the standard document itself.** Rejected. It would give about twenty existing
  uses of *must* and *should* a meaning nobody intended, each of which would need auditing, for no
  benefit to protocol authors.
- **Make `expected_warning` evidence on its own.** Rejected. An outcome checked only by a warning
  string is checked only by what the executor said about itself, which is the rule ADR 0016 set
  against labels.

## Consequences

Protocol authors have one place to write conditions and two words to write them with. Reviewers
have a rule to apply when a condition appears in a step or a note. Executors have a defined action
for each tier, and the test contract can check both.

The validator is unchanged: it cannot check prose semantics, and the rule is enforceable in review.
The `expected_warning` and `warnings` keys are validated and checked by the existing tooling.

Existing protocols with a validation step remain valid. Moving their conditions into Materials is a
content change for each repository, made as protocols are next revised.

The runner's before-Step-1 check is part of its execution contract, which issue #15 proposes to
move into `PROTOCOL_STANDARD.md`; this ADR puts the condition rules there directly and leaves the
rest of #15 open.
