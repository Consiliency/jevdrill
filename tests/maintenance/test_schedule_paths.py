import json
import os
from uuid import uuid4

import pytest

from jevdrill.contracts import ContractError
from jevdrill.maintenance import Maintenance
from jevdrill.storage import SQLiteStorage


def request(scope, action, path):
    return {
        "schema_version": "1",
        "scope": scope,
        "action": action,
        "interactive_busy": False,
        "max_items": 10,
        "archive_retention_days": 365,
        "request_path": str(path),
    }


@pytest.mark.skipif(os.name == "nt", reason="Windows file names cannot hold a line break")
@pytest.mark.parametrize("character", ["\n", "\r", "\x1b", "\x7f"])
def test_schedule_refuses_a_path_with_a_control_character(tmp_path, character):
    scope = {
        "project_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "producer": "fixture",
        "operation": "route",
    }
    store = tmp_path / "store"
    store.mkdir()
    folder = tmp_path / f"proj{character}ExecStart=injected"
    folder.mkdir()
    path = (folder / "maintenance.json").resolve()
    path.write_text(json.dumps(request(scope, "run", path)), encoding="utf-8")
    maintenance = Maintenance(SQLiteStorage(store / "jev.db"))
    with pytest.raises(ContractError, match="control characters"):
        maintenance.run(request(scope, "schedule", path))
    assert not (store / "schedules").exists()
