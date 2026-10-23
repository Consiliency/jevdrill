import uuid

from jevdrill.contracts import parse_contract
from jevdrill.storage import SQLiteStorage


def test_notice_scope_reads_and_cross_producer_deletion(tmp_path):
    scope = {
        "project_id": str(uuid.uuid4()),
        "workspace_id": str(uuid.uuid4()),
        "producer": "host-a",
        "operation": "route",
    }
    store = SQLiteStorage(tmp_path / "notices.db")
    task = str(uuid.uuid4())
    assert store.archive(scope, task, b"PRIVATE_SENTINEL", lambda: None, lambda a, b: a) is None
    notices = store.load_notices(scope)
    assert len(notices) == 1
    parse_contract("LocalNotice", notices[0])
    assert "PRIVATE_SENTINEL" not in str(notices)
    assert store.load_notices(scope | {"producer": "host-b"}) == notices
    assert store.load_notices(scope | {"workspace_id": str(uuid.uuid4())}) == []
    assert store.load_notices(scope | {"project_id": str(uuid.uuid4())}) == []
    store.delete_task(scope | {"producer": "host-b"}, task)
    assert store.load_notices(scope) == []
