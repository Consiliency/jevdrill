import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from jevdrill.analysis import PolicyLifecycle
from jevdrill.contracts import canonical_digest
from jevdrill.storage import SQLiteStorage
from tests.experiments.test_execution import seed_task


class Evidence:
    def __init__(self):
        self.calls = 0
        self.change = lambda evaluation: None
        self.health = {}
        self.before_evaluate = lambda: None

    def prepare(self, definition):
        return {
            "schema_version": "1",
            "definition_digest": canonical_digest(definition),
            "evaluator_identity": "independent-fixture",
            "independent": True,
            "input_revision": "frozen-data",
            "valid_until": "2099-01-01T00:00:00Z",
            "status": self.health.get(definition["policy_revision"], "current"),
            "evidence_ref": "fixture-check",
        }

    def evaluate(self, definition, exposed_at):
        self.calls += 1
        self.before_evaluate()
        calibration = definition["calibration"]
        metric = {
            "metric_id": "raw_token_cost",
            "metric_version": "1",
            "source": "provider",
            "method": "fixture",
            "scope": "task",
            "counting_semantics": "disjoint",
            "parent_metric_id": None,
        }
        evaluation = {
            "schema_version": "1",
            "identities_blinded": True,
            "evidence_origin": "controlled",
            "calibration": calibration,
            **{
                k: calibration[k]
                for k in ("task_family", "evaluator_ref", "rubric_revision", "dataset_revision")
            },
            "cases": [
                {
                    "case_id": c["case_id"],
                    "related_group": c["related_group"],
                    "split": c["split"],
                    "exposed_at": exposed_at,
                    "baseline_quality": 1.0,
                    "candidate_quality": 1.0,
                    "baseline_critical": {"authorization": True},
                    "candidate_critical": {"authorization": True},
                    "baseline_measurements": [
                        metric | {"measurement_value": {"kind": "known", "value": 1, "unit": "USD"}}
                    ],
                    "candidate_measurements": [
                        metric | {"measurement_value": {"kind": "known", "value": 0, "unit": "USD"}}
                    ],
                }
                for c in definition["cases"]
            ],
        }
        self.change(evaluation)
        return evaluation


@pytest.fixture
def setup(tmp_path):
    scope = {
        "project_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "producer": "fixture",
        "operation": "route",
    }
    definition = {
        "schema_version": "1",
        "policy_revision": "one",
        "baseline_policy_revision": "execution-ceilings-v1",
        "task_group": "development-fixture",
        "objective": {
            "objective_id": "cost",
            "version": "1",
            "metric_id": "raw_token_cost",
            "direction": "minimize",
            "routing_cost_basis": "raw",
            "acceptance_requirements": [],
        },
        "candidate_order": [
            {"candidate_id": "a", "candidate_fingerprint": "a" * 64},
            {"candidate_id": "b", "candidate_fingerprint": "b" * 64},
        ],
        "calibration": {
            "schema_version": "1",
            "calibration_revision": "fixture-only",
            "task_family": "review",
            "evaluator_ref": "fixture",
            "rubric_revision": "fixture",
            "dataset_revision": "fixture",
            "calibration_source": "synthetic-control",
            "frozen_at": "2026-01-01T00:00:00Z",
            "critical_requirements": ["authorization"],
            "quality_floor": 0.7,
            "maximum_quality_loss": 0.4,
            "minimum_pairs": 100,
            "confidence": 0.95,
        },
        "cases": [
            {
                "case_id": str(i),
                "related_group": str(i),
                "task_id": str(uuid4()),
                "split": "policy_holdout" if i < 100 else "policy_regression",
            }
            for i in range(200)
        ],
        "objective_value_ceiling": 1.0,
        "minimum_improvement": 0.1,
    }
    authority = {
        "schema_version": "1",
        "authorization_revision": "owner",
        "scope": scope,
        "enabled": True,
        "allowed_task_groups": ["development-fixture"],
        "allowed_policy_revisions": ["one", "two"],
        "max_routes": 2,
        "rollout_basis_points": 10000,
        "expires_at": "2099-01-01T00:00:00Z",
    }
    now = [datetime(2026, 1, 2, tzinfo=UTC)]
    evidence = Evidence()
    service = PolicyLifecycle(
        SQLiteStorage(tmp_path / "db"), lambda _: authority, evidence, lambda: now[0]
    )
    for case in definition["cases"]:
        seed_task(service.storage, scope, case["task_id"])
    request = {
        "schema_version": "1",
        "scope": scope,
        "policy_revision": "one",
        "action": "register",
        "definition": definition,
    }
    return service, request, authority, evidence, now


def action(service, request, name):
    return service.handle(request | {"action": name, "definition": None})


def evaluate(setup):
    service, request, _, _, now = setup
    assert service.handle(request)["status"] == "recorded"
    now[0] += timedelta(seconds=1)
    return action(service, request, "evaluate")


def ordering(service, request, identity=None):
    definition = request["definition"]
    return service.ordering(
        request["scope"],
        definition["task_group"],
        definition["objective"],
        identity or str(uuid4()),
        str(uuid4()),
    )


def test_frozen_exposure_precedes_evaluator_and_cannot_be_repeated(setup):
    service, request, _, evidence, _ = setup

    def inspect():
        saved = action(service, request, "inspect")["record"]
        assert saved["policy_status"] == "exposed" and saved["evaluation"] is None

    evidence.before_evaluate = inspect
    evaluated = evaluate(setup)
    assert evaluated["record"]["assessment"]["classification"] == "quality_gate_passed"
    assert evaluated["record"]["reasons"] == []
    assert action(service, request, "evaluate")["status"] == "denied"
    assert evidence.calls == 1


def test_grant_required_and_bounded_routes_survive_restart(setup):
    service, request, authority, evidence, now = setup
    evaluate(setup)
    authority["enabled"] = False
    assert action(service, request, "promote")["status"] == "denied"
    authority["enabled"] = True
    assert action(service, request, "promote")["record"]["policy_status"] == "active"
    identity = str(uuid4())
    assert ordering(service, request, identity)["status"] == "ready"
    assert ordering(service, request, identity)["status"] == "ready"
    resumed = PolicyLifecycle(
        SQLiteStorage(service.storage.path), lambda _: authority, evidence, lambda: now[0]
    )
    assert ordering(resumed, request)["status"] == "ready"
    assert ordering(resumed, request)["status"] == "blocked"
    assert action(resumed, request, "inspect")["record"]["used_routes"] == 2


@pytest.mark.parametrize(
    "change,reason",
    [
        (
            lambda e: e["cases"][0]["candidate_critical"].update(authorization=False),
            "new_critical_failure",
        ),
        (lambda e: e.update(identities_blinded=False), "evaluation_not_blinded"),
        (lambda e: e.update(evidence_origin="synthetic"), "controlled_evidence_required"),
        (lambda e: e["cases"][0].update(candidate_quality=None), "quality_observation_missing"),
        (
            lambda e: e["cases"][0].update(candidate_measurements=[]),
            "policy_objective_measurement_missing",
        ),
        (
            lambda e: e["cases"][0]["candidate_measurements"][0]["measurement_value"].update(
                value=2
            ),
            "policy_objective_bound_exceeded",
        ),
    ],
)
def test_negative_evidence_cannot_promote(setup, change, reason):
    service, request, _, evidence, _ = setup
    evidence.change = change
    result = evaluate(setup)
    assert reason in result["record"]["reasons"]
    assert action(service, request, "promote")["status"] == "denied"


@pytest.mark.parametrize(
    "change",
    [
        lambda e: e["cases"][0].update(exposed_at="2025-01-01T00:00:00Z"),
        lambda e: e["cases"][0].update(case_id="other"),
        lambda e: e["calibration"].update(quality_floor=0.0),
    ],
)
def test_evaluator_cannot_change_frozen_inputs(setup, change):
    service, request, _, evidence, _ = setup
    evidence.change = change
    assert evaluate(setup)["status"] == "denied"
    assert action(service, request, "inspect")["record"]["policy_status"] == "exposed"
    assert action(service, request, "evaluate")["status"] == "denied"


def test_crash_after_exposure_does_not_rerun_evaluator(setup):
    service, request, _, evidence, _ = setup

    def fail():
        raise OSError("lost result")

    evidence.before_evaluate = fail
    assert evaluate(setup)["reasons"] == ["policy_evaluator_unavailable"]
    assert action(service, request, "evaluate")["status"] == "denied"
    assert evidence.calls == 1


def test_reusing_related_holdout_groups_for_new_revision_is_rejected(setup):
    service, request, _, evidence, now = setup
    evaluate(setup)
    second = copy.deepcopy(request)
    second["policy_revision"] = second["definition"]["policy_revision"] = "two"
    assert service.handle(second)["status"] == "recorded"
    now[0] += timedelta(seconds=1)
    assert action(service, second, "evaluate")["reasons"] == ["policy_holdout_already_exposed"]
    assert evidence.calls == 1


def test_deleted_supporting_data_invalidates_active_policy(setup):
    service, request, _, _, _ = setup
    evaluate(setup)
    action(service, request, "promote")
    service.storage.delete_task(request["scope"], request["definition"]["cases"][0]["task_id"])
    record = action(service, request, "inspect")["record"]
    assert record["policy_status"] == "stale" and record["evaluation"] is None
    assert record["reasons"] == ["supporting_data_deleted"]
    assert ordering(service, request)["status"] == "blocked"


def test_deletion_during_evaluation_cannot_restore_evidence(setup):
    service, request, _, evidence, _ = setup
    evidence.before_evaluate = lambda: service.storage.delete_task(
        request["scope"], request["definition"]["cases"][0]["task_id"]
    )
    assert evaluate(setup)["status"] == "denied"
    assert action(service, request, "inspect")["record"]["evaluation"] is None


def test_regression_restores_only_current_verified_previous_policy(setup):
    service, request, _, evidence, now = setup
    evaluate(setup)
    action(service, request, "promote")
    second = copy.deepcopy(request)
    second["policy_revision"] = second["definition"]["policy_revision"] = "two"
    second["definition"]["baseline_policy_revision"] = "one"
    for case in second["definition"]["cases"]:
        case["related_group"] += "-new"
    assert service.handle(second)["status"] == "recorded"
    now[0] += timedelta(seconds=1)
    assert action(service, second, "evaluate")["status"] == "recorded"
    assert action(service, second, "promote")["record"]["policy_status"] == "active"
    evidence.health["two"] = "critical_regression"
    selected = ordering(service, second)
    assert selected["status"] == "ready" and selected["policy_revision"] == "one"
    assert action(service, second, "inspect")["record"]["policy_status"] == "suspended"
    evidence.health["one"] = "stale"
    assert ordering(service, request)["status"] == "blocked"


def test_concurrent_routes_cannot_exceed_rollout_cap(setup):
    service, request, authority, _, _ = setup
    evaluate(setup)
    authority["max_routes"] = 1
    action(service, request, "promote")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: ordering(service, request), range(2)))
    assert sorted(r["status"] for r in results) == ["blocked", "ready"]


def test_no_configured_evaluator_cannot_register_or_self_authorize(setup):
    service, request, _, _, _ = setup
    assert PolicyLifecycle(service.storage).handle(request)["reasons"] == [
        "policy_independent_evaluator_unavailable"
    ]


@pytest.mark.parametrize("field", ["producer", "operation"])
def test_promotion_authority_cannot_cross_declared_scope(setup, field):
    service, request, authority, _, _ = setup
    evaluate(setup)
    authority["scope"] = dict(
        authority["scope"], **{field: "report" if field == "operation" else "other"}
    )
    assert action(service, request, "promote")["reasons"] == ["policy_promotion_not_authorized"]


def test_optout_only_invalidates_policies_using_the_affected_task(setup):
    service, request, _, _, _ = setup
    evaluate(setup)
    action(service, request, "promote")
    another = copy.deepcopy(request)
    another["policy_revision"] = another["definition"]["policy_revision"] = "unrelated"
    another["definition"]["task_group"] = "unrelated"
    for case in another["definition"]["cases"]:
        case["task_id"] = str(uuid4())
        seed_task(service.storage, request["scope"], case["task_id"])
    assert service.handle(another)["status"] == "recorded"
    service.storage.restrict_learning(
        request["scope"], request["definition"]["cases"][0]["task_id"], False
    )
    assert action(service, request, "inspect")["record"]["policy_status"] == "stale"
    assert action(service, another, "inspect")["record"]["policy_status"] == "registered"
    assert ordering(service, request)["status"] == "blocked"
