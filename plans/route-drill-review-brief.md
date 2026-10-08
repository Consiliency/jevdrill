# ROUTE drill-down replan review

Review the plan for implementation readiness against its roadmap. Use local read
tools to open the paths below. Do not implement or modify files. Do not read
secrets, private research, raw provider transcripts or unrelated dirty changes.

Primary artifact: plans/phase-plan-v1-ROUTE.md
Requirements: specs/phase-plans-v1.md (ROUTE plus context and gates)
Behavior map: docs/drill-roadmap-map.md
Original intent: docs/jevdrill-spec.md section 11

Inspect implementation where relevant:
- src/jevdrill/application.py (route and _prepare)
- src/jevdrill/catalog.py
- src/jevdrill/integrations/jev.py
- src/jevdrill/storage.py and src/jevdrill/cli.py
- baml_src/contracts.baml and baml_src/jev.baml
- docs/vocabulary.yaml and docs/route-interfaces.md
- scripts/verify_route_phase.py and tests/verification/test_route_phase.py

The existing application is a supplied-candidate configuration selector.
The missing product behavior is progressive guidance discovery, followed by
harness-owned decomposition and later independent task routing. This plan
implements ROUTE only; real host integration and empirical quality evaluation
remain later gates. BAML response shape is not a suitability guarantee.

Review specifically:
1. Are the question/state/branch/stop semantics implementable and useful?
2. Do new public contracts preserve v1 and provide sufficient linkage?
3. Are cumulative budgets, crash recovery, deletion, replay and privacy sound?
4. Does the five-second existing deadline remain honest?
5. Are lane ownership and tests complete without rebuilding unrelated code?
6. Can the acceptance pass with discovery absent or always-admit judgments?

Each blocking finding must cite an EC, declared contract or existing invariant,
name the concrete failure, and propose a bounded repair. Distinguish suggestions.
Use your assigned independent lens. End AGREE, PARTIALLY AGREE, or DISAGREE.
President: adjudicate findings and identify the changes needed for readiness.

Review loop cap: three rounds. Collect all findings before editing. Re-review
dissenting seats on the delta; prior AGREE verdicts may be carried with provenance.
Do not waive unresolved blockers or claim product completion from plan review.
