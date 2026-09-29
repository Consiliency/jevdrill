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
class HardConstraints { local_only: bool, allowed_providers: string[], spending_ceiling: Money?, total_deadline_ms: int, context_token_limit: int, max_attempts: int, governing_instruction_refs: string[] }
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
