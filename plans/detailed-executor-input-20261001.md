# Detailed plan: resolved executor input accounting

## Task

Continue the authorized roadmap after USAGE-v0. Record the resolved Linux
Codex payload separately from assembled context and routing estimates. Reuse
the assigned dirty `codex/v0-linux` and `codex/jevdrill-windows-port` worktrees;
their prior changes are required inputs. Execution and closeout are local only.
No provider calls, budget resets, publication, commits, merges or gate closures.

## Research summary

`PromptBundle.render_prompt()` and `render_context()` can differ. Codex converts
the final prompt argument to stdin at launch and materializes the output schema
at that point. `context_sha256` describes assembled context, not necessarily
the prompt submitted. Routing counts a JSON representation of supplied task
material, which omits executor instructions, history, tools and subsequent reads.
Current usage counters cannot establish complete provider context or charges.

## Changes

1. In companion `phase-loop-runtime/src/phase_loop_runtime/launcher.py`, add an
   optional host-local `executor_input_manifest` on LaunchResult. Capture only
   through a private adapter opt-in, live Linux Codex fresh `exec`, and a final
   prompt that can be matched exactly to the resolved delivery path. The manifest
   identifies method `codex_executor_input_v1`, UTF-8 prompt bytes/digest and,
   if present, bytes/digest of the schema materialized by this launch. Existing
   context digest semantics stay intact. Persist metadata through event_metadata
   and preserve it through result enrichment. Never record raw text or schema.
   The manifest describes prepared submission, not confirmed provider receipt;
   provider context, later reads and tokenizer overhead remain unknown. Unsupported
   commands, resume/fork, dry runs and ordinary launches get no manifest. Do not
   read an arbitrary schema path from a caller-supplied command. Missing schema
   observations remain unknown. Recording must not change launch or usage behavior.
2. In companion `phase-loop-runtime/src/phase_loop_runtime/jevdrill_adapter.py`,
   request the input capture alongside existing private usage capture. Add
   `phase-loop-runtime/tests/test_jevdrill_input.py` exercising real synthetic
   child stdin/schema, Unicode, differing context, persistence, result enrichment,
   unsupported paths and deadline exits. Update `docs/jevdrill-integration.md`.
3. In JEV `src/jevdrill/routing.py`, make cost assumptions explicit about supplied
   routing material versus resolved executor payload. In `src/jevdrill/application.py`,
   version the cross-request cache key for these semantics; immutable idempotent
   replay stays intact. Update `tests/application/test_application.py` with cache
   and scope regression controls. Update `docs/route-interfaces.md`,
   `docs/host-interfaces.md`, `docs/vocabulary.yaml` and regenerate
   `docs/vocabulary.md`. Register the host method as an external identifier.
   Do not add a second wire contract or change BAML schemas.
4. Add `scripts/verify_executor_input.py` to refresh frozen dependencies, build
   and install a wheel in an isolated environment, run synthetic companion
   input/usage/adapter/queue and launcher controls, lint/vocabulary checks and the
   full JEV suite. Emit `evidence/INPUT-v0/verification.json` with source bindings,
   check outcomes and explicit no-provider/no-gate scope. Use new private run
   directories under `.phase-loop/runs/INPUT-v0-20261001`; preserve USAGE evidence.
   The runner may read source/test/schema/contract/docs globs and lockfiles in
   both assigned trees and its own output; no historical raw evidence is needed.

Workflow metadata also owns this plan, `plans/manifest.json`, INPUT-v0 run
metadata, repo-local detailed-execution handoff and skill reflection. Starting
statuses/digests are retained in the INPUT-v0 run directory. Preserve all other
dirty paths and staged changes. Raw cost reconstruction is the next bounded task.

## Verification

- Run skill Python preflight in both projects; verify pinned compiler 0.20.1.
- Run focused input and application regressions first.
- Run `BAML_CLI=/mnt/workspace/worktrees/viperjuice/.baml-v1-0201-toolchain/bin/baml-cli JEVDRILL_AGENT_HARNESS_ROOT=/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port .venv/bin/python scripts/verify_executor_input.py`.
- Compare final dirty paths/digests against starting metadata, classify every
  path and require no changes outside declared ownership. Record closeout,
  documentation delta and reflection. No publication from these inherited trees.

## Acceptance criteria

- [ ] Actual resolved prompt and owned schema have deterministic separate byte
  counts/digests, without changing the assembled-context digest.
- [ ] Manifest scope distinguishes prepared submission from provider receipt,
  token counts, complete context and enforceable execution ceilings.
- [ ] Unsupported/dry/ordinary paths do not acquire false observations; final
  identity checks, timing, usage, cleanup and lifecycle continue to work.
- [ ] Host metadata persists only counts/digests; existing BAML wire remains
  authoritative and unchanged.
- [ ] Routing estimates state their input scope, fresh decisions avoid stale
  cache semantics, and immutable replay is preserved.
- [ ] Scoped verification passes with source-bound synthetic evidence, a built
  installed wheel, full JEV suite and no provider execution or phase-gate claims.
