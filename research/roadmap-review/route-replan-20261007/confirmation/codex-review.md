The plan is ready for implementation. I find no remaining blocking defect in the supplied material and require no additional plan repairs.

The reconciliation closes the identified gaps:

- **EC-ROUTE-7:** Route-v2 admits only the two successful discovery variants, including cache/retry paths, while retaining uncertainty and testing successful empty guidance.
- **EC-ROUTE-6:** FIFO insertion, alternating queues and requeued cursors define implementable traversal with bounded opportunities to recover an alternate branch.
- **EC-ROUTE-3/7:** The constraint ordering respects the existing empty-`allowed_providers` meaning and explicitly rejects weakened or incomparable constraints.
- **EC-ROUTE-1/3:** Recovery dispatches no additional provider work; durable reservations survive interruption without renewing the attempt’s allowance.

The selector integration matches the supplied `_prepare` invariants: task-scoped guidance, retrieved-content recounting and zero/one/two-resource combinations. Separate discovery contracts preserve existing operation literals and `JudgeCandidate-v1`. Rejecting unsupported hard output ceilings also matches the pinned client’s exposed capabilities; planning reservations do not claim enforcement.

Durability and privacy obligations remain substantive: transactional linkage/deletion checks, permanent objective tombstones, sanitized provider allowlists, metadata replay without provider calls, and explicit replay unavailability when retained facts are insufficient.

This clears **implementation readiness only**. Implementation and native verification evidence are not supplied. All seven ECs, current-source negative controls, Python/Node compatibility and the Linux/macOS/Windows matrix remain required for gate closure. Historical pending-review metadata is not a product defect.

AGREE