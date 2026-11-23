"""LEARN SL-2 Part A: task deletion and the write-ahead log (Consiliency/jevdrill#21).

A deletion answers `deleted` only once the task's deleted payload rows are erased
from the database file and its write-ahead log. Until then it fails as a storage
failure, after committing the deletion. The test holds another connection's read
transaction open itself, so nothing here depends on timing.
"""

import json
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest

from tests.analysis.test_observations import case, report

LIFECYCLE = {"kind": "lifecycle", "event_type": "completed", "applied_plan_id": None}


def store_files(store):
    """The files that hold rows: the database and its write-ahead log.

    The shared-memory file holds only the log's index, never row content, and another
    connection's locks on it can refuse a read on Windows, so it is not read.
    """
    wal = store.path.with_name(store.path.name + "-wal")
    return [path for path in (store.path, wal) if path.exists()]


def found(store, sentinel):
    return [path.name for path in store_files(store) if sentinel in path.read_bytes()]


@pytest.fixture
def task(tmp_path):
    """A routed task with one report; its event identity is a value nothing else holds."""
    app, scope, context, _ = case(tmp_path)
    event = report(app, scope, context, str(uuid4()), dict(LIFECYCLE, reason=None))
    sentinel = event["event_id"].encode()
    assert found(app.storage, sentinel)
    return app.storage, scope, context["task_id"], sentinel


def reader(store):
    """Another connection holding a read transaction open until it is closed."""
    connection = sqlite3.connect(store.path, isolation_level=None)
    connection.execute("BEGIN")
    connection.execute("SELECT count(*) FROM events_v1").fetchone()
    return connection


def unfinished(store, scope, task_id):
    """True if the request failed as a storage failure, as an unfinished erasure does."""
    with pytest.raises(sqlite3.OperationalError, match="not yet erased"):
        store.delete_task(scope, task_id)
    return True


def test_deletion_is_not_reported_finished_while_a_reader_holds_the_log(task):
    store, scope, task_id, sentinel = task
    held = reader(store)
    try:
        assert unfinished(store, scope, task_id)
        assert found(store, sentinel)
        # The logical deletion is committed: nothing deleted is readable through storage.
        assert store.is_deleted(scope, task_id)
        assert store.learning_observations(scope) == []
    finally:
        held.close()


def idle(store):
    """An idle connection kept open, so that closing the reader is not the last close.

    SQLite checkpoints when its last connection closes; with this one open, only the
    repeated request's own checkpoint can finish the erasure.
    """
    connection = sqlite3.connect(store.path, isolation_level=None)
    # One finished read attaches it to the log; it then holds no transaction.
    connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
    return connection


def test_the_repeated_request_finishes_the_erasure_once_the_reader_closes(task):
    store, scope, task_id, sentinel = task
    keeper, held = idle(store), reader(store)
    try:
        assert unfinished(store, scope, task_id)
        # Repeated while the reader is still open: still not finished.
        assert unfinished(store, scope, task_id)
        assert found(store, sentinel)
        held.close()
        assert found(store, sentinel)  # closing the reader alone erases nothing
        assert store.delete_task(scope, task_id) == {"status": "deleted", "task_id": task_id}
        assert found(store, sentinel) == []
    finally:
        held.close()
        keeper.close()


def test_an_archived_copy_is_gone_after_the_task_is_deleted(task):
    store, scope, task_id, _ = task
    content = b"archived-" + uuid4().hex.encode()
    identity = store.stage_artifact(
        scope, task_id, content, kind="archive", retention="archive", encryption="fernet-v1"
    )
    directory = store._artifact_directory(store._task_scope(scope))
    assert (directory / identity).read_bytes() == content
    assert store.delete_task(scope, task_id)["status"] == "deleted"
    assert not any(path.is_file() for path in directory.rglob("*"))
    assert found(store, content) == []


def test_with_no_other_reader_deletion_finishes_at_once(task):
    store, scope, task_id, sentinel = task
    assert store.delete_task(scope, task_id) == {"status": "deleted", "task_id": task_id}
    assert found(store, sentinel) == []
    assert store.delete_task(scope, task_id) == {"status": "deleted", "task_id": task_id}


def delete_by_command_line(store, scope, task_id):
    """The `delete` command in a child process, as a host calls it."""
    result = subprocess.run(
        [sys.executable, "-m", "jevdrill.cli", "--storage", str(store.path), "delete"]
        + ["--task-id", task_id, "--scope", json.dumps(scope)],
        input="{}",
        text=True,
        capture_output=True,
        cwd=store.path.parent,
        check=False,
    )
    return result.returncode, json.loads(result.stdout)


STORAGE_FAILURE = {
    "schema_version": "1",
    "status": "storage_failure",
    "code": "infrastructure_failure",
}


def test_the_command_line_answers_a_storage_failure_then_deleted(task):
    store, scope, task_id, sentinel = task
    keeper, held = idle(store), reader(store)
    try:
        pending = delete_by_command_line(store, scope, task_id)
        held.close()
        assert found(store, sentinel)
        finished = delete_by_command_line(store, scope, task_id)
        assert found(store, sentinel) == []  # before the last close, which would checkpoint
    finally:
        held.close()
        keeper.close()
    assert pending == (4, STORAGE_FAILURE)
    assert finished == (0, {"schema_version": "1", "status": "deleted", "task_id": task_id})
