import sqlite3

import pytest

from jevdrill.contracts import ContractError
from jevdrill.storage import SQLiteStorage


def test_copied_privacy_database_is_initialized_and_isolated(
    tmp_path, privacy_storage, privacy_database_template
):
    fresh = SQLiteStorage(tmp_path / "fresh.db")
    assert type(privacy_storage) is type(fresh)
    assert privacy_storage is not privacy_database_template
    assert privacy_storage.deadline is fresh.deadline is None
    assert privacy_storage.path != privacy_database_template.path

    def schema(path):
        with sqlite3.connect(path) as connection:
            return connection.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
            ).fetchall()

    initial = schema(fresh.path)
    assert schema(privacy_storage.path) == initial
    with privacy_storage._connect(True) as connection:
        connection.execute("CREATE TABLE fixture_isolation (value TEXT)")
        connection.execute("INSERT INTO fixture_isolation VALUES ('independent')")
    with privacy_storage._connect() as connection:
        assert connection.execute("SELECT value FROM fixture_isolation").fetchone() == (
            "independent",
        )
    assert schema(fresh.path) == schema(privacy_database_template.path) == initial


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
