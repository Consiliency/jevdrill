# Drill-down behavior and roadmap ownership

## What the product must do

JEV Drill helps a harness decide which guidance to use and how to execute the
individual tasks that follow. These are two related decisions, with the harness
in between. A skill is not necessarily one task or one model assignment.

1. Receive the objective, relevant context, available resources and constraints.
2. Start with compact catalog descriptions. Select a useful question and its
   allowed choices, obtain a typed judgment, and update the search state.
3. Narrow through domain, specialty, task and candidate descriptions. Skip levels
   when an exact match supports it; retain alternatives when classification is
   uncertain. Stop within explicit resource limits.
4. Retrieve selected, admitted guidance revisions and return usable instructions
   with evidence, uncertainty and constraints. No optional guidance is valid.
5. Let the executive harness decompose the work and decide what to execute.
6. For each concrete task, select a feasible configuration: model, native effort,
   relevant guidance and execution route. Tasks from one skill can differ.
7. Collect actual outcomes and analyze comparable observations. Reuse that
   evidence in later decisions; run authorized comparisons where useful.

Drill's code owns question selection, allowed answers, state transitions,
branching, budget accounting and stopping. JEV supplies typed judgments through
BAML. Type validation proves the response shape; independent checks must establish
whether a judgment or resulting selection is useful.

For example, a selected implementation workflow might lead the harness to request
separate code-editing, review and documentation tasks. Their constraints can admit
different configurations. Discovery must not prematurely assign one model to all
three, and the harness remains free to reject a recommendation.

## Existing implementation versus required behavior

Paths below name current implementation surfaces, not proposed new module names.
The roadmap ECs are authoritative acceptance requirements.

| Behavior | What exists | Remaining work and owning criteria | A check that must catch a broken implementation |
| --- | --- | --- | --- |
| Strict interfaces and searchable vocabulary | BAML contracts, strict parsing, portable schemas and YAML vocabulary | Add discovery contracts and canonical identifiers under EC-ROUTE-5, following EC-CONTRACT-1–3 compatibility rules | Unknown choices, malformed states and cross-language validation disagreements are rejected |
| Catalog admission and retrieval | `src/jevdrill/catalog.py` preserves revisions and retrieves admitted resources; `narrow` ranks supplied facets | Make narrowing part of application-owned progressive navigation: EC-ROUTE-6 | A useful cross-domain candidate remains reachable after an ambiguous first classification |
| Question selection and changing search state | Current JEV integration provides candidate suitability judgments; caller supplies catalog query facets | Implement bounded rounds, frontier updates, question choices, stopping and compact context: EC-ROUTE-5–6 | A multi-round case fails if the application merely filters once or repeatedly asks the same question |
| Guidance and configuration construction | `application._prepare` combines zero, one or two optional resources with required guidance, checks feasibility and retrieves instructions | Feed discovery results into this existing selector and prove per-task behavior: EC-ROUTE-7 | Reject incompatible guidance; permit no optional guidance and different configurations for tasks derived from one skill |
| Final ranking and decision replay | Existing routing checks constraints, cost, evidence, defaults and stable ties; recorded judgments support replay | Extend persistence/replay to discovery questions, transitions and termination: EC-ROUTE-5–7 | Replaying a trace makes no provider call; stale or differently authorized state cannot reuse a result |
| Harness handoff | CLI/companion routing, reporting, guidance lifetime and substitutions exist | Connect objective discovery to harness decomposition and independent task requests: EC-HOST-4 | Installed acceptance fails if it bypasses discovery with preselected guidance or forces one model for the entire skill |
| Feedback and learning | Observation groups, analysis, retention and candidate-ordering policy machinery exist | Preserve discovery-to-task lineage and retrieve appropriately scoped evidence: EC-LEARN-5 | A task result cannot become an unsupported claim about every task in a skill or domain |
| Decision quality | Recorded routing comparisons and executor evaluations exist | Evaluate discovery and routing discrimination directly: EC-EXPERIMENT-4 | Known unsuitable controls expose an always-admit judgment; executor pass rates alone cannot pass the gate |
| Complete product acceptance | Internal Linux routing/reporting checkpoint exists; release preparation is separate | Installed complete flow and amended criterion coverage: EC-PREPARE-4 | A release with only supplied-candidate selection fails acceptance |

## Why the earlier roadmap was insufficient

[The product draft §11](jevdrill-spec.md#11-jev-drill-down-and-context-management)
already specified progressive navigation, compact state, alternative paths and
bounded rounds. EC-ROUTE-2 required catalog and guidance handling; EC-ROUTE-3
required deterministic selection and recorded judgments. Neither explicitly
required the application to choose the next question and advance the search.

EC-CONTRACT-4 required a draft-requirement coverage sweep and owning criteria whose
text verified each requirement. The target criteria were still too broad. A
requirement mapped to an EC is not sufficient evidence when its distinctive
behavior can be absent while the EC's tests pass. Later experiments measured
executor performance without establishing the missing discovery behavior.

The correction adds behavior-specific criteria to the existing phases rather
than declaring the infrastructure work wasted or starting a competing roadmap.
Earlier PASS reports retain their historical meaning for their recorded source
and criteria. They do not prove the added requirements.

## Implementation order and design details to freeze

The revised **ROUTE plan** uses the existing CONTRACT foundation and has passed
the owner-requested self-review after panel reconciliation. Implement its five
serial lanes first. It freezes these interfaces and test obligations:

- Discovery request/result versus per-task route request, including their links.
- Navigation state, allowed question types and option identities, transition
  rules, branch retention, exact-match shortcuts and terminal outcomes.
- Round, width, candidate, token, elapsed-time and cost accounting within the
  existing request deadline; conservative packing when exact tokens are unknown.
- Admission and retrieval timing, required guidance preservation, and conditions
  for fallback or an explicit inability to recommend.
- Cache/replay identity covering context, policy, taxonomy, resource revisions,
  inventory freshness and authorization; record omitted or unavailable evidence.
- Canonical vocabulary entries and module ownership before choosing new public
  identifiers. Keep YAML as vocabulary authority and BAML as contract authority.
- Fixtures that invoke public application/CLI paths and falsify each new EC,
  with separate deterministic software checks and empirical quality evaluation.

Then revise HOST, LEARN, EXPERIMENT and PREPARE plans in dependency order. Existing
plans are historical implementation inputs until amended; simply updating their
roadmap hashes would hide missing work. Reuse existing selection, storage and
analysis components where their behavior fits.

The amendment does not authorize additional paid calls, expose the release
holdout, reset spending ledgers, promote a policy or expand policy edits beyond
approved candidate ordering. Review history and its limits are recorded in
`plans/phase-plan-v1-ROUTE_reviews.md`; no ratification is claimed.
