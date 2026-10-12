import json

import pytest

from jevdrill.application import Application
from jevdrill.storage import SQLiteStorage


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
