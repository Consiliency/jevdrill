import os
import sqlite3
import stat
import time
from uuid import uuid4

import pytest

from jevdrill.integrations.development import DevelopmentJudge, DevelopmentRunner
from jevdrill.integrations.experiments import RestrictedContainerRunner


def judge(path):
    return DevelopmentJudge(
        path,
        scope={
            "project_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "producer": "fixture",
            "operation": "discover",
        },
        authorization_revision="synthetic-grant",
        max_calls=1,
        total_spend_microusd=2753,
        deadline_ms=int(time.time() * 1000) + 10_000,
        credential=lambda: "synthetic-secret",
        authorize=lambda scope: False,
        base_url="http://127.0.0.1:9/v1",
    )


def runner(path):
    return DevelopmentRunner(
        path,
        models={},
        cases={},
        container=RestrictedContainerRunner("sha256:" + "1" * 64),
        credential=lambda: "synthetic-secret",
        authorize=lambda record: False,
        base_url="http://127.0.0.1:9/v1",
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
@pytest.mark.parametrize("create", [judge, runner])
def test_new_development_databases_are_private(tmp_path, create):
    previous = os.umask(0o022)
    try:
        service = create(tmp_path / "side" / "store.db")
        with sqlite3.connect(service.path) as db:
            db.execute("CREATE TABLE probe (value TEXT)")
    finally:
        os.umask(previous)
    assert stat.S_IMODE(service.path.stat().st_mode) == 0o600


@pytest.mark.parametrize("create", [judge, runner])
def test_unusable_database_path_is_still_reported_by_sqlite(tmp_path, create):
    with pytest.raises(sqlite3.OperationalError):
        create(tmp_path)
    assert list(tmp_path.iterdir()) == []
