import copy
import json
import uuid
from pathlib import Path

import pytest

from jevdrill.application import Application, open_application
from jevdrill.contracts import ContractError
from jevdrill.discovery import reference
from jevdrill.storage import SQLiteStorage


def scope(inputs):
    envelope = inputs["envelope"]
    return {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "discover",
    }


def linked(inputs, result):
    base = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]
    base["catalog"] = copy.deepcopy(inputs["catalog"])
    base["request"]["hard_constraints"] = copy.deepcopy(inputs["hard_constraints"])
    base["request"]["optimization_objective"]["acceptance_requirements"] = copy.deepcopy(
        inputs["acceptance_requirements"]
    )
    base["inventory"]["candidates"][0]["guidance_options"] = [
        reference(row)
        | {
            "role": "optional-" + str(number),
            "admission": row["admission"],
            "authority": "synthetic-admission",
            "task_id": base["request"]["task_id"],
            "token_count": None,
        }
        for number, row in enumerate(inputs["catalog"]["resources"])
    ]
    return {
        "schema_version": "2",
        "route_inputs": base,
        "discovery_ref": {
            key: result["details"][key]
            for key in ("discovery_id", "work_objective_id", "trace_digest")
        },
    }


def test_public_discovery_two_independent_tasks_and_replay(
    tmp_path, discovery_inputs, discovery_observer
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    result = app.discover(discovery_inputs)
    assert result["status"] == "selected_guidance"
    assert [row["resource_id"] for row in result["details"]["guidance_refs"]] == ["alpha"]
    assert app.discover(discovery_inputs) == result
    count = len(discovery_observer.calls)
    assert (
        app.inspect_discovery(scope(discovery_inputs), result["details"]["discovery_id"], True)
        == result
    )
    assert len(discovery_observer.calls) == count
    first = linked(discovery_inputs, result)
    base = first["route_inputs"]
    other = copy.deepcopy(base["inventory"]["candidates"][0])
    other.update(
        candidate_id="candidate-b",
        model_id="model-b",
        resolved_model_revision="model-b-v1",
        completion_time_ms=10,
    )
    other["rates"]["input_rate"] = "0.01"
    base["inventory"]["candidates"].append(other)
    chosen = app.route(first)
    assert chosen["status"] == "ready"
    assert chosen["execution_plan"]["model_id"] == "model-a"
    assert chosen["details"]["discovery_ref"] == first["discovery_ref"]
    second = copy.deepcopy(first)
    second["route_inputs"]["request"]["task_id"] = str(uuid.uuid4())
    second["route_inputs"]["request"]["envelope"]["request_id"] = str(uuid.uuid4())
    second["route_inputs"]["request"]["envelope"]["idempotency_key"] = "second-task"
    second["route_inputs"]["completion_time_limit_ms"] = 20
    chosen = app.route(second)
    assert chosen["status"] == "ready" and chosen["execution_plan"]["model_id"] == "model-b"
    # Even a fresh candidate with an undiscovered beta option cannot inject it.
    assert all(
        row["resource_id"] != "beta" for row in chosen["execution_plan"]["optional_guidance"]
    )


def test_changing_objective_changes_supported_guidance(
    tmp_path, discovery_inputs, discovery_observer
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    first = app.discover(discovery_inputs)
    discovery_inputs["work_objective_text"] = "beta"
    discovery_inputs["envelope"]["idempotency_key"] = "beta-key"
    second = app.discover(discovery_inputs)
    assert first["details"]["guidance_refs"] != second["details"]["guidance_refs"]
    assert second["details"]["guidance_refs"][0]["resource_id"] == "beta"


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("reject", "no_optional_guidance"),
        ("unknown", "discovery_failed"),
        ("context", "needs_context"),
        ("required", "constraint_conflict"),
        ("empty", "no_optional_guidance"),
    ],
)
def test_all_discovery_statuses_gate_quality_sufficient_route(
    tmp_path, discovery_inputs, discovery_observer, mode, expected
):
    if mode == "reject":
        discovery_observer.answer = lambda task, option: False
    elif mode == "unknown":
        discovery_inputs["descriptions"] = []
    elif mode == "context":
        discovery_inputs["work_objective_text"] = ""
    elif mode == "required":
        discovery_inputs["required_guidance"] = [
            reference(discovery_inputs["catalog"]["resources"][0])
            | {
                "role": "required",
                "admission": "explicitly_enabled",
                "authority": "synthetic",
                "task_id": discovery_inputs["work_objective_id"],
                "token_count": None,
            }
        ]
        discovery_inputs["catalog"]["resources"] = []
        discovery_inputs["descriptions"] = []
    elif mode == "empty":
        discovery_inputs["catalog"]["resources"] = []
        discovery_inputs["descriptions"] = []
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    result = app.discover(discovery_inputs)
    assert result["status"] == expected
    wrapper = linked(discovery_inputs, result)
    if expected == "no_optional_guidance":
        assert app.route(wrapper)["status"] == "ready"
    else:
        with pytest.raises(ContractError, match="status"):
            app.route(wrapper)


def test_uncertain_supported_selection_can_route(tmp_path, discovery_inputs, discovery_observer):
    discovery_inputs["limits"]["max_rounds"] = 1
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    result = app.discover(discovery_inputs)
    assert result["status"] == "selected_guidance" and result["details"]["uncertainty"]
    routed = app.route(linked(discovery_inputs, result))
    assert routed["status"] == "ready" and routed["details"]["discovery_uncertainty"]


@pytest.mark.parametrize(
    "mutation",
    ["digest", "objective", "producer", "project", "workspace", "catalog", "hash", "query"],
)
def test_bad_links_never_enter_prepare(
    tmp_path, discovery_inputs, discovery_observer, mutation, monkeypatch
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    value = linked(discovery_inputs, app.discover(discovery_inputs))
    if mutation == "digest":
        value["discovery_ref"]["trace_digest"] = "0" * 64
    elif mutation == "objective":
        value["discovery_ref"]["work_objective_id"] = str(uuid.uuid4())
    elif mutation in {"producer", "project", "workspace"}:
        field = {"producer": "harness_id", "project": "project_id", "workspace": "workspace_id"}[
            mutation
        ]
        value["route_inputs"]["request"]["envelope"][field] = str(uuid.uuid4())
    elif mutation == "catalog":
        value["route_inputs"]["catalog"]["revision"] = "stale"
    elif mutation == "hash":
        value["route_inputs"]["catalog"]["resources"][0]["instructions"] = "changed"
    else:
        value["route_inputs"]["catalog_query"] = {
            "domain": "alpha",
            "specialty": "alpha",
            "task_family": "implementation",
            "facets": [],
            "max_branches": 1,
        }
    monkeypatch.setattr(
        app, "_prepare", lambda *args: pytest.fail("invalid reference entered prepare")
    )
    with pytest.raises(ContractError):
        app.route(value)


@pytest.mark.parametrize(
    "field,parent,strict,relaxed",
    [
        ("total_deadline_ms", 4000, 3000, 5000),
        ("context_token_limit", 32768, 32000, 40000),
        ("max_attempts", 2, 1, 3),
        ("local_only", True, True, False),
        ("allowed_providers", ["local", "typesafeai"], ["local"], []),
        ("governing_instruction_refs", ["mandatory"], ["mandatory", "additional"], []),
        (
            "spending_ceiling",
            {"amount": "10", "currency": "USD"},
            {"amount": "1", "currency": "USD"},
            None,
        ),
        (
            "execution_token_limits",
            {"input_tokens": 10000, "output_tokens": 2000},
            {"input_tokens": 9000, "output_tokens": 1000},
            None,
        ),
    ],
)
def test_constraint_inheritance_every_field(
    tmp_path, field, parent, strict, relaxed, discovery_inputs
):
    before = discovery_inputs["hard_constraints"]
    before[field] = parent
    Application._inherit_constraints(before, copy.deepcopy(before))
    after = copy.deepcopy(before)
    after[field] = strict
    Application._inherit_constraints(before, after)
    after[field] = relaxed
    with pytest.raises(ContractError, match="weakened"):
        Application._inherit_constraints(before, after)
    discovery_inputs["catalog"]["resources"] = []
    discovery_inputs["descriptions"] = []
    app = open_application(tmp_path / "route.db")
    wrapper = linked(discovery_inputs, app.discover(discovery_inputs))
    wrapper["route_inputs"]["inventory"]["candidates"][0]["execution_token_limits"] = {
        "input_tokens": 5000,
        "output_tokens": 500,
    }
    for number, value in enumerate((parent, strict)):
        current = copy.deepcopy(wrapper)
        current["route_inputs"]["request"]["hard_constraints"][field] = value
        current["route_inputs"]["request"]["envelope"].update(
            request_id=str(uuid.uuid4()), idempotency_key="constraint-" + str(number)
        )
        assert app.route(current)["status"] == "ready"
    wrapper["route_inputs"]["request"]["hard_constraints"][field] = relaxed
    with pytest.raises(ContractError, match="weakened"):
        app.route(wrapper)


def test_deletion_invalidates_all_keys_retry_cache_and_late_commit(
    tmp_path, discovery_inputs, discovery_observer, monkeypatch
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    first = app.discover(discovery_inputs)
    task = linked(discovery_inputs, first)
    assert app.route(task)["status"] == "ready"
    second = copy.deepcopy(discovery_inputs)
    second["envelope"]["idempotency_key"] = "independent-second-key"
    app.discover(second)
    deleter = dict(scope(discovery_inputs), producer="authorized-other-producer")
    app.delete_discovery(deleter, discovery_inputs["work_objective_id"])
    for value in (
        discovery_inputs,
        second,
        dict(second, envelope=dict(second["envelope"], idempotency_key="third-key")),
    ):
        with pytest.raises(ContractError, match="deleted"):
            app.discover(value)
    with pytest.raises(ContractError, match="deleted"):
        app.route(task)
    with pytest.raises(ContractError, match="deleted"):
        app.inspect_discovery(scope(discovery_inputs), first["details"]["discovery_id"], True)


def test_route_commit_rechecks_concurrent_objective_deletion(
    tmp_path, discovery_inputs, discovery_observer, monkeypatch
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    wrapper = linked(discovery_inputs, app.discover(discovery_inputs))
    original = app.storage.commit_decision

    def delete_then_commit(*args):
        app.delete_discovery(scope(discovery_inputs), discovery_inputs["work_objective_id"])
        return original(*args)

    monkeypatch.setattr(app.storage, "commit_decision", delete_then_commit)
    with pytest.raises(ContractError, match="deleted"):
        app.route(wrapper)


def test_production_construction_empty_catalog_without_provider(tmp_path, discovery_inputs):
    discovery_inputs["catalog"]["resources"] = []
    discovery_inputs["descriptions"] = []
    result = open_application(tmp_path / "route.db").discover(discovery_inputs)
    assert result["status"] == "no_optional_guidance"


def test_false_initial_category_recovers_useful_alternate_branch(
    tmp_path, discovery_inputs, discovery_observer
):
    discovery_inputs["work_objective_text"] = "Need beta expertise"
    discovery_inputs["limits"]["active_branch_width"] = 1
    discovery_observer.answer = lambda task, option: (
        "beta" in (option["description"] or "") if option["level"] == "resource" else False
    )
    result = Application(
        SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer
    ).discover(discovery_inputs)
    assert result["status"] == "selected_guidance"
    assert result["details"]["guidance_refs"][0]["resource_id"] == "beta"
    assert {row["level"] for row in discovery_observer.calls} == {
        "domain",
        "specialty",
        "task_family",
        "resource",
    }


def test_required_guidance_rebinds_coalesces_and_rejects_conflicts(
    tmp_path, discovery_inputs, discovery_observer
):
    required = reference(discovery_inputs["catalog"]["resources"][0]) | {
        "role": "required",
        "admission": "explicitly_enabled",
        "authority": "owner",
        "task_id": discovery_inputs["work_objective_id"],
        "token_count": None,
    }
    discovery_inputs["required_guidance"] = [required]
    discovery_inputs["work_objective_text"] = "beta"
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    result = app.discover(discovery_inputs)
    wrapper = linked(discovery_inputs, result)
    active = copy.deepcopy(required)
    active["task_id"] = wrapper["route_inputs"]["request"]["task_id"]
    wrapper["route_inputs"]["request"]["active_guidance"] = [active]
    routed = app.route(wrapper)
    assert routed["status"] == "ready"
    guidance = routed["execution_plan"]["required_guidance"]
    assert (
        len(guidance) == 1
        and guidance[0]["task_id"] == active["task_id"]
        and guidance[0]["token_count"] > 0
    )
    for field in ("authority", "role", "admission", "revision", "content_hash"):
        bad = copy.deepcopy(wrapper)
        bad["route_inputs"]["request"]["active_guidance"][0][field] = (
            "policy_admitted"
            if field == "admission"
            else "0" * 64
            if field == "content_hash"
            else "conflicting"
        )
        with pytest.raises(ContractError, match="conflict"):
            app.route(bad)


def test_all_zero_one_two_combinations_skip_catalog_narrow(
    tmp_path, discovery_inputs, discovery_observer, monkeypatch
):
    discovery_observer.answer = lambda task, option: True
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    wrapper = linked(discovery_inputs, app.discover(discovery_inputs))
    assert len(wrapper["discovery_ref"]) == 3
    prepared = []
    original = app._prepare

    def prepare(*args):
        rows = original(*args)
        prepared.extend(rows)
        return rows

    monkeypatch.setattr(app, "_prepare", prepare)
    monkeypatch.setattr(
        "jevdrill.application.narrow", lambda *args: pytest.fail("linked route entered narrow")
    )
    assert app.route(wrapper)["status"] == "ready"
    assert sorted(len(row["optional_guidance"]) for row in prepared) == [0, 1, 1, 2]
    assert all(
        row["task_id"] == wrapper["route_inputs"]["request"]["task_id"]
        for candidate in prepared
        for row in candidate["optional_guidance"]
    )


@pytest.mark.parametrize(
    "limit,value",
    [("max_rounds", 0), ("max_calls", 0), ("max_input_tokens", 1), ("max_candidates", 0)],
)
def test_discovery_exhaustion_keeps_actual_work_within_allowance(
    tmp_path, discovery_inputs, discovery_observer, limit, value
):
    discovery_inputs["limits"][limit] = value
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    result = app.discover(discovery_inputs)
    assert result["status"] == "discovery_failed" and not discovery_observer.calls
    recorded = app.storage.load_discovery(
        scope(discovery_inputs), result["details"]["discovery_id"]
    )
    budget = recorded["trace"]["final_state"]["budget"]
    for field, key in (
        ("max_rounds", "rounds"),
        ("max_calls", "calls"),
        ("max_candidates", "candidates"),
        ("max_input_tokens", "input_tokens"),
    ):
        assert budget[key] <= recorded["allowance"][field]


def test_oversized_description_and_reduced_setting_remain_unknown(
    tmp_path, discovery_inputs, discovery_observer
):
    discovery_inputs["descriptions"][0]["description"] = "x" * 2049
    discovery_inputs["settings_layers"] = [
        {"source": "request", "values": {"max_description_utf8_bytes": 20}}
    ]
    result = Application(
        SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer
    ).discover(discovery_inputs)
    assert result["status"] == "discovery_failed"
    assert not [row for row in discovery_observer.calls if row["level"] == "resource"]
