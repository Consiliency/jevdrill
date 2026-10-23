import sqlite3

import pytest

from jevdrill.contracts import ContractError
from jevdrill.storage import SQLiteStorage


def test_raw_controls_and_archive_key_failure(tmp_path):
    store = SQLiteStorage(tmp_path / "route.db")
    scope = {
        "project_id": "project",
        "workspace_id": "workspace",
        "producer": "host",
        "operation": "route",
    }
    for kind in ("raw_task", "raw_output"):
        assert (
            store.stage_artifact(
                scope, "task", b"private-sentinel", kind=kind, retention="active", encryption="none"
            )
            is None
        )
    with pytest.raises(ContractError, match="plaintext"):
        store.stage_artifact(
            scope,
            "task",
            b"private-sentinel",
            kind="archive",
            retention="archive",
            encryption="none",
        )
    assert (
        store.archive(scope, "task", b"private-sentinel", lambda: None, lambda data, key: data)
        is None
    )
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT kind FROM notices").fetchone()[0] == "archive_key_missing"
        assert connection.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 0
    assert b"private-sentinel" not in store.path.read_bytes()
