# 0020. Record What Decides a Test Run's Outcome

- **Status:** Proposed
- **Date:** 2026-11-18
- **Deciders:** Levi Waldron, Otto Infield-Harm

## Context and Problem Statement

ADR 0019 isolated the executor of a protocol's tests from the checker. Issue #61 reports runs of
`test-protocol` 0.3.0 in isolated mode, with Claude subagents and with small open-weight models
through a minimal tool-calling harness. Each check worked as specified, but four facts that
decided the outcome were missing from `run.yaml`:

1. **What the executor wrote.** Weak executors replied with a plausible result for every test
   while writing nothing. The checker correctly recorded `not_run`, but the record kept no trace
   of what was written, so a reader could not later tell a run's results from any others. The
   same is true of a pass.
2. **The harness's settings.** Whether the model's reasoning stays in its context, the context
   window, the output cap per turn, the system prompt, and how clearly a tool reports a bad call
   each decided whether a run could finish. `harness: <name> <version>` records none of them. A
   model tag such as `qwen3:4b` can move and hides the quantization.
3. **Abandoned runs.** ADR 0019 forbids checking a run twice, but a run that was shaped, started
   and abandoned before the check leaves nothing behind. An invoker could abandon runs that look
   bad, check only the good ones, and the records would look clean.
4. **How the executor was isolated.** `isolation: container` covers a container with only the
   bundle mounted, an OS sandbox around a tool loop, and a virtual machine.

The study in #5 compares runs across executors, and the archive in
`waldronlab/agent-protocol-runs` (#44) keeps their records. Both need these facts in the record.

## Decision

### 1. The record carries a digest of the results

The checker writes `results_digest` into `run.yaml`: a sha256 over the results, taken at check
time, before comparing, and computed as `source_digest` is: for each file in order of its path,
the path, a NUL byte, the contents and a NUL byte.

- With a bundle it covers every file under `<bundle>/results/` except symlinks (below), including
  files the executor left there beyond its results. It does not cover `<bundle>/work/`, the executor's scratch space.
- Without a bundle it covers the subdirectories of the results directory. The top-level files
  (`source.yaml`, `executor.yaml`) are the invoker's and the checker's, and `.remote/` is the
  checker's download cache.
- Each path is written as `results/<path under that directory>`, so the digest of a copy kept as
  `results/` beside its `run.yaml`, as the archive keeps it, can be recomputed without knowing
  where the bundle was.
- Symlinks are neither followed nor covered. `source_digest` refuses them, but the executor
  controls the results tree, and a refusal would let it prevent its own record. The omission is
  not silent where it matters: the archive refuses symlinks, and a copy that replaces one with the
  file it points to no longer matches the digest.

`results_digest` is reserved: `executor.yaml` may not supply it.

### 2. Every shaped run is checked, including abandoned ones

A run stopped before the executor finished still gets an `executor.yaml`, with `abandoned:
<reason>` at the top level, and is checked. `abandoned` is a defined key: when present it is
non-empty text, and the checker copies it into the record and prints it. The checker needs no
other change. It already records every test without a result as `not_run`.

`abandoned` does not change the exit status. The exit status reports only the tests compared, so an
abandoned run whose compared tests all passed exits 0, as any run with `not_run` tests already
does. Whether a run was abandoned, and how many tests were not run, is read from the record, which
is what the archive and its index count.

The `test-protocol` skill gains the rule that every run started with `--shape` ends in a check.
The checker cannot enforce it, since a run that is never checked leaves nothing for it to see.
The rule makes discarding a run a violation rather than a permitted path.

### 3. Exit status 2 has two meanings

The checker writes `run.yaml` and exits 2 when no test has a result ("Nothing was compared"). The
skill said exit 2 means no record was written, and an abandoned run hits the other case every
time. The exit
status is kept, and the wording changes in the standard, the skill and the checker: exit 2 is
either a contract error, with no record, or a run in which nothing was compared, with one. The
checker's message for the second says the record was written.

### 4. Settings that decide the outcome are recommended keys first

The standard and the skill recommend recording, under `executor`:

- `harness_config`, a mapping of every harness setting that changes the executor's behaviour;
- `model_digest` and `quantization`, for open-weight models;
- `isolation_method`, free text saying how `isolation` was achieved.

They are recommended, not defined. Only a few harnesses have been used so far, and the names
will probably change once a second is in common use. The standard already preserves additional
keys, so nothing needs to change to record them, and they are promoted once they settle.

`isolation` keeps its three values. `container` is defined by what the executor could reach,
nothing but the bundle, not by how that was enforced. A container, an OS sandbox or a virtual
machine that meets that keeps the value and says how in `isolation_method`. One that cannot
honestly claim it is the case for a new value.

### 5. The executor's reply is not evidence

The skill reports the executor's reply, but the checker's report is the evidence, and the skill
says so where they disagree.

### Versions

`check_test_result.py` becomes 0.4.0 and the `test-protocol` skill 0.4.0. `run_record` stays
at 1: keys are added, and none changes meaning.

## Alternatives Considered

- **Amend ADR 0019 in place.** Rejected: checking abandoned runs and the results digest are new
  decisions, not corrections to what 0019 says.
- **Define `harness_config`, `isolation_method` and `model_digest` now.** Rejected for now: a
  defined key's meaning is fixed by `run_record`, and these names have been tried with one
  harness.
- **Add `sandbox` and `vm` to `isolation`.** Rejected: `isolation` says what the executor could
  reach, which is what a reader comparing runs needs. How that was enforced is a detail, kept in
  `isolation_method`.
- **Digest `work/` as well.** Rejected: it is scratch space, often large, and not what was
  compared. Its contents are in the transcript.
- **Hash paths relative to `results/`, without the prefix.** Equivalent in strength. The prefix
  matches how the archive keeps a run, `results/` beside `run.yaml`, and how `source_digest`
  names its files relative to the protocol directory (`tests/...`).
- **A nonzero exit status for an abandoned run.** Rejected: the exit status reports comparisons,
  and a run with `not_run` tests already exits 0 when the rest pass. Making `abandoned` change it
  would give the same results two exit statuses depending on why tests were not run.
- **A new exit status for "nothing compared".** Rejected: the record's presence already tells
  the two cases apart, and a new status would change what callers of 0.3.0 see.

## Consequences

- A copy of a run's results can be shown to be the one that was checked, wherever it is kept.
  The archive's validator recomputes `results_digest` the same way.
- Abandoned runs are counted apart from runs where the executor wrote nothing.
- Records written by checker 0.3.0 have no `results_digest`. The archive accepts them, and
  verifies the digest only when the record has one.
- Nothing stops an invoker from discarding a run that was never checked. The rule makes it a
  violation, but nothing records that a run was shaped, so it cannot be detected yet.
- `harness_config` and the other recommended keys can be written differently by different
  people until they are defined. An index that compares runs on them has to allow for that.
