import json
import os
import sqlite3
import subprocess
import sys
from time import monotonic

import pytest

from jevdrill.contracts import ContractError, canonical_digest
from jevdrill.storage import SQLiteStorage


def scope():
    return {
        "project_id": "project",
        "workspace_id": "workspace",
        "producer": "host",
        "operation": "route",
    }


def test_decision_is_scoped_idempotent_and_replayable(tmp_path):
    store = SQLiteStorage(tmp_path / "route.db")
    bundle = {"routing_decision_id": "decision", "task_id": "task", "status": "ready"}
    digest = canonical_digest(bundle)
    assert store.commit_decision(scope(), "key", digest, bundle)["status"] == "committed"
    assert store.commit_decision(scope(), "key", digest, bundle)["status"] == "duplicate"
    assert store.load_replay(scope(), "decision") == bundle
    changed = {"routing_decision_id": "another", "task_id": "task", "status": "ready"}
    with pytest.raises(ContractError, match="idempotency conflict"):
        store.commit_decision(scope(), "key", canonical_digest(changed), changed)


def test_delete_prevents_delayed_event_resurrection(tmp_path):
    store = SQLiteStorage(tmp_path / "route.db")
    event = {"event_id": "event", "task_id": "task"}
    assert store.delete_task(scope(), "task")["status"] == "deleted"
    assert (
        store.ingest_report(scope(), "event", canonical_digest(event), event)["status"]
        == "rejected"
    )


def test_deletion_covers_producers_operations_but_isolates_workspaces(tmp_path):
    store = SQLiteStorage(tmp_path / "route.db")
    bundle = {"routing_decision_id": "decision", "task_id": "task"}
    store.commit_decision(scope(), "key", canonical_digest(bundle), bundle)
    store.delete_task(scope() | {"producer": "other", "operation": "report"}, "task")
    assert store.load_replay(scope(), "decision") is None
    with pytest.raises(ContractError, match="deleted"):
        store.commit_decision(scope(), "key", canonical_digest(bundle), bundle)
    event = {"event_id": "event", "task_id": "task"}
    assert (
        store.ingest_report(
            scope() | {"producer": "third", "operation": "report"},
            "key",
            canonical_digest(event),
            event,
        )["status"]
        == "rejected"
    )
    assert (
        store.commit_decision(
            scope() | {"workspace_id": "other"}, "key", canonical_digest(bundle), bundle
        )["status"]
        == "committed"
    )


def test_immutable_decision_identity_and_operation_scoped_keys(tmp_path):
    store = SQLiteStorage(tmp_path / "route.db")
    bundle = {"routing_decision_id": "decision", "task_id": "task"}
    store.commit_decision(scope(), "key", canonical_digest(bundle), bundle)
    with pytest.raises(ContractError, match="identity conflict"):
        store.commit_decision(scope(), "new-key", canonical_digest(bundle), bundle)
    event = {"event_id": "event", "task_id": "task"}
    assert (
        store.ingest_report(
            scope() | {"operation": "report"}, "key", canonical_digest(event), event
        )["status"]
        == "accepted"
    )
    changed = event | {"event_id": "different"}
    assert (
        store.ingest_report(
            scope() | {"operation": "report"}, "key", canonical_digest(changed), changed
        )["status"]
        == "conflict"
    )


def test_projection_preserves_originals_and_rejects_invalid_corrections(tmp_path):
    store = SQLiteStorage(tmp_path / "route.db")
    events = [
        {
            "event_id": "done",
            "task_id": "task",
            "execution_run_id": "run",
            "source_sequence": 2,
            "payload": {"event_type": "completed"},
        },
        {
            "event_id": "start",
            "task_id": "task",
            "execution_run_id": "run",
            "source_sequence": 1,
            "payload": {"event_type": "started"},
        },
    ]
    for event in events:
        assert (
            store.ingest_report(scope(), event["event_id"], canonical_digest(event), event)[
                "status"
            ]
            == "accepted"
        )
    assert store.project_run(scope(), "run")["status"] == "completed"
    correction = events[0] | {
        "event_id": "correction",
        "supersedes_event_id": "done",
        "payload": {"event_type": "failed"},
    }
    assert (
        store.ingest_report(
            scope() | {"producer": "different"}, "bad", canonical_digest(correction), correction
        )["status"]
        == "rejected"
    )
    assert (
        store.ingest_report(scope(), "correction", canonical_digest(correction), correction)[
            "status"
        ]
        == "accepted"
    )
    assert store.project_run(scope(), "run")["status"] == "failed"
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT count(*) FROM events_v1").fetchone()[0] == 3


@pytest.mark.parametrize("committed", [False, True])
def test_process_exit_at_transaction_boundary(tmp_path, committed):
    path = tmp_path / "route.db"
    store = SQLiteStorage(path)
    script = """
import json, os, sys
from pathlib import Path
from jevdrill.storage import SQLiteStorage
from jevdrill.contracts import canonical_digest
store = SQLiteStorage(Path(sys.argv[1]))
scope = json.loads(sys.argv[2])
bundle = {'routing_decision_id':'decision','task_id':'task'}
if sys.argv[3] == 'True':
    store.commit_decision(scope,'key',canonical_digest(bundle),bundle)
else:
    with store._connect(True) as connection:
        connection.execute('INSERT INTO tasks VALUES (?,?,0)', (store._task_scope(scope),'task'))
        os._exit(0)
os._exit(0)
"""
    subprocess.run(
        [sys.executable, "-c", script, str(path), json.dumps(scope()), str(committed)], check=True
    )
    assert (store.load_replay(scope(), "decision") is not None) == committed
    bundle = {"routing_decision_id": "decision", "task_id": "task"}
    assert store.commit_decision(scope(), "key", canonical_digest(bundle), bundle)["status"] == (
        "duplicate" if committed else "committed"
    )


def test_contention_uses_remaining_deadline(tmp_path):
    store = SQLiteStorage(tmp_path / "route.db")
    with sqlite3.connect(store.path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        store.deadline = monotonic() + 0.05
        started = monotonic()
        with pytest.raises(sqlite3.OperationalError):
            store.delete_task(scope(), "task")
        assert monotonic() - started < 0.5


def test_artifact_recovery_after_failed_replace_and_deletion(tmp_path, monkeypatch):
    store = SQLiteStorage(tmp_path / "route.db")
    original = os.replace

    def fail(*args):
        raise OSError("synthetic crash")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        store.stage_artifact(
            scope(), "task", b"synthetic", kind="measurement", retention="active", encryption="none"
        )
    monkeypatch.setattr(os, "replace", original)
    store.recover_artifacts()
    files = list(store._artifact_directory(store._task_scope(scope())).rglob("*"))
    assert any(path.is_file() and path.read_bytes() == b"synthetic" for path in files)
    store.delete_task(scope(), "task")
    store.recover_artifacts()
    assert not any(
        path.is_file() for path in store._artifact_directory(store._task_scope(scope())).rglob("*")
    )


def test_migration_failure_is_atomic(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE decisions(scope,key,digest,decision_id,bundle)")
        bundle = json.dumps({"routing_decision_id": "duplicate", "task_id": "task"})
        for key in ("one", "two"):
            connection.execute(
                "INSERT INTO decisions VALUES (?,?,?,?,?)",
                (json.dumps(scope()), key, "digest", "duplicate", bundle),
            )
    with pytest.raises(sqlite3.IntegrityError):
        SQLiteStorage(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM decisions").fetchone()[0] == 2
        assert (
            connection.execute("SELECT count(*) FROM sqlite_master WHERE name='tasks'").fetchone()[
                0
            ]
            == 0
        )
