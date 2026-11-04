import copy
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from jevdrill.application import Application
from jevdrill.contracts import ContractError, canonical_digest
from jevdrill.discovery import replay_trace
from jevdrill.storage import SQLiteStorage


def scope(inputs):
    envelope = inputs["envelope"]
    return {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "discover",
    }


def identity(storage):
    with storage._connect() as connection:
        return connection.execute("SELECT discovery_id FROM discoveries LIMIT 1").fetchone()[0]


def test_reservation_crash_recovery_never_dispatches_or_replenishes(
    tmp_path, discovery_inputs, discovery_observer, monkeypatch
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)

    def crash(*args):
        raise RuntimeError("synthetic crash after durable reservation")

    monkeypatch.setattr(discovery_observer, "observe_option", crash)
    with pytest.raises(RuntimeError):
        app.discover(discovery_inputs)
    discovery_id = identity(app.storage)
    before = app.storage.load_discovery(scope(discovery_inputs), discovery_id)
    assert len(before["calls"]) == 1 and before["calls"][0]["observation"] is None
    original_allowance = before["allowance"]
    app.storage.deadline = time.monotonic() - 1
    result = app.discover(discovery_inputs)
    assert result["status"] == "discovery_failed" and result["error_code"] == "interrupted"
    after = app.storage.load_discovery(scope(discovery_inputs), discovery_id)
    assert after["allowance"] == original_allowance and after["calls"] == before["calls"]
    assert app.discover(discovery_inputs) == result
    assert app.inspect_discovery(scope(discovery_inputs), discovery_id, True) == result


def test_observed_partial_recovery_terminal_and_late_answers_audit_only(
    tmp_path, discovery_inputs, discovery_observer, monkeypatch
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    original = app.storage.observe_discovery_call

    def observe_then_crash(*args):
        original(*args)
        raise RuntimeError("synthetic crash after durable observation")

    monkeypatch.setattr(app.storage, "observe_discovery_call", observe_then_crash)
    with pytest.raises(RuntimeError):
        app.discover(discovery_inputs)
    monkeypatch.setattr(app.storage, "observe_discovery_call", original)
    result = app.discover(discovery_inputs)
    assert result["status"] == "selected_guidance" and result["details"]["uncertainty"]
    assert result["details"]["termination_reason"] == "interrupted"
    assert (
        app.inspect_discovery(scope(discovery_inputs), result["details"]["discovery_id"], True)
        == result
    )
    assert len(discovery_observer.calls) == 1


def test_late_answer_cannot_replace_terminal_failure(
    tmp_path, discovery_inputs, discovery_observer, monkeypatch
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    monkeypatch.setattr(
        discovery_observer,
        "observe_option",
        lambda *args: (_ for _ in ()).throw(RuntimeError("crash")),
    )
    with pytest.raises(RuntimeError):
        app.discover(discovery_inputs)
    discovery_id = identity(app.storage)
    before = app.storage.load_discovery(scope(discovery_inputs), discovery_id)
    result = app.discover(discovery_inputs)
    question = before["rounds"][0]["question"]
    late = {
        "schema_version": "1",
        "function_revision": "ObserveDiscoveryOption-v1",
        "model_revision": "jev-latest",
        "question_digest": question["question_digest"],
        "judgments": {before["calls"][0]["option_id"]: True},
        "measurements": [],
    }
    assert (
        app.storage.observe_discovery_call(scope(discovery_inputs), discovery_id, 0, late) is False
    )
    assert app.discover(discovery_inputs) == result
    after = app.storage.load_discovery(scope(discovery_inputs), discovery_id)
    assert after["trace"] == before["trace"] or after["trace"]["result"] == result
    assert after["calls"][0]["reservation"] == before["calls"][0]["reservation"]
    assert app.inspect_discovery(scope(discovery_inputs), discovery_id, True) == result


def test_concurrent_recovery_commits_one_result_and_deletion_wins_afterward(
    tmp_path, discovery_inputs, discovery_observer, monkeypatch
):
    path = tmp_path / "route.db"
    app = Application(SQLiteStorage(path), discovery_judgments=discovery_observer)
    monkeypatch.setattr(
        discovery_observer,
        "observe_option",
        lambda *args: (_ for _ in ()).throw(RuntimeError("crash")),
    )
    with pytest.raises(RuntimeError):
        app.discover(discovery_inputs)
    barrier = threading.Barrier(2)

    def recover():
        recovery = Application(SQLiteStorage(path), discovery_judgments=discovery_observer)
        barrier.wait()
        return recovery.discover(copy.deepcopy(discovery_inputs))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(recover) for _ in range(2)]
        results = [future.result() for future in futures]
    assert results[0] == results[1]
    app.delete_discovery(scope(discovery_inputs), discovery_inputs["work_objective_id"])
    with pytest.raises(ContractError, match="deleted"):
        app.discover(discovery_inputs)


def test_distinct_keys_have_independent_fixed_allowances(
    tmp_path, discovery_inputs, discovery_observer
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    discovery_inputs["limits"]["max_calls"] = 1
    first = app.discover(discovery_inputs)
    discovery_inputs["envelope"]["idempotency_key"] = "fresh-second-key"
    second = app.discover(discovery_inputs)
    assert first["details"]["discovery_id"] != second["details"]["discovery_id"]
    assert len(discovery_observer.calls) == 2
    for result in (first, second):
        recorded = app.storage.load_discovery(
            scope(discovery_inputs), result["details"]["discovery_id"]
        )
        assert recorded["allowance"]["max_calls"] == 1 and len(recorded["calls"]) == 1


def test_same_key_conflict_and_commit_failure_no_success(
    tmp_path, discovery_inputs, discovery_observer, monkeypatch
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    app.discover(discovery_inputs)
    changed = copy.deepcopy(discovery_inputs)
    changed["authorized_context"] = "changed"
    with pytest.raises(ContractError, match="conflict"):
        app.discover(changed)
    changed["envelope"]["idempotency_key"] = "fresh"
    monkeypatch.setattr(
        app.storage,
        "commit_discovery",
        lambda *args: (_ for _ in ()).throw(OSError("synthetic commit failure")),
    )
    with pytest.raises(OSError):
        app.discover(changed)


def test_replay_reconstructs_selection_and_rejects_resigned_tampering(
    tmp_path, discovery_inputs, discovery_observer
):
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    result = app.discover(discovery_inputs)
    recorded = app.storage.load_discovery(
        scope(discovery_inputs), result["details"]["discovery_id"]
    )
    for kind in ("reference", "instructions", "status", "budget"):
        trace = copy.deepcopy(recorded["trace"])
        if kind == "reference":
            trace["result"]["details"]["guidance_refs"][0]["resource_id"] = "beta"
        elif kind == "instructions":
            trace["result"]["details"]["assembled_instructions"][0] = "fabricated"
        elif kind == "status":
            trace["result"]["status"] = "no_optional_guidance"
        else:
            trace["transitions"][0]["budget_after"]["calls"] += 1
        trace["result"]["details"]["trace_digest"] = "0" * 64
        trace["result"]["details"]["trace_digest"] = canonical_digest(trace)
        with pytest.raises(ContractError):
            replay_trace(trace)
