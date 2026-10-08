The four confirmation repairs hold and stay frozen. Route-v2 still accepts only `selected_guidance` and `no_optional_guidance`, including on cache, retry, and commit, and it rejects every other variant before `_prepare`. Queues stay FIFO by monotonic enqueue sequence, with same-batch siblings in stable ID order, alternation when both queues have work starting at preferred, and excess frontier options requeued at the tail as cursors. Nothing re-sorts by last-service age. Stricter limits follow the inherited `HardConstraints` field by field: a restricted `allowed_providers` list may shrink only to a nonempty subset, because empty means unrestricted. Recovery of a nonterminal attempt dispatches no provider work and does not refill that attempt’s allowance when a new five-second response deadline starts. EC-ROUTE-1–7 and both interface gates remain mandatory. The pending-review banner is historical. The existing selector stays in place: v2 filters `guidance_options`, rebinds guidance, and reuses `_prepare`’s 0/1/2 combination loop and `select_plan`.

Required repairs:

1. **EC-ROUTE-1.** Make recovery’s terminal write atomic. Same-key recovery commits interrupted failure, or a supported partial result, before the response is returned. A late observation may become that result only while the attempt is still nonterminal, inside one storage transaction that also rechecks the tombstone. After a terminal record, a late observation is audit-only: it must not replace the result, restore a route allowlist, or drop the reservation. The new no-redispatch rule otherwise races an in-flight call.

2. **EC-ROUTE-1 / EC-ROUTE-6.** Give each idempotency key its own immutable ledger. The parent row keyed by project, workspace, and `work_objective_id` may own many attempts, but a new key gets a fresh limit intersection. It must not clear, share, or inherit another attempt’s remaining calls, tokens, or spend. Same-key recovery must not raise the original allowance. A shared parent counter plus retained reservations would leave a crashed attempt unable to continue and unable to restart.

Suggestions only:

- Persist discovery refs without `task_id` (`resource_id`, revision, hash, role, admission, authority). Source `GuidanceRevision.task_id` is required, and `_prepare` rejects a task mismatch. Bind `task_id` only when rebuilding rows for the concrete route task.
- Pass `ObserveDiscoveryOption-v1` as its own parsed policy. `JevAdapter.__init__` accepts only `JudgmentPolicy` with `function_revision` `JudgeCandidate-v1`.
- Count one provider call per option-level Bool. The pinned client flattens a class into one question per leaf, which would under-count a batched class.
- Leave required v1 `RouteInputs` and decision fields unchanged, and carry discovery termination and uncertainty on the v2 linkage. The decision schema is not in this bundle.
- Keep `baml_src/ns_typesafe_patch/**` out of SL-0 edits. The lane glob covers the patch the preamble forbids replacing.

`storage.py` transaction mechanics, the `select_plan` body, and the code treating empty `allowed_providers` as unrestricted are not in the excerpt. The plan’s field-wise rule is the freeze being confirmed. No code was executed. Implementation artifacts are still future work.

PARTIALLY AGREE
