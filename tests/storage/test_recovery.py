from concurrent.futures import ThreadPoolExecutor

import pytest

from jevdrill.contracts import canonical_digest
from jevdrill.storage import SQLiteStorage


def test_tombstone_is_durable_before_artifact_cleanup(tmp_path, monkeypatch):
    store = SQLiteStorage(tmp_path / "route.db")
    scope = {"project_id": "p", "workspace_id": "w", "producer": "host", "operation": "route"}
    store.stage_artifact(
        scope, "task", b"synthetic", kind="measurement", retention="active", encryption="none"
    )

    def crash():
        raise OSError("synthetic interrupted cleanup")

    monkeypatch.setattr(store, "recover_artifacts", crash)
    with pytest.raises(OSError):
        store.delete_task(scope, "task")
    assert store.is_deleted(scope, "task")
    reopened = SQLiteStorage(store.path)
    assert reopened.is_deleted(scope, "task")
    assert not any(
        path.is_file() for path in store._artifact_directory(store._task_scope(scope)).rglob("*")
    )


def test_missing_key_preserves_indexed_source_for_later_archival(tmp_path):
    store = SQLiteStorage(tmp_path / "route.db")
    scope = {"project_id": "p", "workspace_id": "w", "producer": "host", "operation": "route"}
    identity = store.stage_artifact(
        scope, "task", b"synthetic", kind="measurement", retention="active", encryption="none"
    )
    assert (
        store.archive_artifact(scope, identity, lambda: None, lambda data, key: b"unused") is None
    )
    files = [
        path
        for path in store._artifact_directory(store._task_scope(scope)).rglob("*")
        if path.is_file()
    ]
    assert len(files) == 1 and files[0].read_bytes() == b"synthetic"


def test_concurrent_corrections_cannot_fork_an_immutable_chain(tmp_path):
    store = SQLiteStorage(tmp_path / "route.db")
    scope = {"project_id": "p", "workspace_id": "w", "producer": "host", "operation": "report"}
    event = {
        "event_id": "original",
        "task_id": "task",
        "execution_run_id": "run",
        "payload": {"event_type": "completed"},
    }
    store.ingest_report(scope, "original", canonical_digest(event), event)

    def correct(identity):
        correction = event | {
            "event_id": identity,
            "supersedes_event_id": "original",
            "payload": {"event_type": "failed"},
        }
        return store.ingest_report(scope, identity, canonical_digest(correction), correction)[
            "status"
        ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(correct, ["one", "two"])) == ["accepted", "rejected"]
