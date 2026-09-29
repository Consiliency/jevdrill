# JEV Drill: current implementation, reuse, and remaining questions

Status: CONTRACT implementation in progress; not a canonical adoption artifact.
Companions: [accepted design input](jevdrill-design-input.md) and [implementation proposal](jevdrill-implementation-proposal.md).

## Inspection boundary

Inspected the top-level source/test inventory and relevant implementations in `scripts/catalog_ingest.py`, `catalog_sources.py`, `catalog_review.py`, `catalog_publish.py`, `catalog_router.py`, and `catalog_evaluate.py`. Inspected targeted tests and ran all existing catalog unit tests. This is a bounded reuse assessment, not a security audit or exhaustive review of vendored research sources.

The original inspection found research scripts, tests and a product draft without Git or an application package. The user subsequently authorized public Consiliency/jevdrill; local main and origin now exist. CONTRACT has added BAML contracts, strict Python/Node validation, vocabulary/import checks, evaluation helpers and offline JEV tests. Cross-platform verification remains pending. No routing application or canonical adoption exists yet. See `evidence/CONTRACT/verification.json` for current verification status.

## Existing assets and reuse recommendations

| Asset | Inspected current behavior | Recommended disposition | Gap before product use |
|---|---|---|---|
| `scripts/catalog_ingest.py`: `identity`, `cache_content`, `integrate`, `reusable_refresh` | Stable source-path identities, content verification, revision history, failure/change distinction, verified unchanged refresh | Adapt pure identity/change logic and tests into catalog/storage contracts | Source occurrence is not automatically canonical resource identity; add schema/migration contracts and cross-platform persistence |
| `scripts/catalog_ingest.py`: `atomic_write`, `output_lock` | Atomic replacement/fsync and Unix `fcntl` lock | Reuse behavior requirements, not an unreviewed portability claim | Windows support and storage transaction design; directory fsync assumptions |
| `scripts/catalog_sources.py`: `source_key`, `reconcile`, `scan` | URL aliases, conditional requests, history, fetch-error distinction | Adapt source tracking and fixture tests | Network boundary validation, source-provider expansion, explicit snapshot schema |
| `scripts/catalog_review.py`: `cache_key`, `validate_response` | Cache depends on content/metadata/rubric/model; validates schema, IDs, hashes, quoted evidence | Preserve provenance and evidence-validation ideas | Research-specific Codex model/effort/auth path and Unix locks are not a general product adapter |
| `scripts/catalog_publish.py`: `matches`, `apply_domain_expansion`, `consolidate` | Separates stale evidence and current mappings; preserves research distinctions | Import records with explicit lineage and admission translation | No automatic translation from research priority to production admission |
| `scripts/catalog_router.py`: `paginate`, `build`, `lookup` | Deterministic 24,000-byte packs, multi-domain placement, hashed detail references and checked retrieval | Reuse navigation/packing and hash-checking ideas after adapting interfaces | No JEV calls, no actual token compliance, no model/effort joint selection; research eligibility includes `needs_evaluation` |
| `scripts/catalog_evaluate.py`: `prompt_for`, `score`, `compare` | Paired exact-answer evaluation, explicit abstention and opt-in numeric equivalence; success does not establish admission | Reuse small scorer fixtures/pairing principles where suitable | Not an implementation/review/documentation evaluator suite; runner is fixed-model, CLI-specific, sequential, and not the new container experiment service |
| `research/benchmark-audit/published-evidence/` | Versioned published observations with recorded comparability limits | Supporting evidence import | Unknown settings and mismatched protocols must stay unknown; do not infer model-only rankings |
| `research/taxonomy-expanded.json`, published catalog | Existing taxonomy and unvalidated reviewed material | Seed catalog with source/version references | Select initial admitted/enabled resources and verify supporting files/licenses |

Research pack eligibility is intentionally different from product automatic injection. Do not change the research pipeline's historical meaning to make it appear product-ready. Migrate through an explicit importer.

## Verification performed

The preflight helper warned that no virtual environment exists. Verified the available interpreter and dependency directly: Python 3.14.4, jsonschema 4.19.2. No dependencies were installed. This environment is evidence about current research tests, not the future supported Python-version decision.

Command:

```sh
python3 -m unittest discover -s tests -p 'test_catalog_*.py'
```

Result: 55 tests passed. These tests cover research helpers and mocked review paths. No live provider benchmark, product build, cross-platform test, or pipeline adoption was performed. A subsequent [BAML compatibility proof](../research/baml-proof/README.md) added isolated generation, roundtrip, schema-export, local mock and timeout checks, plus one authorized live JEV call. Generated contract defaults failed the intended strictness requirements; the proof records the required supplements.

## Conflicts with the original product draft

| Draft topic | Required synthesis change |
|---|---|
| “Configuration” and “state” | Apply JD-002's distinct vocabulary; do not globally replace external API names |
| First-release scope/stages | Map the expanded design to JD-046's three deliveries; JD-065 assigns immediate bakeoffs to stage 3 |
| Experiment ownership | Include both internal and harness-assisted execution under JEV Drill ownership |
| Quality/cost selection | Use quality sufficiency plus time constraint, then token cost; isolate optional discounts |
| Retention defaults | Local retention/analysis enabled, 30-day active period, seven-day archive prompt grace, automatic archival, one-year archive expiry, durable redacted measurements |
| Contracts | Five distinct status shapes, immutable plans, idempotency, durable decisions, shared event contract |
| Operational support | Linux/macOS/Windows, CLI JSON transport, maintenance scheduling, durable host queue |
| Learning | Separate evidence updates from policy promotion, preserve objectives and measurements for reassessment |
| Canonical docs | Preserve draft as input; adopt explicitly with source roles instead of treating every document as simultaneously authoritative |

No existing draft paragraphs were silently rewritten during consolidation.

## Fleet compatibility evidence

Agent-harness inspected local revision: `b9627d538faad872077472e3711a941198add5da`.

- `AGENTS.md`: pin inputs rather than future output commits; reference declared exit criteria without paraphrase.
- `phase-loop-skills/phase-roadmap-builder/references/roadmap-template.md`: prescribed headings in `specs/phase-plans-v<N>.md`, phase aliases, `EC-*` criteria and `IF-*` gates.
- `phase-loop-runtime/src/phase_loop_runtime/_contract_docs/phase-loop/spec-discovery-roots.md`: root `specs/` is intake/discovery; governed-pipeline owns adoption/mirrors.
- `roadmap_representation_check.py`: dependency consistency checks are described as advisory; do not claim this alone provides a blocking HTML/Markdown equivalence gate.

Governed-pipeline inspected GitHub main at revision `15f2d40ec6d985bee6dc5edce9d89782010e66dd`:

- [Adoption contract](https://github.com/Consiliency/governed-pipeline/blob/15f2d40ec6d985bee6dc5edce9d89782010e66dd/docs/canonical-spec-adoption.md): explicit adoption modes, archives, source roles and mirrors.
- [HTML contract](https://github.com/Consiliency/governed-pipeline/blob/15f2d40ec6d985bee6dc5edce9d89782010e66dd/docs/canonical-html-contract.md): HTML-first durable intent, stable anchors and metadata sidecars, JSON/event authority.
- [Machine contract](https://github.com/Consiliency/governed-pipeline/blob/15f2d40ec6d985bee6dc5edce9d89782010e66dd/specs/contracts/canonical-html-contract-v1.json): document families and source-role definitions.
- [Writer tests](https://github.com/Consiliency/governed-pipeline/blob/15f2d40ec6d985bee6dc5edce9d89782010e66dd/packages/pipeline-runtime/test/canonical-html-contract.test.mjs): writer compatibility, not a test run performed here.

The older adoption prose lists Markdown outputs; the HTML contract explicitly directs new canonical output to HTML. Verify the installed pipeline version and exported roadmap compatibility before adoption. No fake pipeline manifest or adopted role is generated by this source bundle.

## Remaining implementation blockers

Owners below are proposed responsibility assignments, not named people. “User” means a product/authority choice is needed. “Implementation” means inspect and propose concrete detail without asking the user to choose arbitrary low-level constants.

| ID | Affected stage and decisions | Owner | Unresolved point | Recommendation / next action |
|---|---|---|---|---|
| Q-01 | Stage 1; JD-008–JD-014, JD-036 | Integration implementation | Exact adapter sequence, cancellation, capability report and queue payloads | Actual launch, availability, capability and metric paths are mapped in implementation proposal section 4. Existing metrics lack token/cost measurements; complete the event contract and adapter proof |
| Q-02 (resolved) | Stage 1; JD-004, JD-064 | Architecture | Separate `evaluation`, `analysis`, and `experiments` modules accepted | Reflect ownership in the import graph and interfaces under Q-03/Q-04 |
| Q-03 | All; JD-008–JD-015, JD-081–JD-082 | Contract implementation | Complete BAML contracts, generated types/schemas, strict validation, ID construction, canonical idempotency payload, states, event order, replay/import corrections, schema migration | Isolated `baml-language-0.20.1` proof passes generation, five variant roundtrips, schema export, mocks and one live JEV call. Generated defaults ignore extra fields, coerce numbers and default nullable fields. Implement strict derived validation and resolve runtime import coupling before contract freeze; cross-language and cancellation checks remain pending |
| Q-04 | Stage 1; JD-007, JD-005 | Implementation | Supported Python range, package/build tool, type checker/linter and exact import graph | Inspect dependency compatibility; propose one toolchain and Windows/macOS/Linux CI matrix |
| Q-05 | Stages 1–2; JD-006, JD-052 | Implementation | Full vocabulary schema, deterministic code/prose lint scopes and pipeline registration | Seed YAML registry and generated glossary now exist, with registry consistency and stale-generation checks. Extend these to scoped usage linting before claiming full enforcement |
| Q-06 (default deadline resolved) | Stage 1; JD-019, JD-022, JD-025, JD-073 | Routing/inventory implementation + user for limits | Initial provider/model sources, effort maps, verification methods, deadline timer boundaries, routing rounds, branch/candidate limits, context packing, default plan | JD-073 sets a provisional five-second routing deadline. Validate operational limits against measured baseline; do not equate byte caps with token budgets |
| Q-07 | Stage 1; JD-016, JD-023–JD-024 | Costing implementation | Token estimation, rate versions/currency, cache/reasoning overlap, adjusted-cost formula, hard-cap enforcement across unknown output | Define estimates separately from enforceable token/spending ceilings; bind rate snapshot and report unknowns |
| Q-08 | Stage 1; JD-020–JD-021 | Catalog implementation + user for initial enablement | Initial resource set, import mapping, supporting bundles, conflict checks, admission/revocation | Select narrow initial resources and keep research `needs_evaluation` distinct from admitted |
| Q-09 | Stages 1–2; JD-011–JD-015, JD-044, JD-069 | Storage implementation | Tables/keys/indexes, transaction boundaries, contention policy, migrations, artifact paths, deletion/corrections/backup mechanisms | JD-069 defines evidence deletion and revalidation semantics; implement minimal deletion records, contribution tracking, and recomputation. Design schema and failure matrix before data writes; research helpers are not proven cross-platform |
| Q-10 (notifications, identity, sharing, encryption, and collection policy resolved) | Stages 1–2; JD-043–JD-045, JD-066–JD-071 | User + privacy implementation | Exclusion/redaction implementation, consent UI, archive format/key recovery, restore/backup deletion, default local experiment enablement | JD-066 establishes the local inbox; JD-067 establishes project/workspace identities; JD-068 scopes sharing; JD-069 defines evidence deletion; JD-070 requires encrypted archives; JD-071 scopes collection and exclusions. Resolve remaining boundaries and present concrete OS-local path and scheduler choices |
| Q-11 (timing, missing-context behavior, and resource priority resolved) | Stage 3; JD-032–JD-036, JD-046, JD-065, JD-072, JD-074 | Experiments implementation + user for authority defaults | Stage 3 enables immediate harness-assisted bakeoffs; isolation per task, numeric resource limits, contention signals and cancellation mechanisms remain open | JD-072 governs missing replay context; JD-074 prioritizes interactive work over bounded background experiments. Keep contracts in stage 1; specify isolation, cancellation and standing-authority defaults before stage 3 execution |
| Q-12 (rollback and local analysis model policy resolved) | Stages 2–3; JD-029–JD-031, JD-038–JD-042, JD-075–JD-076 | Analysis implementation + user for risk tolerance | Comparable groups, practical-equivalence margins, batch minima, uncertainty methods, priority scores, promotion/rollback thresholds | JD-075 defines scoped rollback and version suspension; JD-076 requires explicit local analysis model enablement and budgets. Start with versioned rules; calibrate using pilot outcomes and require approval of consequential limits |
| Q-13 | Every stage; JD-047–JD-051 | Evaluation implementation | Actual fixtures, datasets, holdout splits, evaluator independence, sample size, numeric release gates | Define tests and baselines before held-out evaluation; distinguish code review precision/recall from implementation pass rates |
| Q-14 (Git home resolved) | Before adoption/release; JD-052–JD-056 | Governance implementation | Installed pipeline version, brownfield profile, YAML authority support, HTML-to-harness roadmap export | Public Consiliency/jevdrill selected and initialized; source publication and adoption remain separate. Dry-run adoption only after source completeness |

## Implementation follow-through

The interview closeout below supersedes earlier requests for further product-question rounds. The implementation proposal now maps harness integration paths and proposes contract families, storage, import boundaries, and verification gates. Complete its technical proofs and exact schemas before calling the specification implementation-ready. Q-11's experiment isolation, limits, and cancellation details remain stage-3 work.

No automatic change to previously accepted settings is implied by these recommendations. Open questions block only their affected interfaces or stages.

### Interview closeout scope

The planned product interview is complete. JD-078 resolves initial access-route scope; JD-079 resolves initial experiment limit policy; JD-080 requires no meaningful quality regression by default, with explicitly scoped exceptions. These decisions do not reopen earlier answers. Contract schemas, toolchain choices, storage design, adapter hooks, host-specific numeric tuning proposals, and vocabulary tooling should now be researched and drafted by the implementation owner. Raise further user questions only if that work exposes a material unresolved choice. Dependency setup ownership is settled by JD-077: host performs authorized setup; JEV Drill proposes and rechecks.
