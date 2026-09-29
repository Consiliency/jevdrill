---
phase_loop_plan_version: 1
phase: CONTRACT
roadmap: specs/phase-plans-v1.md
roadmap_sha256: b7b225a492d677a65de4eb59b748659ec09303989e72da4cfdcf81cd991f8700
---

# CONTRACT: Contract and toolchain foundation

## Context

Implement the first phase of the reviewed roadmap. Read the accepted decisions, unchanged product draft, implementation proposal, current-state questions, vocabulary registry, BAML proof and manual-panel ruling. They are source inputs; no implementation gate has passed. The user resolved Q-14's repository choice: public Consiliency/jevdrill, local main and origin initialized. Publishing workspace content and importing research corpora remain separate actions.

The main agent executes lanes serially. No worker fanout or sibling-repository writes are authorized by this plan. Existing research scripts/tests remain separate. Preserve historical evidence and the original draft. CONTRACT is complete only after genuine Linux/macOS/Windows evidence for every supported Python version; unavailable runners block this gate, not independent local work.

## External Inputs

- BAML release `baml-language-0.20.1`, matching `baml-bridge==0.20.1`; use the checksum recorded in `research/baml-proof/README.md` for the Linux artifact. Verify other platform artifacts against release checksums.
- Proof baseline: Python 3.13.15 and Pydantic 2.13.5. Proposed supported Python range is 3.12–3.14, subject to wheel/import checks. Record the actual tested set before freeze; do not claim unsupported versions.
- Read allowlist: `research/baml-proof/README.md`, `research/baml-proof/verify.py`, `research/baml-proof/baml_src/contracts.baml`, `research/roadmap-review/manual-claude/review.md`, `research/roadmap-review/manual-rerun/round1/{opus-review,president-review,reviewed-roadmap}.md`, `research/roadmap-review/manual-rerun/round2/{opus-review,gemini-review}.md`. Read synthetic proof/generated SDK and version-matched source only as needed; no other raw research corpus, credentials or live JEV call is required.

## Interface Freeze Gates

- [ ] IF-0-CONTRACT-1 — BAML-authored public contract families and strict generated Python/schema validators; shared fixture parity; supported platform/toolchain matrix; vocabulary/import rules; coverage amendments; metric/split protocol.
- [ ] IF-0-VC-2 — Every verification command below resolves to an owned implementation and emits machine-readable results; negative controls prove checks reject invalid construction paths.

Freeze major version 1 only after the coverage sweep feeds all contract fields into generation. Publish types for requests, five routing outcomes, immutable plans/runs, report submissions/acknowledgments, measurements, settings, capability diagnostics, notices and comparison experiments. Generate fields from BAML; handwritten code adds named semantic validators, never duplicate field catalogs.

Use explicit UUID identities, UTC timestamps, decimal money strings, tagged missing measurements, native-effort variants, exact guidance revisions and namespaced inert extensions. Distinguish required nullable from omittable fields in authored metadata. Ready alone includes an executable plan; invalid status/field combinations fail before application entry.

Version compatibility must require new shared fixtures and rerunning parity/platform checks for later contract amendments. Publish named validators with portable schemas: Python and the non-Python consumer run the complete boundary validation pipeline. Fixtures separately identify schema-only versus semantic rejection; neither silently relaxes the external boundary.

## Lane Index & Dependencies

SL-0 — Coverage and freeze decisions
  Depends on: (none)
  Blocks: SL-1, SL-2, SL-3, SL-4, SL-5
  Parallel-safe: no

SL-1 — Package/toolchain preamble
  Depends on: SL-0
  Blocks: SL-2, SL-3, SL-4, SL-5
  Parallel-safe: no

SL-2 — Authored/generated contracts and conformance
  Depends on: SL-0, SL-1
  Blocks: SL-4, SL-5
  Parallel-safe: no

SL-3 — Vocabulary and import enforcement
  Depends on: SL-0, SL-1
  Blocks: SL-5
  Parallel-safe: no

SL-4 — Evaluation protocol and fixtures
  Depends on: SL-0, SL-1, SL-2
  Blocks: SL-5
  Parallel-safe: no

SL-5 — Platform verification and docs closeout reducer
  Depends on: SL-0, SL-1, SL-2, SL-3, SL-4
  Blocks: (none)
  Parallel-safe: no

## Lanes

### SL-0 — Coverage and freeze decisions

- **Scope**: Turn every accepted requirement and review obligation into a verifiable owning criterion or explicit deferral before schema work.
- **Owned files**: `specs/phase-plans-v1.md`, `specs/jevdrill-implementation-proposal.md`, `specs/jevdrill-current-state.md`, `evidence/CONTRACT/coverage.json`, `docs/contract-decisions.md`, `scripts/check_contract_coverage.py`, `tests/contracts/test_coverage.py`
- **Interfaces provided**: `coverage_decisions`
- **Interfaces consumed**: `accepted_source_bundle` (pre-existing)
- **Parallel-safe**: no
- **Tasks**:
  - test: Reject absent/duplicate JD coverage, unmapped draft clauses, nonexistent ECs, unsupported completion claims, and deferred entries without reason/owner/affected phase. Include a requirement mapped to an EC that does not verify it.
  - impl: Inventory unchanged draft requirements using stable section/item references and exact source pointers. Distinguish superseded clauses from accepted deferrals. Amend downstream EC text without renumbering. Contract-level findings feed SL-2 before freeze; approval-dependent numeric risk thresholds remain owned questions, not invented accepted decisions.
  - impl: Include retry links/failure classes/budgets; local-only JEV restrictions; attachment references and context limits; setup/acknowledgment shapes; settings provenance; guidance deactivation; host inbox notices; retention opt-out; export/deletion semantics; platform checks; policy revalidation and separated holdouts. Preserve admission versus explicit enablement. Normalize HOST platform evidence to the common verification manifest.
  - verify: `uv run pytest tests/contracts/test_coverage.py`; `uv run python scripts/check_contract_coverage.py`; roadmap lint. Refresh this plan's roadmap hash when its authorized amendments change the roadmap, recording before/after hashes in closeout evidence.

### SL-1 — Package/toolchain preamble

- **Scope**: Establish reproducible dependency installation and shared package/check configuration.
- **Owned files**: `pyproject.toml`, `uv.lock`, `baml.toml`, `.python-version`, `.gitignore`, `src/jevdrill/__init__.py`, `src/jevdrill/py.typed`, `package.json`, `package-lock.json`, `tests/contracts/test_package.py`, `docs/toolchain.md`
- **Interfaces provided**: `package_toolchain`
- **Interfaces consumed**: `coverage_decisions`
- **Parallel-safe**: no
- **Tasks**:
  - test: Check package import from outside the checkout and generator/bridge version mismatch rejection.
  - impl: Use uv, pytest, Ruff and strict mypy for application code; lighter checks for tests/research. Add Pydantic, PyYAML and a portable JSON Schema implementation as needed, locking actual resolved versions. Use a pinned Node validator for the non-Python fixture consumer. Do not expose a placeholder routing CLI.
  - impl: Ignore caches, environments, provider logs and private task data; do not hide authored contracts, schema outputs or metadata evidence. Document whether importing public contracts requires the bridge. Probe wheels/imports before choosing supported Python minors.
  - verify: `uv sync --locked`; `npm ci`; `uv run pytest tests/contracts/test_package.py`; `uv build`.

### SL-2 — Contracts and conformance

- **Scope**: Author portable BAML contracts and verify strict boundaries plus offline JEV integration behavior.
- **Owned files**: `baml_src/**`, `src/jevdrill/contracts.py`, `src/jevdrill/telemetry.py`, `src/jevdrill/_generated/**`, `src/baml_sdk/**`, `schemas/**`, `scripts/check_generated_contracts.py`, `scripts/contract_consumer.mjs`, `tests/contracts/test_boundaries.py`, `tests/contracts/test_generation.py`, `tests/contracts/test_jev_boundary.py`, `tests/contracts/fixtures/**`, `docs/contracts.md`
- **Interfaces provided**: `validated_contracts`
- **Interfaces consumed**: `coverage_decisions`, `package_toolchain`
- **Parallel-safe**: no
- **Tasks**:
  - test: Cover all five status variants; extra/nested unknown fields; booleans as integers; numeric strings including whitespace; nonfinite numbers; missing nullable fields; aliases/enums; unsupported versions; invalid references/status combinations; inert extension constraints; immutable hash-changing fields.
  - impl: Generate in a temporary directory and compare normalized outputs deterministically. Derive strict validation/export from authored definitions/metadata, rejecting unsupported generation constructs instead of editing generated code.
  - impl: Freeze report accepted/duplicate/conflict/rejected acknowledgments; event and experiment transition tables; corrections and late-event projection semantics; CLI exit codes 0/2/3/4, cancellation/deadline behavior, adapter negotiation and deprecated-name handling.
  - impl: Specify canonical idempotency payload encoding with shared cross-language golden digests, sorted object keys, preserved array order and explicit numeric rules; scope keys and exclude only documented transport fields.
  - test: Real pinned bridge with synthetic local HTTP mock verifies aliases, request construction, timeout, cancellation/error mapping, usage-event attribution and complete body/header/metadata redaction for retained telemetry. No credentials or network provider needed.
  - verify: `uv run pytest tests/contracts/test_boundaries.py tests/contracts/test_generation.py tests/contracts/test_jev_boundary.py`; `uv run python scripts/check_generated_contracts.py`; `node scripts/contract_consumer.mjs tests/contracts/fixtures`.

### SL-3 — Vocabulary and imports

- **Scope**: Enforce the declared vocabulary and module dependency direction in code and active documentation.
- **Owned files**: `docs/vocabulary.yaml`, `docs/vocabulary.md`, `scripts/render_vocabulary.py`, `scripts/lint_vocabulary.py`, `scripts/check_import_boundaries.py`, `tests/contracts/test_vocabulary.py`, `tests/contracts/test_import_boundaries.py`
- **Interfaces provided**: `vocabulary_import_checks`
- **Interfaces consumed**: `coverage_decisions`, `package_toolchain`
- **Parallel-safe**: no
- **Tasks**:
  - test: Introduce forbidden aliases, ambiguous public fields, undeclared owners, stale glossary output, relative/absolute forbidden imports and cycles; require rejection. Exercise narrow external/historical exemptions without exempting owned code.
  - impl: Extend the existing renderer and registry; scope prose checks to active owned docs and public identifier references. Check declared module ownership and graph using AST, with generated/runtime boundaries explicitly classified. Do not claim arbitrary prose semantic validation.
  - verify: `uv run pytest tests/contracts/test_vocabulary.py tests/contracts/test_import_boundaries.py`; `uv run python scripts/render_vocabulary.py --check`; `uv run python scripts/lint_vocabulary.py`; `uv run python scripts/check_import_boundaries.py`.

### SL-4 — Evaluation protocol

- **Scope**: Define measurable routing outcomes and data separation before any tuning or performance claim.
- **Owned files**: `src/jevdrill/evaluation.py`, `docs/evaluation-protocol.md`, `tests/evaluation/**`, `evidence/CONTRACT/evaluation-protocol.json`
- **Interfaces provided**: `evaluation_protocol`
- **Interfaces consumed**: `coverage_decisions`, `package_toolchain`, `validated_contracts`
- **Parallel-safe**: no
- **Tasks**:
  - test: Reject incompatible units/definitions, treating unknown as zero, overlapping reasoning/cache double counts, parallel-time summation, evaluator preference treated as correctness, and related-task split leakage.
  - impl: Define quality, elapsed/startup/first-output time, token efficiency, raw/adjusted cost, reliability, intervention and guidance benefit including useful-guidance recall, unnecessary injection and calibration.
  - impl: Define JD-050's fixed user default, cheapest feasible, selected model without optional guidance and previous policy baselines; additionally include the draft's simple retrieval baseline where applicable. Use task-family rubrics with blinded evaluator identity. Separate development, validation, policy held-out/regression cases and sealed release holdout, with exposure history.
  - impl: Record proposed quality floors/tolerances and evidence thresholds as provisional until approved/calibrated before exposure. Keep user risk-tolerance decisions visible; no empirical claim from synthetic fixtures.
  - verify: `uv run pytest tests/evaluation`.

### SL-5 — Platform verification and docs closeout

- **Scope**: Collect real platform evidence and reconcile all outputs before marking any CONTRACT gate complete.
- **Owned files**: `.github/workflows/contracts.yml`, `scripts/verify_contract_phase.py`, `scripts/install_contract_compiler.py`, `tests/contracts/test_phase_verification.py`, `evidence/CONTRACT/verification.json`, `evidence/CONTRACT/platforms/**`, `evidence/CONTRACT/spec-delta.json`, `docs/contract-readiness.md`, `README.md`
- **Interfaces provided**: `contract_verification`
- **Interfaces consumed**: `coverage_decisions`, `package_toolchain`, `validated_contracts`, `vocabulary_import_checks`, `evaluation_protocol`
- **Parallel-safe**: no
- **Tasks**:
  - test: Runner refuses missing OS/minor results, stale input digests, mismatched tool pins, skipped assertions or fabricated proxy evidence; aggregates independent failures.
  - impl: Run shared positive/negative fixtures with the pinned generated package and bridge on Linux/macOS/Windows for every frozen Python minor. Record OS/architecture, runner identity, commands, dependency/input digests and outcome. CI workflow creation is not evidence of a CI run.
  - impl: Document pin changes explicitly and rerun affected checks. No local simulation substitutes for missing platform evidence; a proxy requires a runner-stamped roadmap amendment.
  - impl: Verify every lane's output and coverage links, preserve all gates open until evidence supports closure, and record unresolved questions by owner/phase.
  - impl: Update README with package installation and contract-check commands while preserving research limitations. No external release, tag or workflow dispatch occurs in this phase; platform evidence may come from existing authorized runners.
  - verify: `uv run python scripts/verify_contract_phase.py`; `phase-loop validate-roadmap specs/phase-plans-v1.md`; phase-owned diff and closeout audit.

## Execution Notes

Execute serially in dependency order. SL-0 owns roadmap amendments; SL-5 consumes its coverage without rewriting it. If a later lane discovers a missing field or incompatible rule, reopen its producer lane explicitly before continuing. These internal lane interface labels are planning references, not additional public vocabulary. The suite and cross-platform results must exist before IF-0-VC-2 and IF-0-CONTRACT-1 close; command names alone do not establish verification.

Packaging amendment: reopen SL-1/SL-2/SL-3 after the real bridge test exposed the compiler's fixed `baml_sdk` import paths. Relocate unmodified generated output to `src/baml_sdk`, package it explicitly, and enforce its imports as a generated boundary. Do not patch generated code or install global import aliases.

SL-2 additionally owns `src/jevdrill/telemetry.py` for an allowlist projection of JEV measurements: the pinned provider leaves response headers in events even with wire capture disabled. SL-5 additionally owns `tests/contracts/test_phase_verification.py` for reducer negative controls.

Generated SDK files under `src/baml_sdk/**` may be force-staged despite the generator's own ignore rules; omit Python caches. Native fleet verification may copy only application/configuration/docs/specs/scripts/tests and synthetic evidence inputs to isolated per-user directories. Do not copy research corpora, credentials, provider logs or local task data. Historical Unix research regressions run on Linux; all product checks run on every supported platform.

## Verification

Effective `automation.suite_command`: `uv run python scripts/verify_contract_phase.py`. SL-5 implements it as the aggregate of all lane checks plus `uv run ruff check src tests/contracts tests/evaluation`, `uv run ruff format --check src tests/contracts tests/evaluation`, `uv run mypy src/jevdrill`, `uv build`, and existing catalog unittest discovery. It writes metadata-only `evidence/CONTRACT/verification.json`; missing platform evidence means blocked, not passed. Commands referencing new files are deliverables, not checks already run.

## Acceptance Criteria

- [ ] EC-CONTRACT-1 — proven by `uv run pytest tests/contracts/test_boundaries.py tests/contracts/test_generation.py`; falsified by an invalid status or scalar accepted through `src/jevdrill/contracts.py` with the public parser path entered.
- [ ] EC-CONTRACT-2 — proven by `uv run python scripts/verify_contract_phase.py`; falsified by a shared fixture mismatch, stale generation or missing platform/minor manifest passed to the actual suite reducer.
- [ ] EC-CONTRACT-3 — proven by `uv run pytest tests/contracts/test_vocabulary.py tests/contracts/test_import_boundaries.py tests/contracts/test_boundaries.py`; falsified by a forbidden import, alias or incompatible version entering the actual checker and passing.
- [ ] EC-CONTRACT-4 — proven by `uv run pytest tests/contracts/test_coverage.py tests/evaluation`; falsified by an unchecked requirement entering `scripts/check_contract_coverage.py` or exposure-contaminated holdout entering `src/jevdrill/evaluation.py` and passing.

## Spec Closeout Plan

- schema: `spec_delta_closeout.v1`
- decision: `roadmap_amendment`
- target surfaces: `specs/phase-plans-v1.md`, `specs/jevdrill-implementation-proposal.md`, `specs/jevdrill-current-state.md`, `docs/vocabulary.yaml`
- evidence paths: `evidence/CONTRACT/spec-delta.json`, `evidence/CONTRACT/coverage.json`, `evidence/CONTRACT/verification.json`
- redaction posture: `metadata_only`
- downstream handling: roadmap amendment

Do not claim ratification, canonical adoption or release authorization. ROUTE planning follows only when CONTRACT's actual gate is complete.

