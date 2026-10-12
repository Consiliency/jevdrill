import copy
import json
import uuid
from pathlib import Path

from jevdrill.application import Application
from jevdrill.storage import SQLiteStorage


def test_notice_snapshots_do_not_mutate_retry_or_replay(tmp_path):
    payload = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]
    envelope = payload["request"]["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "route",
    }
    app = Application(SQLiteStorage(tmp_path / "notices.db"))
    original = app.route(payload)
    assert original["details"]["notices"] == []
    app.storage.archive(
        scope, payload["request"]["task_id"], b"private", lambda: None, lambda a, b: a
    )
    notices = app.notices({"schema_version": "1", "scope": scope})["notices"]
    assert notices
    assert app.route(payload) == original
    assert app.replay(scope, original["details"]["routing_decision_id"]) == original
    fresh = copy.deepcopy(payload)
    fresh["request"]["envelope"].update(
        idempotency_key="fresh-notice", request_id=str(uuid.uuid4())
    )
    assert app.route(fresh)["details"]["notices"] == notices
