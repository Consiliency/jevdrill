// Public fields are required, including nullable values, unless boundary metadata says otherwise.
enum MissingReason { unsupported, not_reported, not_applicable, redacted, expired, incomplete }
class KnownMeasurement { kind: "known", value: float, unit: string }
class UnknownMeasurement { kind: "unknown", reason: MissingReason }
type MeasurementValue = KnownMeasurement | UnknownMeasurement;
class Measurement {
    metric_id: string, metric_version: string, measurement_value: MeasurementValue,
    source: "direct" | "provider" | "host" | "evaluator" | "estimate",
    method: string, scope: "call" | "run" | "task" | "experiment",
    counting_semantics: "disjoint" | "subset" | "not_applicable",
    parent_metric_id: string?,
}
class Money { amount: string, currency: string }
class CostEstimate { raw_token_cost: Money?, adjusted_token_cost: Money?, observed_cost: Money?, missing_reason: MissingReason?, rate_revision: string, assumptions: string[] }
class ExplicitEffort { kind: "explicit", native_value: string }
class DefaultEffort { kind: "provider_default" }
class UnsupportedEffort { kind: "unsupported" }
type NativeEffort = ExplicitEffort | DefaultEffort | UnsupportedEffort;
class GuidanceRevision {
    resource_id: string, revision: string, content_hash: string, role: string,
    admission: "policy_admitted" | "explicitly_enabled", authority: string,
    task_id: string, token_count: int?,
}
class ExecutionPlan {
    execution_plan_id: string, predecessor_plan_id: string?, model_id: string,
    resolved_model_revision: string?, provider: string, access_route: string,
    native_effort: NativeEffort, optional_guidance: GuidanceRevision[],
    required_guidance: GuidanceRevision[], guidance_action: "none" | "inject",
    required_capabilities: string[], harness_id: string, execution_target_id: string,
}
class RequestEnvelope {
    schema_version: "1", request_id: string, operation: "route" | "report",
    project_id: string, workspace_id: string, harness_id: string,
    execution_target_id: string, created_at: string, idempotency_key: string,
    extensions: baml.Map<string, string>,
}
class AcceptanceRequirement { requirement_id: string, description: string, source: "user" | "task_family" | "inferred", evaluator_ref: string }
class OptimizationObjective { objective_id: string, version: string, metric_id: string, direction: "minimize" | "maximize", routing_cost_basis: "raw" | "adjusted", acceptance_requirements: AcceptanceRequirement[] }
class AttachmentReference { reference: string, modality: "image" | "audio" | "video" | "document", authorized: bool, text_representation: string?, representation_source: string? }
class ExecutionTokenLimits { input_tokens: int, output_tokens: int }
class HardConstraints { local_only: bool, allowed_providers: string[], spending_ceiling: Money?, total_deadline_ms: int, context_token_limit: int, max_attempts: int, governing_instruction_refs: string[], execution_token_limits: ExecutionTokenLimits? }
class RetryContext { prior_routing_decision_id: string, prior_execution_run_id: string, failure_class: "infrastructure" | "quality", failure_summary: string, remaining_attempts: int, remaining_time_ms: int, remaining_spend: Money? }
class Capabilities { declared: string[], runtime: string[], inventory_revision: string, verified_at: string, expires_at: string }
class VersionReferences { settings_revision: string, context_revision: string, catalog_revision: string, policy_revision: string, evidence_revision: string }
class RouteRequest {
    envelope: RequestEnvelope, task_id: string, task_representation: string,
    representation_source: string, attachment_refs: AttachmentReference[],
    optimization_objective: OptimizationObjective, hard_constraints: HardConstraints,
    active_guidance: GuidanceRevision[], capabilities: Capabilities,
    versions: VersionReferences, execution_mode: "main" | "delegated" | "dry_run",
    recursion_bypass: bool, retry_context: RetryContext?,
}
class Diagnostic { code: string, summary: string, evidence_refs: string[], resolution_advice: string[] }
class CapabilityMismatch { code: "capability_mismatch", declared: string[], runtime: string[], effective: string[], affected_operations: string[], evidence_refs: string[], resolution_advice: string[] }
class LocalNotice { notice_id: string, kind: "archive_prompt" | "failure" | "decision_required", summary: string, deadline: string?, automatic_action: "archive" | "none" }
class NoticeRequest { schema_version: "1", scope: CommandScope }
class NoticeInbox { schema_version: "1", notices: LocalNotice[] }
class CandidateExclusion { candidate_id: string, reasons: string[] }
class SetupProposal { candidate_id: string, missing_capabilities: string[], proposed_actions: string[], requires_authorization: bool }
class CloseCall { candidate_ids: string[], differing_dimensions: string[], uncertainty_reason: string, evidence_refs: string[] }
class DecisionDetails {
    schema_version: "1", routing_decision_id: string, request_id: string, task_id: string,
    created_at: string, optimization_objective: OptimizationObjective, versions: VersionReferences,
    diagnostics: Diagnostic[], capability_mismatches: CapabilityMismatch[],
    evidence_refs: string[], exclusions: CandidateExclusion[], alternatives: string[],
    close_calls: CloseCall[], setup_proposals: SetupProposal[], notices: LocalNotice[],
    human_summary: string, acceptance_rationale: string, cost_estimate: CostEstimate,
    measurements: Measurement[], reused_decision_id: string?,
    discovery_ref: DiscoveryRef?, discovery_termination: string?, discovery_uncertainty: string[]?,
}
class ReadinessEvidence { verified_at: string, valid_until: string, inventory_revision: string, checked_capabilities: string[], evidence_refs: string[] }
class Ready { status: "ready", details: DecisionDetails, execution_plan: ExecutionPlan, readiness: ReadinessEvidence, fallback_used: bool }
class NeedsContext { status: "needs_context", details: DecisionDetails, missing_facts: string[] }
class ConstraintConflict { status: "constraint_conflict", details: DecisionDetails, conflicting_requirements: string[] }
class NoCompatiblePlan { status: "no_compatible_plan", details: DecisionDetails }
class RoutingFailed { status: "routing_failed", details: DecisionDetails, error_code: string, retryable: bool }
type RoutingDecision = Ready | NeedsContext | ConstraintConflict | NoCompatiblePlan | RoutingFailed;
class ExecutionRun { execution_run_id: string, task_id: string, selected_plan_id: string, applied_plan_id: string?, prior_execution_run_id: string?, substitution_reason: string?, execution_mode: "main" | "delegated" | "dry_run" }
class LifecyclePayload { kind: "lifecycle", event_type: "queued" | "started" | "plan_applied" | "completed" | "failed" | "canceled" | "guidance_deactivated", applied_plan_id: string?, reason: string? }
class UsagePayload { kind: "usage", measurements: Measurement[] }
class EvaluationPayload { kind: "evaluation", evaluator_ref: string, rubric_revision: string, check_results: baml.Map<string, bool>, measurements: Measurement[] }
class HostChoicePayload { kind: "host_choice", selected_run_id: string, reason: string }
type EventPayload = LifecyclePayload | UsagePayload | EvaluationPayload | HostChoicePayload;
class ExecutionEvent { schema_version: "1", event_id: string, task_id: string, routing_decision_id: string, execution_run_id: string, source_id: string, source_sequence: int, occurred_at: string, supersedes_event_id: string?, payload: EventPayload }
class ReportRequest { envelope: RequestEnvelope, event: ExecutionEvent }
class ReportAccepted { schema_version: "1", status: "accepted", event_id: string, durable: true }
class ReportDuplicate { schema_version: "1", status: "duplicate", event_id: string, durable: true }
class ReportConflict { schema_version: "1", status: "conflict", event_id: string, durable: false, reason: string }
class ReportRejected { schema_version: "1", status: "rejected", event_id: string?, durable: false, reason: string }
type ReportAcknowledgment = ReportAccepted | ReportDuplicate | ReportConflict | ReportRejected;
class Settings {
    schema_version: "1", settings_revision: string, routing_cost_basis: "raw" | "adjusted",
    retain_raw_tasks: bool, retain_raw_outputs: bool, local_analysis_enabled: bool,
    experiment_enabled: bool, model_analysis_enabled: bool,
    default_plan_id: string?, routing_deadline_ms: int,
    excluded_paths: string[], setting_sources: baml.Map<string, string>,
    max_description_utf8_bytes: int?,
}
class ExperimentLimits { max_candidates: int, max_concurrency: int, max_duration_ms: int, cpu_limit: int, memory_limit_bytes: int, per_experiment_spend: Money?, daily_spend: Money? }
class ComparisonExperiment {
    schema_version: "1", comparison_experiment_id: string, task_id: string,
    context_ref: string, context_hash: string, candidate_plans: ExecutionPlan[],
    optimization_objectives: OptimizationObjective[], evaluator_ref: string,
    rubric_revision: string, authorization_revision: string?,
    execution_path: "internal" | "harness_assisted", host_accepted: bool,
    isolation_ref: string, limits: ExperimentLimits,
    experiment_state: "proposed" | "accepted" | "queued" | "running" | "completed" | "incomplete" | "canceled" | "blocked",
    assignment_policy: string, assignment_probabilities: baml.Map<string, float>,
}

function echo_decision(value: RoutingDecision) -> RoutingDecision { value }

class RateCard {
    revision: string, currency: string, input_rate: string?, output_rate: string?,
    verified_at: string, expires_at: string, subscription_multiplier: string?,
}
class CandidateSnapshot {
    candidate_id: string, model_id: string, resolved_model_revision: string,
    provider: string, access_route: string, local: bool, native_effort: NativeEffort,
    supported_efforts: string[], declared_capabilities: string[], runtime_capabilities: string[],
    required_capabilities: string[], verified_at: string, expires_at: string, source: string,
    context_token_limit: int, output_token_limit: int, token_counter_revision: string,
    quality_sufficient: bool?, satisfied_requirements: string[], completion_time_ms: int?,
    evidence_strength: "measured" | "judgment" | "unknown", evidence_refs: string[],
    rates: RateCard?, default: bool, guidance_options: GuidanceRevision[],
    addresses_failures: string[], execution_token_limits: ExecutionTokenLimits?,
}
class InventorySnapshot {
    schema_version: "1", revision: string, target: string, source_version: string,
    verified_at: string, expires_at: string, candidates: CandidateSnapshot[],
}
class CatalogResource {
    resource_id: string, revision: string, content_hash: string, rights: string,
    admission: "policy_admitted" | "explicitly_enabled" | "unadmitted",
    source_occurrences: string[], aliases: string[], domain: string, specialty: string,
    task_family: string, facets: string[], benchmark_protocol: string?, benchmark_split: string?,
    benchmark_effort: string?, instructions: string, conflicts: string[],
}
class CatalogSnapshot { schema_version: "1", revision: string, resources: CatalogResource[] }
class CatalogQuery { domain: string, specialty: string, task_family: string, facets: string[], max_branches: int }
class SettingsOverride {
    routing_cost_basis: ("raw" | "adjusted")?, retain_raw_tasks: bool?, retain_raw_outputs: bool?,
    local_analysis_enabled: bool?, experiment_enabled: bool?, model_analysis_enabled: bool?,
    default_plan_id: string?, routing_deadline_ms: int?, excluded_paths: string[]?,
    max_description_utf8_bytes: int?,
}
class SettingsLayer {
    source: "product" | "user" | "project" | "directory" | "personal_project" | "request",
    values: SettingsOverride,
}
class JudgmentPolicy {
    enabled: bool, cloud_allowed: bool, max_calls: int, max_candidates: int,
    max_input_tokens: int, max_output_tokens: int, spending_ceiling: Money?,
    rates: RateCard?, model_revision: string, function_revision: "JudgeCandidate-v1" | "JudgeCandidate-v2",
    token_counter_revision: string,
}
class RouteInputs {
    schema_version: "1", request: RouteRequest, inventory: InventorySnapshot?,
    catalog: CatalogSnapshot?, settings_layers: SettingsLayer[], judgment_policy: JudgmentPolicy?,
    completion_time_limit_ms: int?,
    catalog_query: CatalogQuery?,
}
class JudgmentRecord {
    schema_version: "1", function_revision: "JudgeCandidate-v1" | "JudgeCandidate-v2", model_revision: string,
    candidate_digest: string, judgments: baml.Map<string, bool>, measurements: Measurement[],
}
class CommandScope {
    project_id: string, workspace_id: string, producer: string, operation: "route" | "report",
}
class InspectRequest { schema_version: "1", scope: CommandScope, decision_id: string, replay: bool }
class DeleteRequest { schema_version: "1", scope: CommandScope, task_id: string }
class ReplayBundle {
    schema_version: "1", routing_decision_id: string, task_id: string, request_digest: string,
    cache_digest: string, decision: RoutingDecision, judgments: JudgmentRecord?,
}

class LearningContext {
    task_id: string, routing_decision_id: string, discovery_ref: DiscoveryRef?,
    task_family: string, task_group: string, environment_revision: string,
    isolation_revision: string, evaluator_ref: string, rubric_revision: string,
    local_analysis_enabled: bool, share_user_wide: bool,
}
class AnalysisRequest {
    schema_version: "1", scope: CommandScope, action: "record" | "analyze" | "inspect",
    context: LearningContext?, objectives: OptimizationObjective[],
    minimum_batch: int, interval_seconds: int, include_user_wide: bool,
    settings_layers: SettingsLayer[],
}
class EvidenceMetric {
    metric_definition: Measurement, sample_count: int, missing_count: int,
    mean: float?, median: float?, p95: float?, minimum: float?, maximum: float?,
}
class EvidenceGroup {
    group_id: string, evidence_scope: "observed_task_group",
    conditions: baml.Map<string, string>, run_count: int,
    completed_count: int, failed_count: int, canceled_count: int, incomplete_count: int,
    accepted_count: int, rejected_count: int, acceptance_unknown_count: int,
    retained_count: int, declined_count: int, preference_unknown_count: int,
    substituted_count: int, applied_unknown_count: int,
    metrics: EvidenceMetric[], observation_refs: string[], sources: ObservationSource[],
}
class ObservationSource {
    origin: "local" | "user_wide_redacted", task_id: string?, routing_decision_id: string?,
    execution_run_id: string?, discovery_ref: DiscoveryRef?,
}
class ObjectiveAssessment {
    objective: OptimizationObjective,
    classification: "insufficient_evidence" | "non_comparable" | "observed",
    group_ids: string[], reason: string,
}
class AnalysisResult {
    schema_version: "1", status: "recorded" | "updated" | "not_due" | "inspected" | "denied",
    evidence_revision: string, source_digest: string, groups: EvidenceGroup[],
    assessments: ObjectiveAssessment[], objective_history: OptimizationObjective[],
}
class MaintenanceRequest {
    schema_version: "1", scope: CommandScope,
    action: "run" | "pause" | "resume" | "cancel" | "schedule",
    interactive_busy: bool, max_items: int, archive_retention_days: int,
    request_path: string?,
}
class MaintenanceResult {
    schema_version: "1", status: "completed" | "paused" | "canceled" | "busy" | "schedule_proposed",
    processed: int, pending: int, notices: LocalNotice[], scheduler_instructions: string[],
}
class RecoveryRequest {
    schema_version: "1", scope: CommandScope, action: "export" | "backup" | "import" | "restore",
    artifact_id: string?, encrypted_bundle: string?, recovery_key: string?,
}
class RecoveryResult {
    schema_version: "1", status: "exported" | "imported" | "restored",
    encrypted_bundle: string?, restored_count: int,
}
class RecoveryArtifact {
    task: string, kind: "raw_task" | "raw_output" | "context", content: string, digest: string,
}
class RecoveryDecision { scope: CommandScope, bundle: ReplayBundle }
class RecoveryEvent { scope: CommandScope, event: ExecutionEvent }
class RecoveryDiscovery {
    scope: CommandScope, discovery_ref: DiscoveryRef,
    status: "selected_guidance" | "no_optional_guidance", revisions: DiscoveryRevisions,
    guidance_refs: DiscoveryGuidanceRef[], domains: string[],
}
class RecoveryBundle {
    schema_version: "1", scope: string, tasks: baml.Map<string, bool>,
    objectives: baml.Map<string, bool>, learning_policy: baml.Map<string, bool>,
    decisions: RecoveryDecision[], events: RecoveryEvent[], contexts: LearningContext[],
    discoveries: RecoveryDiscovery[], artifacts: RecoveryArtifact[],
}

class ExperimentProposal {
    experiment: ComparisonExperiment, task_group: string,
    uncertainty_rank: int, benefit_rank: int, estimated_cost_microusd: int?,
}
class ExperimentRequest {
    schema_version: "1", scope: CommandScope, idempotency_key: string,
    action: "propose" | "inspect" | "cancel",
    proposal: ExperimentProposal?, comparison_experiment_id: string?,
}
class ExperimentQueueEntry {
    proposal: ExperimentProposal, occurrence_count: int,
    priority_revision: "recurrence-benefit-cost-v1", priority_score: string,
}
class ExperimentResult {
    schema_version: "1", status: "recorded" | "duplicate" | "listed" | "canceled" | "not_found",
    experiments: ExperimentQueueEntry[], execution_authorized: false,
}

class ExperimentAuthorization {
    schema_version: "1", authorization_revision: string, scope: CommandScope,
    enabled: bool, task_ids: string[], allowed_providers: string[],
    allowed_harnesses: string[], allowed_execution_paths: string[], allowed_isolation_refs: string[],
    background_allowed: bool, local_only: bool, expires_at: string,
    limits: ExperimentLimits, total_spend_microusd: int,
}
class ExperimentReadiness {
    schema_version: "1", harness_id: string, execution_target_id: string,
    context_hash: string, context_available: bool, local_execution: bool,
    isolation_ref: string, declared_capabilities: string[], runtime_capabilities: string[],
    candidate_plan_digests: string[], spend_bound_verified: bool,
    upper_cost_microusd: int, available_cpu: int, available_memory_bytes: int,
    max_concurrency: int, expires_at: string,
}
class ExperimentExecutionRequest {
    schema_version: "1", scope: CommandScope, comparison_experiment_id: string,
    action: "admit" | "inspect" | "advance" | "cancel", background: bool,
}
class ExperimentCandidateResult {
    execution_plan_id: string, status: "completed" | "failed" | "canceled" | "timeout",
    measurements: Measurement[], acceptance_checks: baml.Map<string, bool>,
    evaluator_ref: string, rubric_revision: string,
}
class ExperimentHostReceipt {
    schema_version: "1", dispatch_token: string, experiment_digest: string,
    host_status: "absent" | "running" | "completed" | "failed" | "canceled",
    cleanup_verified: bool, candidates: ExperimentCandidateResult[],
    preferred_plan_id: string?, preference_reason: string?,
}
class ExperimentExecutionRecord {
    comparison_experiment_id: string, task_id: string, experiment_digest: string,
    authorization_revision: string, authorization_digest: string,
    dispatch_token: string, harness_id: string, reserved_microusd: int,
    admitted_at_ms: int, observed_at_ms: int, deadline_ms: int,
    execution_status: "accepted" | "running" | "completed" | "incomplete" | "cancel_pending" | "canceled",
    receipt: ExperimentHostReceipt?,
}
class ExperimentExecutionResult {
    schema_version: "1", status: "denied" | "not_found" | "recorded",
    reasons: string[], record: ExperimentExecutionRecord?,
}


class QualityCalibration {
    schema_version: "1", calibration_revision: string,
    task_family: "implementation" | "review" | "documentation",
    evaluator_ref: string, rubric_revision: string, dataset_revision: string,
    calibration_source: string, frozen_at: string,
    critical_requirements: string[], quality_floor: float,
    maximum_quality_loss: float, minimum_pairs: int, confidence: float,
}
class PolicyCase {
    case_id: string, related_group: string,
    split: "development" | "validation" | "policy_holdout" | "policy_regression" | "release_holdout",
    exposed_at: string, baseline_quality: float?, candidate_quality: float?,
    baseline_critical: baml.Map<string, bool>, candidate_critical: baml.Map<string, bool>,
    baseline_measurements: Measurement[], candidate_measurements: Measurement[],
}
class PolicyEvaluation {
    schema_version: "1", task_family: "implementation" | "review" | "documentation",
    evaluator_ref: string, rubric_revision: string, dataset_revision: string,
    identities_blinded: bool, evidence_origin: "controlled" | "observational" | "synthetic",
    calibration: QualityCalibration?, cases: PolicyCase[],
}
class PolicyAssessment {
    schema_version: "1", classification: "quality_gate_passed" | "critical_regression" | "quality_regression" | "insufficient_evidence" | "non_comparable",
    calibration_revision: string?, evidence_digest: string,
    pair_count: int, critical_regressions: string[], reasons: string[],
    candidate_quality_lower_bound: float?, quality_loss_upper_bound: float?,
    promotion_authorized: false,
}
class PolicyCandidate { candidate_id: string, candidate_fingerprint: string }
class PolicyCaseAssignment {
    case_id: string, related_group: string, task_id: string,
    split: "policy_holdout" | "policy_regression",
}
class PolicyDefinition {
    schema_version: "1", policy_revision: string, task_group: string,
    baseline_policy_revision: string,
    objective: OptimizationObjective, candidate_order: PolicyCandidate[],
    calibration: QualityCalibration, cases: PolicyCaseAssignment[],
    objective_value_ceiling: float, minimum_improvement: float,
}
class PolicyAuthorization {
    schema_version: "1", authorization_revision: string, scope: CommandScope,
    enabled: bool, allowed_task_groups: string[], allowed_policy_revisions: string[],
    max_routes: int, rollout_basis_points: int, expires_at: string,
}
class PolicyEvidencePreparation {
    schema_version: "1", definition_digest: string, evaluator_identity: string,
    independent: bool, input_revision: string, valid_until: string, evidence_ref: string,
    status: "current" | "critical_regression" | "quality_regression" | "stale",
}
class PolicyRequest {
    schema_version: "1", scope: CommandScope, policy_revision: string,
    action: "register" | "evaluate" | "promote" | "inspect" | "suspend",
    definition: PolicyDefinition?,
}
class PolicyRecord {
    definition: PolicyDefinition, definition_digest: string,
    registered_at: string, observed_at: string, exposed_at: string?,
    policy_status: "registered" | "exposed" | "evaluated" | "active" | "suspended" | "stale",
    preparation: PolicyEvidencePreparation?, evaluation: PolicyEvaluation?, assessment: PolicyAssessment?,
    objective_improvement_lower_bound: float?, reasons: string[],
    authorization: PolicyAuthorization?, previous_policy_revision: string?, used_routes: int,
}
class PolicyResult {
    schema_version: "1", status: "recorded" | "not_found" | "denied",
    reasons: string[], record: PolicyRecord?,
}
