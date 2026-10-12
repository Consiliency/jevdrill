import hashlib
import json
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from jevdrill.contracts import ContractError
from jevdrill.integrations.archive import decrypt_archive
from jevdrill.maintenance import DAY, Maintenance
from tests.analysis.test_observations import case, measurement, report


def request(scope, action="run", max_items=10, path=None):
    return {
        "schema_version": "1",
        "scope": scope,
        "action": action,
        "interactive_busy": False,
        "max_items": max_items,
        "archive_retention_days": 365,
        "request_path": str(path) if path else None,
    }


def artifact(app, scope, context, content=b"synthetic task", created=100):
    return app.storage.stage_artifact(
        scope,
        context["task_id"],
        content,
        kind="raw_task",
        retention="active",
        encryption="none",
        retain_raw_tasks=True,
        created_at=created,
    )


def test_active_grace_encrypted_archive_one_year_expiry_and_measurement_persistence(tmp_path):
    app, scope, context, _ = case(tmp_path)
    report(app, scope, context, str(uuid4()), {"kind": "usage", "measurements": [measurement()]})
    identity = artifact(app, scope, context)
    key = Fernet.generate_key()
    now = [100]
    maintenance = Maintenance(app.storage, lambda _: key, lambda: now[0])
    now[0] = 100 + 30 * DAY - 1
    assert maintenance.run(request(scope))["processed"] == 0
    now[0] += 1
    first = maintenance.run(request(scope))
    assert first["processed"] == 1
    assert first["notices"][0]["automatic_action"] == "archive"
    directory = app.storage._artifact_directory(app.storage._task_scope(scope))
    now[0] += 7 * DAY - 1
    assert maintenance.run(request(scope))["processed"] == 0 and (directory / identity).exists()
    now[0] += 1
    assert maintenance.run(request(scope))["processed"] == 1 and not (directory / identity).exists()
    with app.storage._connect() as c:
        archive_id, archived = c.execute(
            "SELECT artifact_id,archived FROM artifact_lifecycle WHERE archived IS NOT NULL"
        ).fetchone()
    encrypted = (directory / archive_id).read_bytes()
    body = json.loads(decrypt_archive(encrypted, key))
    assert bytes.fromhex(body["content"]) == b"synthetic task"
    assert b"synthetic task" not in encrypted
    now[0] = archived + 358 * DAY
    notices = maintenance.run(request(scope))["notices"]
    assert any("expires" in n["summary"] and n["deadline"] for n in notices)
    now[0] = archived + 365 * DAY
    assert (
        maintenance.run(request(scope))["processed"] == 1 and not (directory / archive_id).exists()
    )
    assert app.storage.learning_observations(scope)[0]["measurements"] == [measurement()]
    app.storage.delete_task(scope, context["task_id"])
    assert app.storage.learning_observations(scope) == []


@pytest.mark.parametrize("key_state", ["missing", "locked", "failed"])
def test_key_failures_keep_pending_active_content_and_notice(tmp_path, key_state):
    app, scope, context, _ = case(tmp_path)
    identity = artifact(app, scope, context)
    now = [100 + 30 * DAY]

    def provider(_):
        if key_state == "failed":
            raise OSError("synthetic key service unavailable")

    maintenance = Maintenance(app.storage, provider, lambda: now[0])
    maintenance.run(request(scope))
    now[0] += 7 * DAY
    result = maintenance.run(request(scope))
    assert result["pending"] == 1 and any(
        "key unavailable" in n["summary"] for n in result["notices"]
    )
    assert (
        app.storage._artifact_directory(app.storage._task_scope(scope)) / identity
    ).read_bytes() == b"synthetic task"
    assert app.storage.load_notices(scope) == result["notices"]


def test_clock_rollback_and_corruption_enter_production_retention(tmp_path):
    app, scope, context, _ = case(tmp_path)
    identity = artifact(app, scope, context)
    key = Fernet.generate_key()
    now = [100 + 30 * DAY]
    maintenance = Maintenance(app.storage, lambda _: key, lambda: now[0])
    maintenance.run(request(scope))
    now[0] -= 1
    assert maintenance.run(request(scope))["status"] == "paused"
    now[0] = 100 + 37 * DAY
    directory = app.storage._artifact_directory(app.storage._task_scope(scope))
    (directory / identity).write_bytes(b"corrupt")
    with pytest.raises(ContractError, match="digest"):
        maintenance.run(request(scope))
    assert (directory / identity).exists()


def test_archive_crash_retry_keeps_source_until_durable_verification(tmp_path, monkeypatch):
    app, scope, context, _ = case(tmp_path)
    identity = artifact(app, scope, context)
    key = Fernet.generate_key()
    now = [100 + 30 * DAY]
    maintenance = Maintenance(app.storage, lambda _: key, lambda: now[0])
    maintenance.run(request(scope))
    now[0] += 7 * DAY
    original = app.storage.stage_artifact

    def crash(*args, **kwargs):
        result = original(*args, **kwargs)
        if kwargs.get("kind") == "archive":
            raise OSError("synthetic crash after durable archive")
        return result

    monkeypatch.setattr(app.storage, "stage_artifact", crash)
    with pytest.raises(OSError):
        maintenance.run(request(scope))
    assert (app.storage._artifact_directory(app.storage._task_scope(scope)) / identity).exists()
    monkeypatch.setattr(app.storage, "stage_artifact", original)
    assert maintenance.run(request(scope))["processed"] == 1
    with app.storage._connect() as c:
        assert c.execute("SELECT count(*) FROM artifacts WHERE kind='archive'").fetchone()[0] == 1
        assert c.execute("SELECT archived FROM artifact_lifecycle").fetchone()[0] == now[0]


def test_archive_tamper_cannot_restore(tmp_path):
    app, scope, context, _ = case(tmp_path)
    artifact(app, scope, context)
    key = Fernet.generate_key()
    now = [100 + 30 * DAY]
    maintenance = Maintenance(app.storage, lambda _: key, lambda: now[0])
    maintenance.run(request(scope))
    now[0] += 7 * DAY
    maintenance.run(request(scope))
    with app.storage._connect() as c:
        identity = c.execute("SELECT artifact_id FROM artifacts WHERE kind='archive'").fetchone()[0]
    path = app.storage._artifact_directory(app.storage._task_scope(scope)) / identity
    content = bytearray(path.read_bytes())
    content[-10] ^= 1
    path.write_bytes(content)
    with app.storage._connect(True) as c:
        c.execute(
            "UPDATE artifacts SET digest=? WHERE artifact_id=?",
            (hashlib.sha256(content).hexdigest(), identity),
        )
    with pytest.raises(ContractError, match="authentication"):
        maintenance.restore(scope, identity)
