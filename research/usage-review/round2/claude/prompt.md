Review the bounded observed-Codex-usage implementation PLAN before code is written. This is a manual advisory review, not a governed implementation gate. User authorizes local subscription review and full tool permissions. Use local Read/search/shell tools to inspect the referenced files; do not just assess this pointer prompt. Roots: JEV=/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux; companion=/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port. Primary artifact: /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-usage-reporting-20261001-1610.md. Read its six acceptance criteria and frozen behavior, then inspect relevant existing source and pinned upstream copies. Source versions and privacy/unknown semantics matter. Review current working bytes, not only committed HEAD; preserve inherited modifications.
Do not implement changes, run builds/tests/providers, access credentials or edit source. Only write your canonical verdict file when instructed. Do not claim tests passed. Verify behavior by source inspection. Scope: Linux Codex exec 0.159.2, stdout cumulative usage, LaunchResult->adapter->durable queue->installed JEV; input accounting, pricing, Windows and policy remain follow-ups. Challenging a published invariant is valid; unrelated new goals are suggestions.
Report concrete actionable findings with IDs, severity, exact file/line or plan section, and which acceptance criterion or existing invariant is broken. Distinguish blockers from suggestions; state the smallest repair. Mention inspected paths and unverified assumptions. End with exactly AGREE, PARTIALLY AGREE, or DISAGREE. Three review rounds maximum, all seats finish before fixes, dissenters re-review a bound delta. Your lens will be supplied separately.

Re-review the corrected current plan against your previous findings. Read /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/usage-review/reconciliation.md, /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/usage-review/round2/delta.diff, and /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/usage-review/round1/claude/verdict.md. Prior AGREE seats are carried; resolve old concerns and identify remaining blockers.
 This is a focused delta review. Start with your prior verdict, the president ruling at /mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/usage-review/round1/president/ruling-2.md, reconciliation, and the bound delta. Runtime source bytes are unchanged; inspect only source needed to check the proposed remedies. Do not repeat the full original audit. Optional deferred suggestions are not blockers unless tied to an existing invariant or acceptance criterion.

Lens: correctness. Read relevant sections with targeted searches; you need not load entire large source files.
Open the local referenced files with tools; they are the review inputs.

## Referenced context files (BY REFERENCE — contents NOT inlined)

The files below are provided BY REFERENCE ONLY: their raw contents are intentionally NOT included anywhere in this bundle or prompt. When you need detail, OPEN each file yourself with your own local tools (your Read / file / PDF tooling) at the path shown. Do not assume the contents are pasted here, and do not infer, guess, or fabricate unavailable contents.

- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/plans/detailed-usage-reporting-20261001-1610.md"
  bytes: 23970
  sha256: e77c918213dc4a0f60e4c2f13290ba5cf8971330aee9bbd1dc256a62d313cdd4
  mime_untrusted_hint: text/markdown
  extension_untrusted_hint: md
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/runtime-accounting/investigation-20261001.md"
  bytes: 12397
  sha256: c451f4e51a45eafcb1cba7192bda6e5ec01c699c0fea776e753ed35f38d559a6
  mime_untrusted_hint: text/markdown
  extension_untrusted_hint: md
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/runtime-accounting/observations-20261001.json"
  bytes: 2630
  sha256: c954147c17c82c1781b6dd14589f6df25f10366fd6e1f827463d965f872cc8f9
  mime_untrusted_hint: application/json
  extension_untrusted_hint: json
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/baml_src/contracts.baml"
  bytes: 22155
  sha256: 444203c56f5273ac22f0f7cea5bbadba214aebddf961e4d7ab7e25360bb83b41
  mime_untrusted_hint: application/octet-stream
  extension_untrusted_hint: baml
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/schemas/ReportRequest.json"
  bytes: 12278
  sha256: 3958d5acb8819f53a743f3f98787e53b84541aeebdc76f3a756058f95a06ad71
  mime_untrusted_hint: application/json
  extension_untrusted_hint: json
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/application.py"
  bytes: 31533
  sha256: 31a4213ca08dde029b5438405af371d1449525335fc19acfa2ef9878221df17d
  mime_untrusted_hint: text/x-python
  extension_untrusted_hint: py
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/src/jevdrill/storage.py"
  bytes: 61520
  sha256: 5cf0f79c8d40604de16af6c2ce1ecaab4ef7aed022c45d14dd7f6980e54b59ba
  mime_untrusted_hint: text/x-python
  extension_untrusted_hint: py
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/docs/host-interfaces.md"
  bytes: 6514
  sha256: 06f54dbc6cb0b9b800c24192ab10ec70f4a1b57ed6be452a7241517f642b145f
  mime_untrusted_hint: text/markdown
  extension_untrusted_hint: md
- path: "/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port/phase-loop-runtime/src/phase_loop_runtime/launcher.py"
  bytes: 192211
  sha256: 351e666ffe963bab7e3e89e241d3973def269a62dccdd2628119909fe34025a5
  mime_untrusted_hint: text/x-python
  extension_untrusted_hint: py
- path: "/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port/phase-loop-runtime/src/phase_loop_runtime/jevdrill_adapter.py"
  bytes: 29765
  sha256: 401b0c72c4b40b276b3e4ad69ec78c1f6ea6ad3ff7e6aab069c4676692517ede
  mime_untrusted_hint: text/x-python
  extension_untrusted_hint: py
- path: "/mnt/workspace/worktrees/viperjuice/agent-harness-windows-port/phase-loop-runtime/src/phase_loop_runtime/jevdrill_queue.py"
  bytes: 10317
  sha256: 3e8ca1508681266c5cf5919d4e91681acc4f1c8102a5d490b4dc5a947b635000
  mime_untrusted_hint: text/x-python
  extension_untrusted_hint: py
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/PLAN-usage-reporting-20261001-1610/exec-events.rs"
  bytes: 27168
  sha256: bc296541b385f9b4ca2c28cc638e25a8d6b1332b2cd67f5a03eaa97a3d612b19
  mime_untrusted_hint: application/rls-services+xml
  extension_untrusted_hint: rs
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/.phase-loop/runs/PLAN-usage-reporting-20261001-1610/exec-contract.rs"
  bytes: 10713
  sha256: dafa872d7e86a099e56e28a329dcb9c03db90ed768c3b88cca8c91d46dc1d0e5
  mime_untrusted_hint: application/rls-services+xml
  extension_untrusted_hint: rs
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/usage-review/reconciliation.md"
  bytes: 6816
  sha256: 34bccd20fec156861d45b8d190479434906bdfeb093d20ac3c4f8f0030bc97c3
  mime_untrusted_hint: text/markdown
  extension_untrusted_hint: md
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/usage-review/round2/delta.diff"
  bytes: 17185
  sha256: b4892fdb7150e87768a5e99ed1fb23523a5e1f011fa5c0bfd68d6420c88a8744
  mime_untrusted_hint: text/x-diff
  extension_untrusted_hint: diff
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/usage-review/round2/delta-binding.json"
  bytes: 392
  sha256: 482d143f7cc386a9deeec26d86ceec31a4077d37daabb1f2b2d9bcbe0d8207ca
  mime_untrusted_hint: application/json
  extension_untrusted_hint: json
- path: "/mnt/workspace/worktrees/viperjuice/jevdrill-codex-v0-linux/research/usage-review/upstream/exec-lib.rs"
  bytes: 86172
  sha256: 48be5b8d89283f1fe338682d634ea3e73847ef1eb7c7626ca801002980527de1
  mime_untrusted_hint: application/rls-services+xml
  extension_untrusted_hint: rs
