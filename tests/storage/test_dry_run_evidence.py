"""HOST SL-5: no dry run becomes a learning observation (Consiliency/jevdrill#109).

Every case routes a dry run and, beside it, a real run, gives both the same reports,
and checks the observations in the deciding store and in a fresh store after an
export and an import. Inputs are the committed synthetic route fixture; a judgment
port that fails if called is injected, so no request leaves the runner.
"""

import json
import sqlite3
import time
from pathlib import Path
from uuid import uuid4

import pytest

from jevdrill import routing, storage
from jevdrill.application import Application
from jevdrill.contracts import canonical_digest, parse_contract
from jevdrill.storage import SQLiteStorage

LIFECYCLE = (
    "queued",
    "started",
    "plan_applied",
    "completed",
    "failed",
    "canceled",
    "guidance_deactivated",
)
REPORTS = [f"lifecycle:{name}" for name in LIFECYCLE] + ["usage", "evaluation", "host_choice"]
CASES = [*REPORTS, "none"]  # 11 report sets: every kind and every event_type, and none


class ForbiddenJudge:
    """Stand-in judgment port that fails the test if it is called at all."""

    model_revision = "jev-latest"

    def judge(self, *args):
        raise AssertionError("judgment port called")


def route(app, mode, task=None):
    value = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]
    value["request"].update(task_id=task or str(uuid4()), execution_mode=mode, active_guidance=[])
    value["request"]["envelope"].update(request_id=str(uuid4()), idempotency_key=str(uuid4()))
    value["settings_layers"] = [{"source": "request", "values": {"local_analysis_enabled": True}}]
    value["inventory"]["candidates"][0]["guidance_options"] = []
    result = app.route(value)
    assert result["status"] == "ready"
    envelope = value["request"]["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "route",
    }
    context = {
        "task_id": value["request"]["task_id"],
        "routing_decision_id": result["details"]["routing_decision_id"],
        "discovery_ref": None,
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
    return scope, context, result


def payload(case, decision, run):
    kind, _, name = case.partition(":")
    if kind == "lifecycle":
        applied = (
            decision["execution_plan"]["execution_plan_id"] if name == "plan_applied" else None
        )
        return {"kind": "lifecycle", "event_type": name, "applied_plan_id": applied, "reason": None}
    if kind == "usage":
        value = {"kind": "known", "value": 12, "unit": "tokens"}
        return {
            "kind": "usage",
            "measurements": [
                {
                    "metric_id": "input_tokens",
                    "metric_version": "v1",
                    "measurement_value": value,
                    "source": "host",
                    "method": "direct-v1",
                    "scope": "run",
                    "counting_semantics": "disjoint",
                    "parent_metric_id": None,
                }
            ],
        }
    if kind == "evaluation":
        required = decision["details"]["optimization_objective"]["acceptance_requirements"]
        checks = {row["requirement_id"]: True for row in required} or {"tests": True}
        return {
            "kind": "evaluation",
            "evaluator_ref": "checks-v1",
            "rubric_revision": "v1",
            "check_results": checks,
            "measurements": [],
        }
    return {"kind": "host_choice", "selected_run_id": run, "reason": "synthetic preference"}


def report(store, scope, context, decision, case):
    run = str(uuid4())
    event = {
        "schema_version": "1",
        "event_id": str(uuid4()),
        "task_id": context["task_id"],
        "routing_decision_id": context["routing_decision_id"],
        "execution_run_id": run,
        "source_id": "synthetic-host",
        "source_sequence": 1,
        "occurred_at": "2026-11-22T00:00:00Z",
        "supersedes_event_id": None,
        "payload": payload(case, decision, run),
    }
    parse_contract("ExecutionEvent", event)
    result = store.ingest_report(
        dict(scope, operation="report"), event["event_id"], canonical_digest(event), event
    )
    assert result["status"] == "accepted" and result["durable"] is True


def observed(store, scope, decision_id):
    rows = store.learning_observations(scope)
    return [r for r in rows if r["source"]["routing_decision_id"] == decision_id]


def test_routing_and_storage_share_the_dry_run_code():
    assert routing.DRY_RUN_DIAGNOSTIC == storage.DRY_RUN_DIAGNOSTIC == "dry_run_decision"


@pytest.mark.parametrize("where", ["deciding", "imported"])
@pytest.mark.parametrize("case", CASES)
def test_no_dry_run_becomes_an_observation(tmp_path, case, where):
    app = Application(SQLiteStorage(tmp_path / "route.db"), judgments=ForbiddenJudge())
    scope, dry_context, dry = route(app, "dry_run")
    _, main_context, main = route(app, "main")
    for context, decision in ((dry_context, dry), (main_context, main)):
        if case != "none":
            report(app.storage, scope, context, decision, case)
    store = app.storage
    if where == "imported":
        body = store.export_recovery(scope)
        store = SQLiteStorage(tmp_path / "fresh.db")
        store.import_recovery(scope, body, time.time())
        arrived = store.export_recovery(scope)
        ids = {d["bundle"]["routing_decision_id"] for d in arrived["decisions"]}
        assert {dry_context["routing_decision_id"], main_context["routing_decision_id"]} <= ids
        contexts = {c["routing_decision_id"] for c in arrived["contexts"]}
        assert {dry_context["routing_decision_id"], main_context["routing_decision_id"]} <= contexts
        assert len(arrived["events"]) == len(body["events"]) == (0 if case == "none" else 2)
    assert observed(store, scope, dry_context["routing_decision_id"]) == []
    assert len(observed(store, scope, main_context["routing_decision_id"])) == 1


@pytest.mark.parametrize("marked", [True, False])
def test_unmarked_cached_dry_run_decision_is_not_reused(tmp_path, marked):
    app = Application(SQLiteStorage(tmp_path / "route.db"), judgments=ForbiddenJudge())
    _, _, first = route(app, "dry_run")
    identity = first["details"]["routing_decision_id"]
    if not marked:
        # Simulate a dry-run decision recorded before the fix: remove its diagnostic in the store.
        with sqlite3.connect(app.storage.path) as connection:
            (raw,) = connection.execute(
                "SELECT bundle FROM decisions_v1 WHERE decision_id=?", (identity,)
            ).fetchone()
            bundle = json.loads(raw)
            bundle["decision"]["details"]["diagnostics"] = []
            connection.execute(
                "UPDATE decisions_v1 SET bundle=? WHERE decision_id=?",
                (json.dumps(bundle, sort_keys=True, separators=(",", ":")), identity),
            )
    _, _, second = route(app, "dry_run", task=first["details"]["task_id"])
    assert second["details"]["reused_decision_id"] == (identity if marked else None)
    codes = [row["code"] for row in second["details"]["diagnostics"]]
    assert codes == ["dry_run_decision"]
