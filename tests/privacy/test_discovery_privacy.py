import json

import pytest
from cryptography.fernet import Fernet

from jevdrill.application import Application
from jevdrill.contracts import ContractError
from jevdrill.maintenance import DAY, Maintenance
from jevdrill.storage import SQLiteStorage
from tests.retention.test_retention import request


@pytest.mark.parametrize(
    "field", ["work_objective_text", "authorized_context", "description", "attachment_refs"]
)
def test_folded_credentials_never_reach_discovery_judgment_or_retention(
    tmp_path, discovery_inputs, discovery_observer, credential_text, credential_may_reject, field
):
    if field == "attachment_refs":
        discovery_inputs[field] = [
            {
                "reference": "public.txt",
                "authorized": True,
                "modality": "document",
                "representation_source": "supplied",
                "text_representation": credential_text,
            }
        ]
    elif field == "description":
        discovery_inputs["descriptions"][0][field] += "\n" + credential_text
    else:
        discovery_inputs[field] += "\n" + credential_text
    discovery_inputs["settings_layers"].append(
        {"source": "request", "values": {"retain_raw_tasks": True}}
    )
    calls = []

    def answer(task, option):
        calls.append(task)
        return True

    discovery_observer.answer = answer
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    try:
        app.discover(discovery_inputs)
    except ContractError:
        assert credential_may_reject
        assert not calls and not discovery_observer.calls
        assert b"SYNTHETIC_SENTINEL" not in (tmp_path / "route.db").read_bytes()
        assert not [p for p in (tmp_path / "artifacts").rglob("*") if p.is_file()]
        return
    assert calls and "SYNTHETIC_SENTINEL" not in json.dumps(calls)
    assert "SYNTHETIC_SENTINEL" not in json.dumps(discovery_observer.calls)
    artifacts = [p for p in (tmp_path / "artifacts").rglob("*") if p.is_file()]
    assert artifacts
    assert all(b"SYNTHETIC_SENTINEL" not in p.read_bytes() for p in artifacts)
    assert b"SYNTHETIC_SENTINEL" not in (tmp_path / "route.db").read_bytes()


def test_retained_discovery_content_archives_expires_and_does_not_return_on_retry(
    tmp_path, discovery_inputs, discovery_observer, monkeypatch
):
    monkeypatch.setattr("jevdrill.storage.time", lambda: 100)
    discovery_inputs["work_objective_text"] += " discovery-private-sentinel"
    discovery_inputs["settings_layers"].append(
        {"source": "request", "values": {"retain_raw_tasks": True}}
    )
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    result = app.discover(discovery_inputs)
    envelope = discovery_inputs["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "discover",
    }
    with app.storage._connect() as db:
        identity = db.execute("SELECT artifact_id FROM artifacts WHERE kind='raw_task'").fetchone()[
            0
        ]
        assert "discovery-private-sentinel" not in str(
            db.execute("SELECT seed,trace FROM discoveries").fetchall()
        )
    directory = app.storage._artifact_directory(app.storage._task_scope(scope))
    assert b"discovery-private-sentinel" in (directory / identity).read_bytes()
    now = [100 + 30 * DAY]
    key = Fernet.generate_key()
    maintenance = Maintenance(app.storage, lambda _: key, lambda: now[0])
    assert app.storage.export_recovery(scope)["artifacts"] == []
    maintenance_scope = scope | {"operation": "route", "producer": "maintenance"}
    assert maintenance.run(request(maintenance_scope))["notices"]
    now[0] += 7 * DAY
    assert maintenance.run(request(maintenance_scope))["processed"] == 1
    assert not (directory / identity).exists()
    assert app.storage.export_recovery(scope)["artifacts"] == []
    now[0] += 365 * DAY
    assert maintenance.run(request(maintenance_scope))["processed"] == 1
    assert not list(directory.iterdir())
    assert app.inspect_discovery(scope, result["details"]["discovery_id"], True) == result
    assert app.discover(discovery_inputs) == result
    assert not list(directory.iterdir())


def test_objective_deletion_scrubs_retained_discovery_artifacts(
    tmp_path, discovery_inputs, discovery_observer
):
    discovery_inputs["settings_layers"].append(
        {"source": "request", "values": {"retain_raw_tasks": True}}
    )
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    result = app.discover(discovery_inputs)
    envelope = discovery_inputs["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "discover",
    }
    independent = app.storage.stage_artifact(
        scope,
        result["details"]["discovery_id"],
        b"independent task content",
        kind="raw_task",
        retention="active",
        encryption="none",
        retain_raw_tasks=True,
    )
    app.delete_discovery(scope, discovery_inputs["work_objective_id"])
    with app.storage._connect() as db:
        assert db.execute("SELECT artifact_id FROM artifacts").fetchall() == [(independent,)]
    assert not app.storage.is_deleted(scope, result["details"]["discovery_id"])


def test_objective_deletion_before_raw_staging_never_retains_content(
    tmp_path, discovery_inputs, discovery_observer, monkeypatch
):
    discovery_inputs["settings_layers"].append(
        {"source": "request", "values": {"retain_raw_tasks": True}}
    )
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    envelope = discovery_inputs["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "discover",
    }
    original = app.storage.stage_artifact

    def delete_before_stage(*args, **kwargs):
        app.delete_discovery(scope, discovery_inputs["work_objective_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(app.storage, "stage_artifact", delete_before_stage)
    with pytest.raises(ContractError, match="deleted"):
        app.discover(discovery_inputs)
    assert not discovery_observer.calls
    with app.storage._connect() as db:
        assert not db.execute("SELECT 1 FROM artifacts").fetchall()


def test_metadata_replay_has_no_raw_objective_description_or_provider_payload(
    tmp_path, discovery_inputs, discovery_observer
):
    discovery_inputs["work_objective_text"] = (
        "alpha objective-private-sentinel api_key=credential-sentinel"
    )
    discovery_inputs["descriptions"][0]["description"] += (
        " description-private-sentinel password=secret-sentinel"
    )
    discovery_inputs["authorized_context"] += " access_token=context-secret-sentinel"
    discovery_observer.answer = lambda task, option: (
        option["level"] != "resource" or "alpha" in (option["description"] or "")
    )
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    result = app.discover(discovery_inputs)
    assert result["status"] == "selected_guidance"
    serialized = json.dumps(discovery_observer.calls)
    assert "secret-sentinel" not in serialized and "credential-sentinel" not in serialized
    with app.storage._connect() as connection:
        rows = connection.execute("SELECT seed,result,trace FROM discoveries").fetchall()
        questions = connection.execute("SELECT question FROM discovery_rounds").fetchall()
    stored = json.dumps([rows, questions])
    for sentinel in (
        "objective-private-sentinel",
        "description-private-sentinel",
        "credential-sentinel",
        "context-secret-sentinel",
        "secret-sentinel",
    ):
        assert sentinel not in stored
    envelope = discovery_inputs["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "discover",
    }
    discovery_inputs["catalog"]["resources"] = []
    assert app.inspect_discovery(scope, result["details"]["discovery_id"], True) == result


@pytest.mark.parametrize("restriction", ["local", "provider", "cloud", "hard_output", "spend"])
def test_discovery_forbidden_provider_traffic_never_dispatches(
    tmp_path, discovery_inputs, discovery_observer, restriction
):
    if restriction == "local":
        discovery_inputs["hard_constraints"]["local_only"] = True
    elif restriction == "provider":
        discovery_inputs["hard_constraints"]["allowed_providers"] = ["local"]
    elif restriction == "cloud":
        discovery_inputs["judgment_policy"]["cloud_allowed"] = False
    elif restriction == "hard_output":
        discovery_inputs["limits"]["hard_output_token_limit"] = 1
    else:
        discovery_inputs["limits"]["spending_ceiling"] = {"amount": "1", "currency": "USD"}
    result = Application(
        SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer
    ).discover(discovery_inputs)
    assert result["status"] == "discovery_failed"
    assert not discovery_observer.calls
