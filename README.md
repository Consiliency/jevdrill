# JEV Drill

Governed comparisons and recorded policy evaluation are available through the installed experiment commands with explicit trusted adapter configuration. Defaults grant no execution or promotion authority. See [EXPERIMENT interfaces](docs/experiment-interfaces.md), [readiness](docs/experiment-readiness.md) and the [new development study proposal](evidence/EXPERIMENT/study-proposal.json).

JEV Drill provides progressive guidance discovery, independent task routing and durable local reporting/replay. Discovery returns admitted guidance and uncertainty; the harness owns decomposition and execution. See [ROUTE readiness](docs/route-readiness.md), [HOST readiness](docs/host-readiness.md), [host interfaces](docs/host-interfaces.md) and the [roadmap](specs/phase-plans-v1.md). The explicit agent-harness companion connects discovery to host-produced task lanes and existing launch constructors. Later phases require replanning against these linked observations.

For local development, install CPython 3.13 and run `uv sync --locked` and `npm ci`. Set `BAML_CLI` to the verified BAML 0.20.1 compiler, then run `uv run python scripts/verify_contract_phase.py`. Missing platform evidence keeps the phase open. [Toolchain details](docs/toolchain.md) and [contract rules](docs/contracts.md) describe the generated package and strict validation boundary.

Use `jevdrill discover` with `DiscoveryInputs`, then pass its discovery identity and trace digest with each task's `DiscoveryRouteInputs` to `jevdrill route`. JSON travels through stdin/stdout. `inspect-discovery --discovery-id ID --scope JSON --replay` replays recorded transitions without a provider call; `delete-discovery --work-objective-id ID --scope JSON` permanently tombstones the objective. Legacy route-v1 inputs remain supported. Run `uv run python scripts/verify_route_phase.py --local-only` for local evidence; the reducer requires matching native Linux/macOS/Windows reports for all seven criteria.

`jevdrill notices` reads a strict NoticeRequest from stdin and returns pending project/workspace notices without acknowledging them. Run `uv run python scripts/verify_host_phase.py --agent-harness PATH --local-only` with the separately installed companion and pinned compiler; full acceptance requires all three native receipts. Passing synthetic checks establish software behavior. Model quality, guidance effectiveness and performance gains remain insufficient evidence.

## Existing research

`jevdrill analyze`, `maintenance` and `recovery` provide consent-scoped observational
evidence, bounded retention and authenticated portable recovery. See
[LEARN interfaces](docs/learn-interfaces.md) and [LEARN readiness](docs/learn-readiness.md).
Local and user-wide learning require explicit consent. Scheduler configurations
are generated for inspection; OS keys and scheduler installation remain host
setup actions. Observations supply no causal benefit or policy promotion authority.

Source discovery, versioned ingestion, model triage, independent domain review and paired evaluation for a prospective Jev advisor router. Research began on 2026-09-26. GPT-6 Sol performs the main reviews; a matched GPT-6 Luna experiment is retained separately.

## Start here

- [JEV Drill product specification](docs/jevdrill-spec.md): plain-English draft covering joint model/effort/guidance routing, project context, capability checks, structured handoff, local storage, telemetry, experiments, and later learning.
- [Combined sweep report](research/collection-expansion/FINAL-REPORT.md): 9,104 pinned candidate paths, with 8,887 completed Sol reviews, 205 documented exclusions and 12 unresolved output-evidence failures; no candidate is validated. The [original sweep report](research/REPORT.md) preserves the first corpus's comparison and evaluation results.
- [Browse the reviewed catalog](research/published/CATALOG.md): domain counts, research shortlists, direct source links and explicit gaps. [All candidate records](research/published/ranked-catalog.json) preserve decisions, exclusions, duplicates and evidence; [snapshot statistics](research/published/summary.json) show completion status.
- [Initial discovery catalog](research/CATALOG.md) and [original records](research/catalog.json): 88 skill records, 35 individual prompts, 37 collections and three references, with source URLs, curation evidence, validation limits and licensing notes.
- [Discovery inventory](research/discovery-inventory.json): the original 2,296 candidate paths across 14 repositories—1,622 SKILL.md paths and 674 prompt/instruction paths. [Pinned ingestion manifest](research/ingestion/manifest.json) and content-addressed text cache retain every source, including duplicates. All original bodies were fetched and verified against their Git blob hashes. Broader path matching found another 59 paths, recorded separately in [the refresh snapshot](research/ingestion/refresh-check/manifest.json).
- [Review status](research/review/summary.json), [ranked model triage](research/review/ranked-catalog.json) and [review procedure](research/review/README.md). Ranking is research priority, not measured advisor quality. Unresolved output-validation failures remain explicit.
- [Independent domain review](research/domain-review/consolidated-summary.json) and [paired evaluation results](research/evaluation/pilot-summary.json). No skill has earned validated admission. The four paired fixtures showed no incremental benefit: both arms passed 12 of 12 checks.
- [Sol/Luna comparison](research/review/model-comparison.json): supported evidence on 20/20 matched Sol reviews versus 12/20 Luna reviews. This small experiment supports keeping Sol for evidence-bearing triage; it is not a general model benchmark.
- [Benchmark source investigation](research/benchmark-audit/SUMMARY.md), [published-evidence audit](research/benchmark-audit/published-evidence/REPORT.md), [taxonomy crosswalk](research/benchmark-audit/published-evidence/taxonomy-crosswalk.md), and [collection plan](research/benchmark-collection-plan.md): 1,619 published observations and 28 task mappings are recorded. These are source observations, not benchmark executions or skill admissions; no exact model/version/effort comparison is eligible yet.
- [Expanded taxonomy](research/taxonomy-expanded.json): 32 domains, 258 specialties and independent task/constraint facets. [Evidence-backed additions](research/taxonomy-changes.json) extend the original 233 specialties without rewriting the historical review taxonomy. Coverage of a root does not establish coverage of every specialty.
- [Progressive routing packs](research/router/index.json) and [packing report](research/router/packing-report.json): domains, specialties, candidate pages and pinned detail pointers. Each routing pack is limited to 24,000 UTF-8 bytes; actual Jev token count is unmeasured. These are prospective retrieval packs, not a validated skill/model router.
- [Jev constraints and routing handoff](research/routing-notes.md).
- [Coverage counts and record IDs](research/catalog-summary.json).
- [Combined collection inventory](research/collection-expansion/full-manifest.json), [source registry](research/source-registry.json), and [refresh operations](research/OPERATIONS.md): stable identities, URL aliases, source versions, change checks and review-cache reuse. The registry also records benchmark evidence URLs, which are not skill bodies.

## How to interpret the records

`skill` identifies a skill artifact or explicitly marked skill lead; `prompt` identifies a plain reusable prompt. Collections are discovery hubs, not individual advisors. Source inspection depth varies and is recorded. One skill lead was reviewed at README level; the Hermes collection is a publisher-cited lead with direct access limitations. Ten prompts.chat rows share a CSV URL and are distinguished by `artifact_locator`.

Trust labels describe provenance. Publisher curation does not establish professional correctness; community curation does not establish independent review. The single `research_evaluated` record is TypeSafe's own skill-selection experiment, not a validation of our catalog. No discovered skill was installed, executed, or professionally certified. Unknown licensing remains unknown; repository licenses can have artifact-specific exceptions.

The initial discovery catalog normalizes `source_observations` to objects and maps original domain labels to `taxonomy_domain_ids`. Original researcher files preserve their source notes. Its historical observations do not claim inspection of the later pinned revisions. The ingestion/review pipeline separately records exact source hashes, quotations, model settings and decision provenance. Mapping remains provisional; interdisciplinary records can appear in multiple categories.

## Tools and remaining work

PMCP Firecrawl, Context7, web search, local inspection and public GitHub retrieval were used. The local BrightData launcher was repaired to select its managed Node release, and a live BrightData search succeeded. Startup diagnostics are tracked in [Consiliency/pmcp#302](https://github.com/Consiliency/pmcp/issues/302). No executable or matching gateway capability named `def` was found; no local `firecrawld` executable was found, although Firecrawl through PMCP worked. Historical redacted access notes are in [professional research notes](research/professional-domains-notes.md).

Thin areas include crop-specific agronomy, emergency response, jurisdiction-specific professional practice, neutral religious advising, clinical psychology, and expert sports advice. Some broad domains currently rely on modest prompts or collection leads. See [technical notes](research/technical-science-notes.md), [humanities notes](research/humanities-creative-notes.md), and [gap sweep](research/gap-sweep-notes.md).

Remaining admission work includes inspecting referenced support files, resolving artifact-specific reuse rights, harder repeated task evaluations, and domain-professional review. The benchmark directory still needs comparable model/version/effort observations before it can support a combined model-effort router. Optimization or prompt distillation should follow task-level evaluation rather than replace it.
