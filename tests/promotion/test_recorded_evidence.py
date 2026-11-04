import copy
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from jevdrill.analysis import PolicyLifecycle, RecordedPolicyEvidence, RecordedPolicyStudy
from jevdrill.contracts import ContractError, canonical_digest
from jevdrill.integrations.development import IndependentDevelopmentGrader
from jevdrill.routing import candidate_fingerprint
from tests.experiments.test_development import (
    development as development,  # noqa: PLC0414 -- pytest fixture
)
from tests.experiments.test_development import (
    provider as provider,  # noqa: PLC0414 -- pytest fixture
)
from tests.experiments.test_development import setup as setup  # noqa: PLC0414 -- pytest fixture
from tests.experiments.test_execution import seed_task


@pytest.fixture
def recorded(development, request):
    execution, worker, original, proposal, authority, _ticks, provider_state = development
    mode = getattr(request, "param", False)
    runtime_grader = mode in ("runtime_good", "runtime_bad")
    if runtime_grader:
        assert os.environ.get("JEVDRILL_DEVELOPMENT_IMAGE"), "Explicit real Linux image required"
    assignments, comparisons, requests = [], {}, []
    exercises = [
        ("maximum", "Math.max(a, b)", [3, 1]),
        ("minimum", "Math.min(a, b)", [3, 4]),
        ("difference", "a - b", [5, 2]),
    ]
    for index in range(4):
        following = copy.deepcopy(proposal)
        experiment = following["proposal"]["experiment"]
        if index:
            following["idempotency_key"] = str(uuid4())
            experiment["comparison_experiment_id"] = str(uuid4())
            experiment["task_id"] = str(uuid4())
            authority["task_ids"].append(experiment["task_id"])
            case = copy.deepcopy(worker.cases[experiment["context_ref"]])
            name, _expression, inputs = exercises[index - 1]
            case["prompt"] = "Define solve(a, b) returning their " + name + "."
            case["inputs"] = [inputs]
            experiment["context_ref"] = name
            experiment["context_hash"] = canonical_digest(case)
            worker.cases[name] = case
            seed_task(execution.storage, original["scope"], experiment["task_id"])
            execution.handle(following)
        assignment = {
            "case_id": str(index),
            "related_group": "synthetic-group-" + str(index),
            "task_id": experiment["task_id"],
            "split": "policy_holdout" if index < 2 else "policy_regression",
        }
        assignments.append(assignment)
        comparisons[str(index)] = {
            "assignment": assignment,
            "comparison_experiment_id": experiment["comparison_experiment_id"],
            "experiment_digest": canonical_digest(experiment),
            "baseline_plan": experiment["candidate_plans"][0],
            "candidate_plan": experiment["candidate_plans"][1],
            "artifacts_digest": "sealed-after-execution",
        }
        requests.append(
            original | {"comparison_experiment_id": experiment["comparison_experiment_id"]}
        )
    definition = {
        "schema_version": "1",
        "policy_revision": "recorded-v1",
        "baseline_policy_revision": "execution-ceilings-v1",
        "task_group": "synthetic",
        "objective": {
            "objective_id": "cost",
            "version": "1",
            "metric_id": "raw_token_cost",
            "direction": "minimize",
            "routing_cost_basis": "raw",
            "acceptance_requirements": [],
        },
        "candidate_order": [
            {"candidate_id": str(i), "candidate_fingerprint": candidate_fingerprint(p)}
            for i, p in enumerate(
                [comparisons["0"]["candidate_plan"], comparisons["0"]["baseline_plan"]]
            )
        ],
        "calibration": {
            "schema_version": "1",
            "calibration_revision": "synthetic-only",
            "task_family": "implementation",
            "evaluator_ref": "development-js-v1",
            "rubric_revision": "1",
            "dataset_revision": "synthetic-stored-v1",
            "calibration_source": "synthetic-controls",
            "frozen_at": "1970-01-01T00:00:00Z",
            "critical_requirements": ["answers_match" if runtime_grader else "independent-test"],
            "quality_floor": 0.7,
            "maximum_quality_loss": 0.1,
            "minimum_pairs": 100,
            "confidence": 0.95,
        },
        "cases": assignments,
        "objective_value_ceiling": 1.0,
        "minimum_improvement": 0.1,
    }
    grader = None
    if runtime_grader:
        recipes = {
            canonical_digest([definition["calibration"]["dataset_revision"], str(index)]): {
                "inputs": case["inputs"],
                "expected_answers": case["expected_answers"],
            }
            for index, case in enumerate(worker.cases.values())
        }
        grader = IndependentDevelopmentGrader(
            recipes,
            container=worker.container,
            lock_path=worker.path.parent / "grader.lock",
            duration_ms=10_000,
            authorize=lambda key: key in recipes,
        )
    study = RecordedPolicyStudy(
        definition,
        comparisons,
        "1970-01-01T00:00:01Z",
        "2099-01-01T00:00:00Z",
        grader.revision if grader else "local-blind-grader-v1",
        "synthetic",
    )
    execution.storage.freeze_policy_study(original["scope"], RecordedPolicyEvidence.protocol(study))
    if mode:
        complete = worker._complete

        def contrasted(prompt, profile, deadline):
            expression = "0" if profile.model_revision.endswith("1") else "a + b"
            if runtime_grader:
                expressions = {"sum": "a + b", **{name: expr for name, expr, _ in exercises}}
                expression = next(
                    expr for name, expr in expressions.items() if f"their {name}." in prompt
                )
                if mode == "runtime_bad" and profile.model_revision.endswith("1"):
                    expression = "0"
            provider_state["body"]["choices"][0]["message"]["content"] = (
                "function solve(a, b) { return " + expression + "; }"
            )
            return complete(prompt, profile, deadline)

        worker._complete = contrasted
    for index, execution_request in enumerate(requests):
        result = execution.execute(execution_request)
        assert result["status"] == "recorded", result
        started = execution.execute(execution_request | {"action": "advance"})["record"]
        if index:
            provider_state["body"]["choices"][0]["message"]["content"] = (
                "function solve(a, b) { return " + exercises[index - 1][1] + "; }"
            )
        assert worker.run(started)["host_status"] == "completed"
        record = execution.execute(execution_request | {"action": "advance"})["record"]
        comparisons[str(index)]["artifacts_digest"] = canonical_digest(
            worker.retained_observations(record)
        )
    calls, history = [], {c["related_group"]: "unexposed" for c in assignments}

    def grade(case_id, outputs):
        calls.append((case_id, copy.deepcopy(outputs)))
        if grader:
            assert (
                execution.storage.policy_records(original["scope"])[0]["policy_status"] == "exposed"
            )
            return grader.grade(case_id, outputs)
        return [{"quality": 1.0, "critical": {"independent-test": True}} for _ in outputs]

    def build(source=study, scope=None):
        return RecordedPolicyEvidence(
            execution.storage,
            scope or original["scope"],
            [source],
            artifacts=worker.retained_observations,
            grade=grade,
            grader_revision=lambda: grader.revision if grader else study.evaluator_identity,
            exposure_history=lambda dataset, groups: dict(history),
        )

    clock = [datetime(2026, 1, 1, tzinfo=UTC)]
    lifecycle = PolicyLifecycle(execution.storage, evidence=build(), clock=lambda: clock[0])
    policy_request = {
        "schema_version": "1",
        "scope": original["scope"],
        "policy_revision": definition["policy_revision"],
        "action": "register",
        "definition": definition,
    }
    return (
        lifecycle,
        policy_request,
        study,
        build,
        calls,
        history,
        clock,
        execution,
        worker,
        provider_state,
    )


def evaluate(recorded):
    service, request, _, _, _, _, clock, *_ = recorded
    registered = service.handle(request)
    assert registered["status"] == "recorded", registered
    clock[0] += timedelta(seconds=1)
    return service.handle(request | {"action": "evaluate", "definition": None})


def test_recorded_evaluator_binds_real_durable_comparisons_without_new_calls(recorded):
    service, request, _, _, calls, _, _, execution, _, provider_state = recorded
    before = len(provider_state["requests"])
    preparation = service.evidence.prepare(request["definition"])
    assert calls == [] and "cases" not in preparation
    result = evaluate(recorded)
    assert result["record"]["policy_status"] == "evaluated", result
    assert result["record"]["assessment"]["reasons"] == ["controlled_evidence_required"]
    assert result["record"]["evaluation"]["evidence_origin"] == "synthetic"
    assert len(calls) == 4 and len(provider_state["requests"]) == before == 8
    for case in result["record"]["evaluation"]["cases"]:
        assert case["baseline_quality"] == case["candidate_quality"] == 1
        assert case["baseline_measurements"][0]["source"] == "direct"
    assert all(isinstance(output, str) for _, outputs in calls for output in outputs)
    assert "requested_model" not in str(calls)
    assert all(r["exposed_at"] for r in execution.storage.policy_records(request["scope"]))
    assert service.handle(request | {"action": "promote", "definition": None})["status"] == "denied"


def test_evaluation_requires_durable_exposure(recorded):
    service, request, *_ = recorded
    with pytest.raises(ContractError, match="policy_durable_exposure_missing"):
        service.evidence.evaluate(request["definition"], "2026-01-01T00:00:00Z")


@pytest.mark.parametrize(
    "field,value",
    [
        ("baseline_policy_revision", "other"),
        ("task_group", "other"),
        ("candidate_order", []),
    ],
)
def test_request_cannot_change_trusted_selection(recorded, field, value):
    service, request, *_ = recorded
    definition = copy.deepcopy(request["definition"])
    definition[field] = value
    with pytest.raises(ContractError, match="policy_study_binding_mismatch"):
        service.evidence.prepare(definition)


@pytest.mark.parametrize("value", ["development", "another-dataset-alias", None])
def test_external_exposure_and_unknown_history_are_rejected(recorded, value):
    service, request, _, _, calls, history, *_ = recorded
    if value is None:
        history.clear()
    else:
        history[next(iter(history))] = value
    result = service.handle(request)
    assert result["reasons"] == ["policy_external_exposure_unverified"]
    assert calls == []


def test_cannot_freeze_a_protocol_after_comparisons_ran(recorded):
    _, request, study, _, _, _, _, execution, *_ = recorded
    definition = copy.deepcopy(study.definition)
    definition["policy_revision"] = "post-hoc"
    with pytest.raises(ContractError, match="policy_study_must_precede_execution"):
        execution.storage.freeze_policy_study(
            request["scope"], RecordedPolicyEvidence.protocol(replace(study, definition=definition))
        )


def test_cross_scope_and_changed_protocol_are_rejected(recorded):
    _, request, study, build, *_ = recorded
    with pytest.raises(ContractError, match="policy_frozen_protocol_missing_or_changed"):
        build(scope=request["scope"] | {"workspace_id": str(uuid4())}).prepare(study.definition)
    with pytest.raises(ContractError, match="policy_grader_revision_mismatch"):
        build(replace(study, evaluator_identity="changed-grader")).prepare(study.definition)


def test_deleted_source_cannot_be_reclassified_or_refrozen(recorded):
    service, request, study, _, _, _, _, execution, *_ = recorded
    execution.storage.delete_task(request["scope"], study.definition["cases"][0]["task_id"])
    assert service.handle(request)["status"] == "denied"
    with pytest.raises(ContractError, match="policy_task_deleted"):
        execution.storage.freeze_policy_study(
            request["scope"], RecordedPolicyEvidence.protocol(study)
        )


def test_deletion_during_independent_grading_discards_results(recorded):
    service, request, study, _, _, _, _, execution, *_ = recorded
    original = service.evidence.grade

    def deleted(case_id, outputs):
        execution.storage.delete_task(request["scope"], study.definition["cases"][0]["task_id"])
        return original(case_id, outputs)

    service.evidence.grade = deleted
    result = evaluate(recorded)
    assert result["status"] == "denied"
    current = execution.storage.policy_records(request["scope"])[0]
    assert current["policy_status"] == "stale" and current["evaluation"] is None


def test_grader_failure_is_not_repeated_after_restart(recorded):
    service, request, _, _, calls, _, clock, execution, *_ = recorded

    def failed(case_id, outputs):
        calls.append(case_id)
        raise OSError("grader failed")

    service.evidence.grade = failed
    result = evaluate(recorded)
    assert result["reasons"] == ["policy_evaluator_unavailable"]
    restarted = PolicyLifecycle(
        execution.storage, evidence=service.evidence, clock=lambda: clock[0]
    )
    assert restarted.handle(request | {"action": "evaluate", "definition": None})["reasons"] == [
        "policy_exposure_cannot_be_repeated"
    ]
    assert len(calls) == 1


@pytest.mark.parametrize("bad", [None, [], [{"quality": 1, "critical": {}}], [1, 2]])
def test_malformed_grader_results_are_rejected(recorded, bad):
    service, *_ = recorded
    service.evidence.grade = lambda *_: bad
    assert evaluate(recorded)["reasons"] == ["policy_grader_result_invalid"]


def test_changed_sealed_artifacts_cannot_be_graded(recorded):
    service, request, _, _, calls, *_ = recorded
    original = service.evidence.artifacts

    def changed(record):
        artifact = original(record)
        artifact["observations"][0]["output"] = "tampered"
        return artifact

    service.evidence.artifacts = changed
    assert service.handle(request)["reasons"] == ["policy_artifacts_changed"]
    assert calls == []


@pytest.mark.parametrize("recorded", [True], indirect=True)
def test_independent_grades_preserve_roles_and_veto_critical_failure(recorded):
    service, _, _, _, calls, *_ = recorded

    def grade(case_id, outputs):
        calls.append((case_id, copy.deepcopy(outputs)))
        assert (
            service.storage.policy_records(service.evidence.scope)[0]["policy_status"] == "exposed"
        )
        return [
            {
                "quality": 1.0 if "return 0;" not in output else 0.0,
                "critical": {"independent-test": "return 0;" not in output},
            }
            for output in outputs
        ]

    service.evidence.grade = grade
    result = evaluate(recorded)
    assert result["record"]["assessment"]["classification"] == "critical_regression"
    for case in result["record"]["evaluation"]["cases"]:
        assert case["baseline_quality"] == 1.0 and case["candidate_quality"] == 0.0
    assert len(calls) == 4


def test_cross_dataset_alias_cannot_reuse_exposed_local_groups(recorded):
    service, request, study, _, _, _, _, execution, *_ = recorded
    assert evaluate(recorded)["status"] == "recorded"
    previous = execution.storage.policy_records(request["scope"])[0]
    other = copy.deepcopy(previous)
    other["definition"]["calibration"]["dataset_revision"] = "another-alias"
    other["definition"]["policy_revision"] = "other-study"
    other["definition_digest"] = canonical_digest(other["definition"])
    assert execution.storage.store_policy(request["scope"], other, None)
    with pytest.raises(ContractError, match="policy_related_group_already_exposed"):
        service.evidence.prepare(study.definition)


def test_existing_frozen_protocol_is_idempotent_and_immutable(recorded):
    _, request, study, _, _, _, _, execution, *_ = recorded
    original = RecordedPolicyEvidence.protocol(study)
    execution.storage.freeze_policy_study(request["scope"], original)
    changed = copy.deepcopy(original)
    changed["definition"]["baseline_policy_revision"] = "changed"
    with pytest.raises(ContractError, match="policy_study_already_frozen"):
        execution.storage.freeze_policy_study(request["scope"], changed)


def test_partial_or_changed_receipt_cannot_supply_policy_evidence(recorded):
    service, request, study, _, _, _, _, execution, *_ = recorded
    identity = study.comparisons["0"]["comparison_experiment_id"]
    original = execution.storage.experiment_execution(request["scope"], identity)
    following = copy.deepcopy(original)
    following["record"]["receipt"]["candidates"].pop()
    assert execution.storage.update_experiment_execution(
        request["scope"], identity, original, following
    )
    assert service.handle(request)["reasons"] == ["policy_comparison_incomplete"]


def test_retained_observations_are_copied_and_require_terminal_custody(recorded):
    _, request, study, _, _, _, _, execution, worker, provider_state = recorded
    record = execution.storage.experiment_execution(
        request["scope"], study.comparisons["0"]["comparison_experiment_id"]
    )["record"]
    original = worker.retained_observations(record)
    changed = worker.retained_observations(record)
    changed["observations"][0]["output"] = "caller edit"
    assert worker.retained_observations(record) == original
    with pytest.raises(ContractError, match="development_observations_not_terminal"):
        worker.retained_observations(record | {"execution_status": "running"})
    assert len(provider_state["requests"]) == 8


def test_changed_grader_revision_prevents_exposure(recorded):
    service, request, _, _, calls, *_ = recorded
    assert service.handle(request)["status"] == "recorded"
    service.evidence.grader_revision = lambda: "changed"
    result = service.handle(request | {"action": "evaluate", "definition": None})
    assert result["reasons"] == ["policy_grader_revision_mismatch"]
    assert calls == [] and result["record"]["exposed_at"] is None


def test_incomplete_candidate_preserves_unknown_critical_checks(recorded):
    service, request, study, _, _, _, _, execution, _worker, _ = recorded
    identity = study.comparisons["0"]["comparison_experiment_id"]
    job = execution.storage.experiment_execution(request["scope"], identity)
    following = copy.deepcopy(job)
    following["record"]["execution_status"] = "incomplete"
    following["record"]["receipt"]["host_status"] = "failed"
    following["record"]["receipt"]["candidates"][1]["status"] = "failed"
    assert execution.storage.update_experiment_execution(request["scope"], identity, job, following)
    original = service.evidence.artifacts
    service.evidence.artifacts = lambda record: (
        original(record | {"execution_status": "completed", "receipt": job["record"]["receipt"]})
        if record["comparison_experiment_id"] == identity
        else original(record)
    )
    result = evaluate(recorded)
    assert result["record"]["assessment"]["classification"] == "insufficient_evidence"
    assert result["record"]["assessment"]["critical_regressions"] == []
    row = result["record"]["evaluation"]["cases"][0]
    assert row["candidate_quality"] is None and row["candidate_critical"] == {}
