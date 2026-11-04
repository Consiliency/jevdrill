"""Comparable observational evidence; no routing, navigation or promotion effects."""

import copy
import math
import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from .contracts import ContractError, canonical_digest, parse_contract
from .evaluation import evaluate_policy, require_comparable
from .routing import candidate_fingerprint
from .storage import SQLiteStorage


class PolicyEvidencePort(Protocol):
    """Trusted independent evaluator, configured outside public policy requests.

    Prepare verifies dataset membership, group separation, provenance and current
    monitoring evidence without exposing held-out answers. Evaluate runs once,
    after durable exposure registration. Neither method may initiate paid work.
    """

    def prepare(self, definition: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def evaluate(self, definition: Mapping[str, Any], exposed_at: str) -> Mapping[str, Any]: ...


PolicyAuthority = Callable[[Mapping[str, str]], Mapping[str, Any] | None]


@dataclass(frozen=True)
class RecordedPolicyStudy:
    """Trusted study selection frozen before execution; outcomes sealed afterward."""

    definition: Mapping[str, Any]
    comparisons: Mapping[str, Mapping[str, Any]]
    protocol_frozen_at: str
    valid_until: str
    evaluator_identity: str
    evidence_origin: str


class RecordedPolicyEvidence:
    """Bind recorded comparisons to a frozen study and an independent grader.

    The host supplies studies, retained artifacts, a versioned blind grader and
    exposure history from other stores/dataset aliases. Public requests supply
    none of these. Hashes establish continuity, not the truth of host metadata.
    No method starts an experiment, makes a model call or grants promotion.
    """

    def __init__(
        self,
        storage: SQLiteStorage,
        scope: Mapping[str, str],
        studies: Sequence[RecordedPolicyStudy],
        *,
        artifacts: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        grade: Callable[[str, Sequence[str | None]], Sequence[Mapping[str, Any]]],
        grader_revision: Callable[[], str],
        exposure_history: Callable[[str, Sequence[str]], Mapping[str, str]],
    ) -> None:
        self.storage, self.scope = storage, dict(scope)
        self.artifacts, self.grade, self.exposure_history = artifacts, grade, exposure_history
        self.grader_revision = grader_revision
        self.studies: dict[str, dict[str, Any]] = {}
        for source in studies:
            study = copy.deepcopy(asdict(source))
            definition = parse_contract("PolicyDefinition", study["definition"]).payload()
            revision = definition["policy_revision"]
            if revision in self.studies:
                raise ContractError("policy_duplicate_study")
            calibration = definition["calibration"]
            frozen = datetime.fromisoformat(study["protocol_frozen_at"])
            if (
                frozen.tzinfo is None
                or datetime.fromisoformat(study["valid_until"]).tzinfo is None
                or frozen < datetime.fromisoformat(calibration["frozen_at"])
                or datetime.fromisoformat(study["valid_until"]) <= frozen
                or not study["evaluator_identity"].strip()
                or study["evidence_origin"] not in {"controlled", "observational", "synthetic"}
            ):
                raise ContractError("policy_study_provenance_invalid")
            study["definition"] = dict(definition)
            self.studies[revision] = study

    @staticmethod
    def protocol(study: RecordedPolicyStudy) -> dict[str, Any]:
        """Pre-execution selection; output hashes are sealed after completion."""
        payload = copy.deepcopy(asdict(study))
        for comparison in payload["comparisons"].values():
            comparison.pop("artifacts_digest")
        return payload

    def _snapshot(
        self, definition: Mapping[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        study = self.studies.get(definition["policy_revision"])
        if study is None or canonical_digest(definition) != canonical_digest(study["definition"]):
            raise ContractError("policy_study_binding_mismatch")
        if self.grader_revision() != study["evaluator_identity"]:
            raise ContractError("policy_grader_revision_mismatch")
        protocol = copy.deepcopy(study)
        for comparison in protocol["comparisons"].values():
            comparison.pop("artifacts_digest")
        if canonical_digest(
            self.storage.policy_study(self.scope, definition["policy_revision"])
        ) != (canonical_digest(protocol)):
            raise ContractError("policy_frozen_protocol_missing_or_changed")
        assignments = definition["cases"]
        groups = [case["related_group"] for case in assignments]
        if (
            len(set(groups)) != len(groups)
            or len({c["case_id"] for c in assignments}) != len(assignments)
            or set(study["comparisons"]) != {c["case_id"] for c in assignments}
        ):
            raise ContractError("policy_dataset_membership_mismatch")
        history = self.exposure_history(definition["calibration"]["dataset_revision"], groups)
        if (
            not isinstance(history, Mapping)
            or set(history) != set(groups)
            or any(history[g] != "unexposed" for g in groups)
        ):
            raise ContractError("policy_external_exposure_unverified")
        for prior in self.storage.policy_records(self.scope):
            if (
                prior["exposed_at"] is not None
                and prior["definition_digest"] != canonical_digest(definition)
                and set(groups).intersection(
                    c["related_group"] for c in prior["definition"]["cases"]
                )
            ):
                raise ContractError("policy_related_group_already_exposed")
        seen_experiments, seen_contexts, snapshots = set(), set(), []
        frozen_ms = datetime.fromisoformat(study["protocol_frozen_at"]).timestamp() * 1000
        for assignment in assignments:
            binding = study["comparisons"][assignment["case_id"]]
            if set(binding) != {
                "assignment",
                "comparison_experiment_id",
                "experiment_digest",
                "baseline_plan",
                "candidate_plan",
                "artifacts_digest",
            } or canonical_digest(binding["assignment"]) != canonical_digest(assignment):
                raise ContractError("policy_case_binding_mismatch")
            identity = binding["comparison_experiment_id"]
            if identity in seen_experiments:
                raise ContractError("policy_duplicate_comparison")
            seen_experiments.add(identity)
            if self.storage.is_deleted(self.scope, assignment["task_id"]):
                raise ContractError("policy_task_deleted")
            if not self.storage.experiment_context_current(self.scope, identity):
                raise ContractError("policy_comparison_context_changed")
            job = self.storage.experiment_execution(self.scope, identity)
            if job is None or job["experiment"] is None:
                raise ContractError("policy_comparison_unavailable")
            experiment, record = job["experiment"], job["record"]
            receipt = record["receipt"]
            if (
                record["task_id"] != assignment["task_id"]
                or canonical_digest(experiment) != binding["experiment_digest"]
                or record["experiment_digest"] != binding["experiment_digest"]
                or record["admitted_at_ms"] <= frozen_ms
                or record["execution_status"] not in {"completed", "incomplete"}
                or receipt is None
                or not receipt["cleanup_verified"]
                or receipt["host_status"] not in {"completed", "failed"}
                or receipt["experiment_digest"] != record["experiment_digest"]
                or receipt["dispatch_token"] != record["dispatch_token"]
                or any(
                    experiment[k] != definition["calibration"][k]
                    for k in ("evaluator_ref", "rubric_revision")
                )
            ):
                raise ContractError("policy_comparison_binding_mismatch")
            if experiment["context_hash"] in seen_contexts:
                raise ContractError("policy_related_context_reused")
            seen_contexts.add(experiment["context_hash"])
            plans = [
                parse_contract("ExecutionPlan", binding[k]).payload()
                for k in ("baseline_plan", "candidate_plan")
            ]
            plan_ids = [p["execution_plan_id"] for p in plans]
            if len(set(plan_ids)) != 2 or sorted(map(canonical_digest, plans)) != sorted(
                canonical_digest(p) for p in experiment["candidate_plans"]
            ):
                raise ContractError("policy_plan_binding_mismatch")
            if any(
                candidate_fingerprint(p)
                not in {c["candidate_fingerprint"] for c in definition["candidate_order"]}
                for p in plans
            ):
                raise ContractError("policy_candidate_fingerprint_mismatch")
            results = {r["execution_plan_id"]: r for r in receipt["candidates"]}
            if len(results) != len(receipt["candidates"]) or set(results) != set(plan_ids):
                raise ContractError("policy_comparison_incomplete")
            artifact = dict(self.artifacts(copy.deepcopy(record)))
            if (
                canonical_digest(artifact) != binding["artifacts_digest"]
                or set(artifact) != {"experiment_digest", "context_hash", "observations"}
                or artifact["experiment_digest"] != record["experiment_digest"]
                or artifact["context_hash"] != experiment["context_hash"]
            ):
                raise ContractError("policy_artifacts_changed")
            observations = {r["execution_plan_id"]: r for r in artifact["observations"]}
            if len(observations) != len(artifact["observations"]) or set(observations) != set(
                plan_ids
            ):
                raise ContractError("policy_comparison_incomplete")
            for plan_id in plan_ids:
                if (
                    canonical_digest(observations[plan_id]["measurements"])
                    != canonical_digest(results[plan_id]["measurements"])
                    or (
                        results[plan_id]["status"] == "completed"
                        and not observations[plan_id]["completed"]
                    )
                    or observations[plan_id]["requested_model"]
                    != next(
                        p["resolved_model_revision"]
                        for p in plans
                        if p["execution_plan_id"] == plan_id
                    )
                ):
                    raise ContractError("policy_observation_binding_mismatch")
            snapshots.append(
                {
                    "assignment": assignment,
                    "plans": plans,
                    "record": record,
                    "observations": observations,
                    "results": results,
                }
            )
            if self.storage.is_deleted(self.scope, assignment["task_id"]):
                raise ContractError("policy_task_deleted")
        return study, snapshots

    def prepare(self, definition: Mapping[str, Any]) -> Mapping[str, Any]:
        study, snapshots = self._snapshot(definition)
        return {
            "schema_version": "1",
            "definition_digest": canonical_digest(definition),
            "evaluator_identity": study["evaluator_identity"],
            "independent": True,
            "input_revision": canonical_digest(study),
            "valid_until": study["valid_until"],
            "status": "current",
            "evidence_ref": canonical_digest([s["record"]["experiment_digest"] for s in snapshots]),
        }

    def evaluate(self, definition: Mapping[str, Any], exposed_at: str) -> Mapping[str, Any]:
        study, snapshots = self._snapshot(definition)
        registered = next(
            (
                r
                for r in self.storage.policy_records(self.scope)
                if r["definition_digest"] == canonical_digest(definition)
            ),
            None,
        )
        if (
            registered is None
            or registered["policy_status"] != "exposed"
            or (
                registered["exposed_at"] != exposed_at
                or registered["preparation"]["input_revision"] != canonical_digest(study)
            )
        ):
            raise ContractError("policy_durable_exposure_missing")
        cases = []
        for snapshot in snapshots:
            case = snapshot["assignment"]
            ids = [p["execution_plan_id"] for p in snapshot["plans"]]
            # The grader receives only a case key and output text, without model,
            # plan, timing, usage, host preference or baseline/candidate labels.
            if int(canonical_digest([canonical_digest(definition), case["case_id"]])[:8], 16) % 2:
                ids.reverse()
            outputs = [snapshot["observations"][i]["output"] for i in ids]
            labels = {
                p[k]
                for p in snapshot["plans"]
                for k in ("model_id", "resolved_model_revision")
                if p[k]
            }
            if any(
                label.casefold() in output.casefold()
                for output in outputs
                if output
                for label in labels
            ):
                raise ContractError("policy_output_identity_visible")
            try:
                grading_key = canonical_digest(
                    [definition["calibration"]["dataset_revision"], case["case_id"]]
                )
                grades = list(self.grade(grading_key, outputs))
            except (TypeError, ValueError):
                raise ContractError("policy_grader_result_invalid") from None
            if len(grades) != 2 or any(
                not isinstance(g, Mapping) or set(g) != {"quality", "critical"} for g in grades
            ):
                raise ContractError("policy_grader_result_invalid")
            scored = dict(zip(ids, grades, strict=True))
            row = {k: case[k] for k in ("case_id", "related_group", "split")}
            row["exposed_at"] = exposed_at
            for role, plan in zip(("baseline", "candidate"), snapshot["plans"], strict=True):
                identity = plan["execution_plan_id"]
                completed = snapshot["results"][identity]["status"] == "completed"
                row[role + "_quality"] = scored[identity]["quality"] if completed else None
                row[role + "_critical"] = scored[identity]["critical"] if completed else {}
                row[role + "_measurements"] = snapshot["observations"][identity]["measurements"]
            cases.append(row)
        # A grader cannot race deletion or source replacement into accepted evidence.
        _, following = self._snapshot(definition)
        if canonical_digest(following) != canonical_digest(snapshots):
            raise ContractError("policy_evidence_changed")
        return dict(
            parse_contract(
                "PolicyEvaluation",
                {
                    "schema_version": "1",
                    "identities_blinded": True,
                    "evidence_origin": study["evidence_origin"],
                    "calibration": definition["calibration"],
                    **{
                        k: definition["calibration"][k]
                        for k in (
                            "task_family",
                            "evaluator_ref",
                            "rubric_revision",
                            "dataset_revision",
                        )
                    },
                    "cases": cases,
                },
            ).payload()
        )


class PolicyLifecycle:
    def __init__(
        self,
        storage: SQLiteStorage,
        authority: PolicyAuthority | None = None,
        evidence: PolicyEvidencePort | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.storage, self.authority, self.evidence = storage, authority, evidence
        self.clock = clock or (lambda: datetime.now(UTC))

    def _timestamp(self) -> str:
        return self.clock().astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    @staticmethod
    def _result(record: Mapping[str, Any] | None, *reasons: str) -> dict[str, Any]:
        return dict(
            parse_contract(
                "PolicyResult",
                {
                    "schema_version": "1",
                    "status": "denied" if reasons else "recorded" if record else "not_found",
                    "reasons": list(reasons),
                    "record": record,
                },
            ).payload()
        )

    def _prepare(self, record: Mapping[str, Any]) -> dict[str, Any]:
        if self.evidence is None:
            raise ContractError("policy_independent_evaluator_unavailable")
        preparation = parse_contract(
            "PolicyEvidencePreparation", self.evidence.prepare(copy.deepcopy(record["definition"]))
        ).payload()
        if (
            preparation["definition_digest"] != record["definition_digest"]
            or not preparation["independent"]
        ):
            raise ContractError("policy_provenance_unverified")
        if datetime.fromisoformat(preparation["valid_until"]) <= self.clock():
            raise ContractError("policy_evidence_expired")
        if self.clock() < datetime.fromisoformat(record["observed_at"]):
            raise ContractError("policy_clock_regression")
        if preparation["status"] != "current":
            raise ContractError("policy_" + preparation["status"])
        prior = record["preparation"]
        if prior and any(
            preparation[key] != prior[key] for key in ("input_revision", "evaluator_identity")
        ):
            raise ContractError("policy_evidence_changed")
        return dict(preparation)

    def _authority(self, scope: Mapping[str, str], record: Mapping[str, Any]) -> dict[str, Any]:
        source = self.authority(scope) if self.authority else None
        if source is None:
            raise ContractError("policy_promotion_authority_unavailable")
        authority = parse_contract("PolicyAuthorization", source).payload()
        definition = record["definition"]
        if not authority["enabled"] or any(authority["scope"][key] != scope[key] for key in scope):
            raise ContractError("policy_promotion_not_authorized")
        if (
            definition["task_group"] not in authority["allowed_task_groups"]
            or definition["policy_revision"] not in authority["allowed_policy_revisions"]
        ):
            raise ContractError("policy_promotion_scope_mismatch")
        if datetime.fromisoformat(authority["expires_at"]) <= self.clock():
            raise ContractError("policy_promotion_authority_expired")
        if record["authorization"] is not None and canonical_digest(
            record["authorization"]
        ) != canonical_digest(authority):
            raise ContractError("policy_promotion_authority_changed")
        return dict(authority)

    @staticmethod
    def _improvement(definition: Mapping[str, Any], evaluation: Mapping[str, Any]) -> float:
        objective = definition["objective"]
        unit = {"raw_token_cost": "USD", "completion_time_ms": "ms"}.get(objective["metric_id"])
        if (
            unit is None
            or objective["direction"] != "minimize"
            or (
                objective["metric_id"] == "raw_token_cost"
                and objective["routing_cost_basis"] != "raw"
            )
        ):
            raise ContractError("policy_objective_unsupported")
        ceiling = definition["objective_value_ceiling"]
        alpha = 1 - definition["calibration"]["confidence"]
        improvements: dict[str, list[float]] = {"policy_holdout": [], "policy_regression": []}
        reference = None
        for case in evaluation["cases"]:
            pair = []
            for key in ("baseline_measurements", "candidate_measurements"):
                matching = [m for m in case[key] if m["metric_id"] == objective["metric_id"]]
                if len(matching) != 1 or matching[0]["source"] == "estimate":
                    raise ContractError("policy_objective_measurement_missing")
                metric = parse_contract("Measurement", matching[0])
                require_comparable(reference or metric, metric)
                if matching[0]["measurement_value"]["unit"] != unit:
                    raise ContractError("policy_objective_unit_mismatch")
                reference = metric
                value = matching[0]["measurement_value"]["value"]
                if not 0 <= value <= ceiling:
                    raise ContractError("policy_objective_bound_exceeded")
                pair.append(value)
            difference = pair[0] - pair[1]
            improvements[case["split"]].append(
                difference if objective["direction"] == "minimize" else -difference
            )
        bounds = [
            statistics.fmean(rows) - 2 * ceiling * math.sqrt(math.log(2 / alpha) / (2 * len(rows)))
            for rows in improvements.values()
        ]
        return float(min(bounds))

    def handle(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = parse_contract("PolicyRequest", payload).payload()
        scope, revision, action = request["scope"], request["policy_revision"], request["action"]
        records = self.storage.policy_records(scope)
        record = next((r for r in records if r["definition"]["policy_revision"] == revision), None)
        if (action == "register") != (request["definition"] is not None):
            raise ContractError("policy_action_fields_invalid")
        try:
            if action == "register":
                definition = request["definition"]
                if revision != definition["policy_revision"]:
                    raise ContractError("policy_revision_mismatch")
                if record:
                    if record["definition_digest"] != canonical_digest(definition):
                        raise ContractError("policy_definition_conflict")
                    return self._result(record)
                cases = definition["cases"]
                for key in ("case_id", "related_group"):
                    if len({case[key] for case in cases}) != len(cases) or any(
                        not case[key].strip() for case in cases
                    ):
                        raise ContractError("policy_duplicate_or_missing_case_group")
                if {case["split"] for case in cases} != {"policy_holdout", "policy_regression"}:
                    raise ContractError("policy_both_splits_required")
                candidates = definition["candidate_order"]
                if len({c["candidate_id"] for c in candidates}) != len(candidates):
                    raise ContractError("policy_duplicate_candidate")
                if datetime.fromisoformat(definition["calibration"]["frozen_at"]) > self.clock():
                    raise ContractError("policy_calibration_in_future")
                following = {
                    "definition": definition,
                    "definition_digest": canonical_digest(definition),
                    "registered_at": self._timestamp(),
                    "observed_at": self._timestamp(),
                    "exposed_at": None,
                    "policy_status": "registered",
                    "preparation": None,
                    "evaluation": None,
                    "assessment": None,
                    "objective_improvement_lower_bound": None,
                    "reasons": [],
                    "authorization": None,
                    "previous_policy_revision": None,
                    "used_routes": 0,
                }
                following["preparation"] = self._prepare(following)
            elif record is None or action == "inspect":
                return self._result(record)
            elif action == "suspend":
                following = dict(record) | {
                    "policy_status": "suspended",
                    "reasons": ["operator_suspended"],
                }
            elif action == "evaluate":
                if record["policy_status"] != "registered":
                    return self._result(record, "policy_exposure_cannot_be_repeated")
                self._prepare(record)
                exposed = self.clock()
                if exposed <= datetime.fromisoformat(
                    record["registered_at"]
                ) or exposed <= datetime.fromisoformat(
                    record["definition"]["calibration"]["frozen_at"]
                ):
                    raise ContractError("policy_exposure_must_follow_registration")
                following = dict(record) | {
                    "policy_status": "exposed",
                    "exposed_at": self._timestamp(),
                    "observed_at": self._timestamp(),
                }
                if not self.storage.store_policy(scope, following, record):
                    raise ContractError("policy_concurrent_update")
                record = following
                assert self.evidence is not None
                evaluation = parse_contract(
                    "PolicyEvaluation",
                    self.evidence.evaluate(
                        copy.deepcopy(record["definition"]), record["exposed_at"]
                    ),
                ).payload()
                expected = record["definition"]
                if canonical_digest(evaluation["calibration"]) != canonical_digest(
                    expected["calibration"]
                ):
                    raise ContractError("policy_calibration_changed")
                assignments = {c["case_id"]: c for c in expected["cases"]}
                if len(evaluation["cases"]) != len(assignments) or {
                    c["case_id"] for c in evaluation["cases"]
                } != set(assignments):
                    raise ContractError("policy_case_binding_mismatch")
                if any(
                    c["exposed_at"] != record["exposed_at"]
                    or any(c[k] != assignments[c["case_id"]][k] for k in ("related_group", "split"))
                    for c in evaluation["cases"]
                ):
                    raise ContractError("policy_exposure_binding_mismatch")
                assessment = evaluate_policy(evaluation)
                following = dict(record) | {
                    "policy_status": "evaluated",
                    "evaluation": evaluation,
                    "assessment": assessment,
                    "reasons": list(assessment["reasons"]),
                }
                if assessment["classification"] == "quality_gate_passed":
                    try:
                        improvement = self._improvement(expected, evaluation)
                        following["objective_improvement_lower_bound"] = improvement
                        following["reasons"] = (
                            []
                            if improvement >= expected["minimum_improvement"]
                            else ["policy_objective_improvement_unproven"]
                        )
                    except ContractError as error:
                        following["reasons"] = [str(error)]
            elif action == "promote":
                if record["policy_status"] == "active":
                    return self._result(record)
                if (
                    record["policy_status"] != "evaluated"
                    or record["reasons"]
                    or record["assessment"]["classification"] != "quality_gate_passed"
                ):
                    raise ContractError("policy_evidence_not_eligible")
                self._prepare(record)
                authority = self._authority(scope, record)
                active = next(
                    (
                        r
                        for r in records
                        if r["definition"]["task_group"] == record["definition"]["task_group"]
                        and r["policy_status"] == "active"
                    ),
                    None,
                )
                if record["definition"]["baseline_policy_revision"] != (
                    active["definition"]["policy_revision"] if active else "execution-ceilings-v1"
                ):
                    raise ContractError("policy_evaluated_baseline_changed")
                following = dict(record) | {
                    "policy_status": "active",
                    "authorization": authority,
                    "previous_policy_revision": active["definition"]["policy_revision"]
                    if active
                    else None,
                }
            else:
                raise ContractError("policy_action_invalid")
            following["observed_at"] = self._timestamp()
            self._result(following)
            if not self.storage.store_policy(scope, following, record):
                raise ContractError("policy_concurrent_update")
            return self._result(following)
        except ContractError as error:
            return self._result(record, str(error))
        except OSError:
            return self._result(record, "policy_evaluator_unavailable")

    def ordering(
        self,
        scope: Mapping[str, str],
        task_group: str,
        objective: Mapping[str, Any],
        request_id: str,
        task_id: str,
    ) -> dict[str, Any]:
        if self.storage.is_deleted(scope, task_id):
            return {"status": "blocked"}
        records = self.storage.policy_records(scope, task_group)
        active = next((r for r in records if r["policy_status"] == "active"), None)
        if active is None:
            return {
                "status": "blocked"
                if any(r["authorization"] is not None for r in records)
                else "inactive"
            }
        try:
            self._prepare(active)
            authority = self._authority(scope, active)
        except (ContractError, OSError) as error:
            reason = (
                str(error) if isinstance(error, ContractError) else "policy_evaluator_unavailable"
            )
            suspended = dict(active) | {"policy_status": "suspended", "reasons": [reason]}
            if not self.storage.store_policy(scope, suspended, active):
                return {"status": "blocked"}
            prior = next(
                (
                    r
                    for r in records
                    if r["definition"]["policy_revision"] == active["previous_policy_revision"]
                ),
                None,
            )
            if prior is None or prior["policy_status"] != "evaluated" or prior["reasons"]:
                return {"status": "blocked"}
            try:
                self._prepare(prior)
                self._authority(scope, prior)
                if prior["used_routes"] >= prior["authorization"]["max_routes"]:
                    return {"status": "blocked"}
            except (ContractError, OSError):
                return {"status": "blocked"}
            restored = dict(prior) | {"policy_status": "active", "previous_policy_revision": None}
            if not self.storage.store_policy(scope, restored, prior):
                return {"status": "blocked"}
            return self.ordering(scope, task_group, objective, request_id, task_id)
        if canonical_digest(objective) != canonical_digest(active["definition"]["objective"]):
            return {"status": "inactive"}
        cohort = int(canonical_digest([active["definition_digest"], task_id])[:16], 16) % 10000
        if cohort >= authority["rollout_basis_points"]:
            return {"status": "inactive"}
        if not self.storage.use_policy(scope, active, request_id, self._timestamp()):
            return {"status": "blocked"}
        return {
            "status": "ready",
            "policy_revision": active["definition"]["policy_revision"],
            "candidate_order": active["definition"]["candidate_order"],
            "evidence_digest": active["assessment"]["evidence_digest"],
        }


def aggregate_observations(observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for observation in observations:
        grouped.setdefault(canonical_digest(observation["conditions"]), []).append(observation)
    result = []
    for identity, rows in sorted(grouped.items()):
        metrics: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            for measurement in row["measurements"]:
                definition = {k: v for k, v in measurement.items() if k != "measurement_value"}
                definition["unit"] = measurement["measurement_value"].get("unit")
                metrics.setdefault(canonical_digest(definition), []).append(measurement)
        summaries = []
        for _, measurements in sorted(metrics.items()):
            values = sorted(
                m["measurement_value"]["value"]
                for m in measurements
                if m["measurement_value"]["kind"] == "known"
            )
            summaries.append(
                {
                    "metric_definition": measurements[0],
                    "sample_count": len(values),
                    "missing_count": len(measurements) - len(values),
                    "mean": statistics.fmean(values) if values else None,
                    "median": statistics.median(values) if values else None,
                    "p95": values[math.ceil(len(values) * 0.95) - 1] if values else None,
                    "minimum": values[0] if values else None,
                    "maximum": values[-1] if values else None,
                }
            )
        counts = {
            status: sum(r["status"] == status for r in rows)
            for status in ("completed", "failed", "canceled")
        }
        result.append(
            {
                "group_id": identity,
                "evidence_scope": "observed_task_group",
                "conditions": dict(rows[0]["conditions"]),
                "run_count": len(rows),
                "completed_count": counts["completed"],
                "failed_count": counts["failed"],
                "canceled_count": counts["canceled"],
                "incomplete_count": len(rows) - sum(counts.values()),
                "accepted_count": sum(r["accepted"] is True for r in rows),
                "rejected_count": sum(r["accepted"] is False for r in rows),
                "acceptance_unknown_count": sum(r["accepted"] is None for r in rows),
                "retained_count": sum(r["preference"] == "retained" for r in rows),
                "declined_count": sum(r["preference"] == "declined" for r in rows),
                "preference_unknown_count": sum(r["preference"] is None for r in rows),
                "substituted_count": sum(r["substituted"] for r in rows),
                "applied_unknown_count": sum(r["applied_unknown"] for r in rows),
                "metrics": summaries,
                "observation_refs": sorted(r["observation_ref"] for r in rows),
                "sources": [r["source"] for r in rows],
            }
        )
    return result


def assess_objectives(
    groups: Sequence[Mapping[str, Any]], objectives: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    return [
        {
            "objective": dict(objective),
            "classification": "insufficient_evidence",
            "group_ids": sorted(g["group_id"] for g in groups),
            "reason": "Observed task groups retain measured outcomes only. No counterfactual, whole-skill, cross-domain or policy promotion claim is supported.",
        }
        for objective in objectives
    ]
