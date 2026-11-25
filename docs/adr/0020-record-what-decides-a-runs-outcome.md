# 0020. Record What Decides a Test Run's Outcome

- **Status:** Accepted
- **Date:** 2026-11-18
- **Deciders:** Levi Waldron, Otto Infield-Harm

Amends ADR 0019.

## Context

Issue #61 reports runs of `test-protocol` 0.3.0 in isolated mode, with Claude subagents and with small open-weight models. Each check worked as specified, but four facts that decided the outcome were missing from `run.yaml`:

1. **What the executor wrote.** Weak executors replied with a plausible result for every test while writing nothing. The record kept no trace of what was written, for a failure or a pass.
2. **The harness's settings.** Context window, output cap, system prompt and whether reasoning stays in context each decided whether a run could finish. `harness: <name> <version>` records none of them, and a model tag such as `qwen3:4b` can move and hides the quantization.
3. **Abandoned runs.** A run that was shaped and then abandoned leaves nothing behind, so an invoker could check only the runs that look good.
4. **How the executor was isolated.** `isolation: container` covers a container, an OS sandbox and a virtual machine.

The study in #5 and the archive in `waldronlab/agent-protocol-runs` (#44) both need these facts.

## Decision

1. **A digest of the results.** The checker writes `results_digest` into `run.yaml`: a sha256 over the executor's results, taken before comparing and computed as `source_digest` is. It covers `<bundle>/results/` but not `work/`. Without a bundle, it covers the test subdirectories of the results directory. Symlinks are skipped instead of refused, because the executor controls this tree and a refusal would let it prevent its own record. `executor.yaml` may not supply this key.
2. **Every shaped run is checked.** A run stopped early gets an `executor.yaml` with `abandoned: <reason>` and is checked like any other. The checker copies the reason into the record and prints it. The `test-protocol` skill requires every run started with `--shape` to end in a check.
3. **Each exit status has one meaning.**

   | Exit | Meaning | `run.yaml` written? |
   |---|---|---|
   | 0 | every test ran and passed | yes |
   | 1 | at least one test failed | yes |
   | 2 | the checker could not run (contract error) | no |
   | 3 | no test failed, but at least one is `not_run`, including when nothing was compared | yes |

   The code depends only on the results, so `abandoned` does not change it. `check_citations.py` (#67) uses 3 the same way.
4. **Recommended keys for settings.** Under `executor`, the standard recommends `harness_config`, `model_digest`, `quantization` and `isolation_method`. They are recommended, not defined, until more than one harness has used them. `container` keeps its meaning (the executor could reach only the bundle), however that was enforced, and `isolation_method` says how.
5. **The executor's reply is not evidence.** Where it disagrees with the checker's report, the skill says so.

`check_test_result.py` and the skill become 0.4.0. `run_record` stays at 1.

## Alternatives Considered

- **Define the recommended keys now.** Rejected: the names have been tried with only one harness.
- **Add `sandbox` and `vm` to `isolation`.** Rejected: `isolation` records what the executor could reach, and that is what comparing runs needs.
- **Digest `work/` too.** Rejected: it is scratch space and is not compared.
- **A separate exit status for abandoned runs.** Rejected: the same results would get two exit statuses.

## Consequences

- A copy of a run's results can be shown to be the one that was checked. The archive's validator recomputes the digest the same way.
- Abandoned runs are counted separately from runs where the executor wrote nothing.
- Records from checker 0.3.0 have no `results_digest`. The archive accepts them.
- Nothing can detect a run that was shaped and never checked. The rule makes discarding it a violation.
- Until the recommended keys are defined, people may record them differently.

Drafted with Claude Code. Shortened by Levi Waldron with Claude Code.
