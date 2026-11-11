import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest

from jevdrill.analysis import aggregate_observations, assess_objectives
from jevdrill.application import Application
from jevdrill.contracts import ContractError, canonical_digest, parse_contract
from jevdrill.storage import SQLiteStorage


def case(tmp_path, discovery_inputs=None, project=None):
    app = Application(SQLiteStorage(tmp_path / "route.db"))
    base = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]
    base["request"]["active_guidance"] = []
    base["request"]["task_id"] = str(uuid4())
    base["request"]["envelope"].update(request_id=str(uuid4()), idempotency_key=str(uuid4()))
    base["settings_layers"] = [{"source": "request", "values": {"local_analysis_enabled": True}}]
    base["inventory"]["candidates"][0]["guidance_options"] = []
    if project:
        base["request"]["envelope"]["project_id"] = project
    linkage = None
    if discovery_inputs:
        discovery_inputs = copy.deepcopy(discovery_inputs)
        discovery_inputs["catalog"]["resources"] = []
        discovery_inputs["descriptions"] = []
        result = app.discover(discovery_inputs)
        linkage = {
            k: result["details"][k] for k in ("discovery_id", "work_objective_id", "trace_digest")
        }
        base["request"]["envelope"]["project_id"] = discovery_inputs["envelope"]["project_id"]
        base["request"]["envelope"]["workspace_id"] = discovery_inputs["envelope"]["workspace_id"]
        base["request"]["envelope"]["harness_id"] = discovery_inputs["envelope"]["harness_id"]
        base["request"]["hard_constraints"] = discovery_inputs["hard_constraints"]
        base["catalog"] = discovery_inputs["catalog"]
        routed = app.route({"schema_version": "2", "route_inputs": base, "discovery_ref": linkage})
    else:
        routed = app.route(base)
    assert routed["status"] == "ready"
    envelope = base["request"]["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "route",
    }
    context = {
        "task_id": base["request"]["task_id"],
        "routing_decision_id": routed["details"]["routing_decision_id"],
        "discovery_ref": linkage,
        "task_family": "implementation",
        "task_group": "parser",
        "environment_revision": "native-v1",
        "isolation_revision": "temp-v1",
        "evaluator_ref": "checks-v1",
        "rubric_revision": "v1",
        "local_analysis_enabled": True,
        "share_user_wide": False,
    }
    app.storage.deadline = None
    app.storage.record_learning_context(scope, context)
    return app, scope, context, routed


def report(app, scope, context, run, payload, sequence=1, supersedes=None):
    event = {
        "schema_version": "1",
        "event_id": str(uuid4()),
        "task_id": context["task_id"],
        "routing_decision_id": context["routing_decision_id"],
        "execution_run_id": run,
        "source_id": "synthetic-host",
        "source_sequence": sequence,
        "occurred_at": "2026-10-09T00:00:00Z",
        "supersedes_event_id": supersedes,
        "payload": payload,
    }
    parse_contract("ExecutionEvent", event)
    result = app.storage.ingest_report(
        dict(scope, operation="report"), event["event_id"], canonical_digest(event), event
    )
    assert result["status"] == "accepted"
    return event


def measurement(value=12, version="v1", unit="tokens"):
    return {
        "metric_id": "input_tokens",
        "metric_version": version,
        "measurement_value": {"kind": "known", "value": value, "unit": unit},
        "source": "host",
        "method": "direct-v1",
        "scope": "run",
        "counting_semantics": "disjoint",
        "parent_metric_id": None,
    }


def test_missing_failed_canceled_corrected_and_unknown_observations(tmp_path):
    app, scope, context, decision = case(tmp_path)
    initial = aggregate_observations(app.storage.learning_observations(scope))[0]
    assert initial["incomplete_count"] == 1 and initial["metrics"] == []
    run = str(uuid4())
    report(
        app,
        scope,
        context,
        run,
        {
            "kind": "lifecycle",
            "event_type": "plan_applied",
            "applied_plan_id": decision["execution_plan"]["execution_plan_id"],
            "reason": None,
        },
    )
    done = report(
        app,
        scope,
        context,
        run,
        {"kind": "lifecycle", "event_type": "completed", "applied_plan_id": None, "reason": None},
        2,
    )
    unknown = measurement()
    unknown["measurement_value"] = {"kind": "unknown", "reason": "not_reported"}
    report(app, scope, context, run, {"kind": "usage", "measurements": [measurement(), unknown]}, 3)
    report(
        app,
        scope,
        context,
        run,
        {
            "kind": "lifecycle",
            "event_type": "failed",
            "applied_plan_id": None,
            "reason": "measured failure",
        },
        4,
        done["event_id"],
    )
    report(
        app,
        scope,
        context,
        str(uuid4()),
        {"kind": "lifecycle", "event_type": "canceled", "applied_plan_id": None, "reason": None},
        5,
    )
    groups = aggregate_observations(app.storage.learning_observations(scope))
    assert sum(g["failed_count"] for g in groups) == 1
    assert sum(g["canceled_count"] for g in groups) == 1
    assert sum(g["completed_count"] for g in groups) == 0
    known = [m for g in groups for m in g["metrics"] if m["sample_count"]]
    missing = [m for g in groups for m in g["metrics"] if m["missing_count"]]
    assert known[0]["mean"] == 12 and missing[0]["mean"] is None
    assert missing[0]["metric_definition"]["measurement_value"]["kind"] == "unknown"
    with app.storage._connect() as c:
        assert c.execute("SELECT count(*) FROM events_v1").fetchone()[0] == 5


def test_substitution_preference_and_evaluation_are_distinct(tmp_path):
    app, scope, context, decision = case(tmp_path)
    run = str(uuid4())
    report(
        app,
        scope,
        context,
        run,
        {
            "kind": "lifecycle",
            "event_type": "plan_applied",
            "applied_plan_id": str(uuid4()),
            "reason": "host substitution",
        },
    )
    report(
        app,
        scope,
        context,
        run,
        {"kind": "host_choice", "selected_run_id": str(uuid4()), "reason": "decline"},
        2,
    )
    report(
        app,
        scope,
        context,
        run,
        {
            "kind": "evaluation",
            "evaluator_ref": "checks-v1",
            "rubric_revision": "v1",
            "check_results": {"test": False},
            "measurements": [],
        },
        3,
    )
    group = aggregate_observations(app.storage.learning_observations(scope))[0]
    assert group["substituted_count"] == group["declined_count"] == group["rejected_count"] == 1
    assert group["conditions"]["applied_configuration"] == "unknown"
    assert group["conditions"]["applied_configuration_reason"] == "different_plan"
    assert group["evidence_scope"] == "observed_task_group"
    objectives = [
        decision["details"]["optimization_objective"],
        dict(decision["details"]["optimization_objective"], version="v2", direction="maximize"),
    ]
    assessments = assess_objectives([group], objectives)
    assert [a["objective"]["version"] for a in assessments] == [objectives[0]["version"], "v2"]
    assert all(a["classification"] == "insufficient_evidence" for a in assessments)


def test_terminal_applied_ids_corrections_and_unrelated_runs_remain_authoritative(tmp_path):
    app, scope, context, decision = case(tmp_path)
    selected = decision["execution_plan"]["execution_plan_id"]
    run, other = str(uuid4()), str(uuid4())
    done = report(
        app,
        scope,
        context,
        run,
        {
            "kind": "lifecycle",
            "event_type": "completed",
            "applied_plan_id": selected,
            "reason": None,
        },
    )
    report(
        app,
        scope,
        context,
        other,
        {
            "kind": "lifecycle",
            "event_type": "completed",
            "applied_plan_id": None,
            "reason": None,
        },
    )
    observations = app.storage.learning_observations(scope)
    by_run = {r["source"]["execution_run_id"]: r for r in observations}
    assert by_run[run]["conditions"]["applied_configuration_reason"] == "reported_selected_plan"
    assert by_run[other]["conditions"]["applied_configuration_reason"] == "not_reported"
    report(
        app,
        scope,
        context,
        run,
        {
            "kind": "lifecycle",
            "event_type": "completed",
            "applied_plan_id": str(uuid4()),
            "reason": "corrected identity",
        },
        2,
        done["event_id"],
    )
    groups = aggregate_observations(app.storage.learning_observations(scope))
    assert {g["conditions"]["applied_configuration_reason"] for g in groups} == {
        "different_plan",
        "not_reported",
    }
    assert all(g["conditions"]["applied_configuration"] == "unknown" for g in groups)


@pytest.mark.parametrize(
    "dimension",
    [
        "task_family",
        "task_group",
        "environment_revision",
        "isolation_revision",
        "evaluator_ref",
        "rubric_revision",
    ],
)
def test_incompatible_contexts_never_aggregate_across_domains(tmp_path, dimension):
    app, scope, _context, _ = case(tmp_path)
    observations = app.storage.learning_observations(scope)
    other = copy.deepcopy(observations[0])
    other["conditions"][dimension] = "different"
    assert len(aggregate_observations(observations + [other])) == 2


def test_metric_revisions_units_methods_remain_separate(tmp_path):
    app, scope, context, _ = case(tmp_path)
    report(
        app,
        scope,
        context,
        str(uuid4()),
        {
            "kind": "usage",
            "measurements": [
                measurement(),
                measurement(version="v2"),
                measurement(unit="bytes"),
                dict(measurement(), method="estimate-v2"),
            ],
        },
    )
    group = aggregate_observations(app.storage.learning_observations(scope))[0]
    assert len(group["metrics"]) == 4


def test_source_digest_recheck_prevents_deleted_analysis_commit(tmp_path):
    app, scope, context, decision = case(tmp_path)
    observations = app.storage.learning_observations(scope)
    digest = canonical_digest(observations)
    evidence = {
        "schema_version": "1",
        "status": "updated",
        "source_digest": digest,
        "evidence_revision": "v1",
        "groups": aggregate_observations(observations),
        "assessments": [],
        "objective_history": [decision["details"]["optimization_objective"]],
    }
    app.storage.delete_task(scope, context["task_id"])
    with pytest.raises(ContractError, match="sources changed"):
        app.storage.save_evidence(scope, evidence, 100, digest, False)
    assert app.storage.latest_evidence(scope) is None


def test_no_guidance_discoveries_keep_authoritative_boundaries_despite_forged_family_labels(
    tmp_path, discovery_inputs
):
    app, scope, context, _ = case(tmp_path, discovery_inputs)
    second = copy.deepcopy(discovery_inputs)
    second["work_objective_id"] = str(uuid4())
    second["envelope"]["idempotency_key"] = str(uuid4())
    app, other_scope, other_context, _ = case(tmp_path, second)
    assert scope == other_scope
    groups = aggregate_observations(app.storage.learning_observations(scope))
    assert len(groups) == 2
    assert (
        groups[0]["conditions"]["selected_configuration"]
        == groups[1]["conditions"]["selected_configuration"]
    )
    assert all(g["conditions"]["discovery_status"] == "no_optional_guidance" for g in groups)
    assert {g["sources"][0]["discovery_ref"]["work_objective_id"] for g in groups} == {
        context["discovery_ref"]["work_objective_id"],
        other_context["discovery_ref"]["work_objective_id"],
    }
