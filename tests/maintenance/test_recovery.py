import json

import pytest
from cryptography.fernet import Fernet

from jevdrill.contracts import ContractError
from jevdrill.integrations.archive import decrypt_archive, encode_archive
from jevdrill.maintenance import DAY, Maintenance
from jevdrill.storage import SQLiteStorage
from tests.analysis.test_observations import case
from tests.retention.test_retention import artifact, request


def recovery(scope, key, action="export", bundle=None):
    return {
        "schema_version": "1",
        "scope": scope,
        "action": action,
        "artifact_id": None,
        "encrypted_bundle": bundle,
        "recovery_key": key.decode(),
    }


def test_portable_export_backup_import_preserves_lineage_and_deletion_precedes_sources(
    tmp_path, discovery_inputs
):
    app, scope, context, _ = case(tmp_path, discovery_inputs)
    artifact(app, scope, context)
    key = Fernet.generate_key()
    maintenance = Maintenance(app.storage)
    exported = maintenance.recover(recovery(scope, key))
    body = json.loads(decrypt_archive(exported["encrypted_bundle"].encode(), key))
    assert body["discoveries"][0]["discovery_ref"] == context["discovery_ref"]
    assert "assembled_instructions" not in body["discoveries"][0]
    target = SQLiteStorage(tmp_path / "import.db")
    destination = Maintenance(target)
    assert (
        destination.recover(recovery(scope, key, "import", exported["encrypted_bundle"]))[
            "restored_count"
        ]
        == 1
    )
    assert (
        target.learning_observations(scope)[0]["source"]["discovery_ref"]
        == context["discovery_ref"]
    )
    target.delete_discovery(
        dict(scope, operation="discover", producer="other"),
        context["discovery_ref"]["work_objective_id"],
    )
    destination.recover(recovery(scope, key, "import", exported["encrypted_bundle"]))
    assert target.learning_observations(scope) == []
    assert target.load_replay(scope, context["routing_decision_id"]) is not None
    target.delete_task(scope, context["task_id"])
    destination.recover(recovery(scope, key, "import", exported["encrypted_bundle"]))
    assert (
        target.is_deleted(scope, context["task_id"])
        and target.load_replay(scope, context["routing_decision_id"]) is None
    )
    tombstoned = json.loads(
        decrypt_archive(
            destination.recover(recovery(scope, key, "backup"))["encrypted_bundle"].encode(), key
        )
    )
    assert (
        tombstoned["tasks"][context["task_id"]]
        and tombstoned["objectives"][context["discovery_ref"]["work_objective_id"]]
    )


@pytest.mark.parametrize(
    "mutation", ["tamper", "digest", "context", "scope", "decision_conflict", "correction"]
)
def test_malformed_or_conflicting_import_rejects_transactionally(tmp_path, mutation):
    app, scope, context, _ = case(tmp_path)
    artifact(app, scope, context)
    key = Fernet.generate_key()
    maintenance = Maintenance(app.storage)
    exported = maintenance.recover(recovery(scope, key))["encrypted_bundle"]
    body = json.loads(decrypt_archive(exported.encode(), key))
    body["tasks"][context["task_id"]] = True
    if mutation == "tamper":
        encrypted = exported[:-2] + "aa"
    else:
        if mutation == "digest":
            body["artifacts"][0]["digest"] = "0" * 64
        elif mutation == "context":
            body["contexts"][0]["task_group"] = "forged"
        elif mutation == "scope":
            body["scope"] = "[]"
        elif mutation == "decision_conflict":
            body["decisions"][0]["bundle"]["decision"]["details"]["human_summary"] = "changed"
        elif mutation == "correction":
            from uuid import uuid4

            from tests.analysis.test_observations import report

            event = report(
                app,
                scope,
                context,
                str(uuid4()),
                {
                    "kind": "lifecycle",
                    "event_type": "completed",
                    "applied_plan_id": None,
                    "reason": None,
                },
            )
            body["events"] = [
                {
                    "scope": dict(scope, operation="report"),
                    "event": dict(event, event_id=str(uuid4()), supersedes_event_id=str(uuid4())),
                }
            ]
        encrypted = encode_archive(body, key).decode()
    with pytest.raises(ContractError):
        maintenance.recover(recovery(scope, key, "import", encrypted))
    assert not app.storage.is_deleted(scope, context["task_id"])
    assert app.storage.load_replay(scope, context["routing_decision_id"]) is not None


def test_imported_optout_never_reenables_analysis_or_policy_validation(tmp_path):
    app, scope, context, _ = case(tmp_path)
    key = Fernet.generate_key()
    maintenance = Maintenance(app.storage)
    before = maintenance.recover(recovery(scope, key))["encrypted_bundle"]
    app.storage.restrict_learning(scope, context["task_id"], False)
    maintenance.recover(recovery(scope, key, "import", before))
    assert app.storage.learning_observations(scope) == []
    with app.storage._connect() as c:
        assert (
            c.execute(
                "SELECT stale FROM policy_validation WHERE scope=?",
                (app.storage._task_scope(scope),),
            ).fetchone()[0]
            == 1
        )


def test_native_archive_restore_and_portable_archive_export(tmp_path):
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
    portable = Fernet.generate_key()
    exported = maintenance.recover(recovery(scope, portable))
    body = json.loads(decrypt_archive(exported["encrypted_bundle"].encode(), portable))
    assert body["artifacts"][0]["kind"] == "raw_task"
    assert maintenance.restore(scope, identity) == 1
    app.storage.delete_task(scope, context["task_id"])
    with pytest.raises(ContractError):
        maintenance.restore(scope, identity)
