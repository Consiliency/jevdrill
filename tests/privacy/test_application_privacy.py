import json
import sqlite3
import time
from pathlib import Path
from uuid import uuid4

import pytest

from jevdrill.application import Application
from jevdrill.contracts import ContractError
from jevdrill.integrations.development import DevelopmentJudge
from jevdrill.storage import SQLiteStorage
from tests.application.test_route_integration import inputs, policy
from tests.privacy.test_context_privacy import (
    DOUBLED_QUOTE_EXPLICIT_KEY_CASES,
    ESCAPED_LOCAL_RECORD_CASES,
    EXPLICIT_KEY_REPAIR_CASES,
    PROSE_EXPLICIT_KEY_CASES,
    PUBLIC_NEL_MEMBER,
    QUOTE_KEY_CROSS_PRODUCT,
)


@pytest.mark.parametrize(
    "field",
    (
        "route_task",
        "route_attachment",
        "work_objective_text",
        "authorized_context",
        "description",
        "attachment_refs",
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_local_escaped_labels_and_public_nel_at_six_sanitize_boundaries(field, presentation):
    from jevdrill.application import _sanitize

    credential = ESCAPED_LOCAL_RECORD_CASES[0]
    public = PUBLIC_NEL_MEMBER
    if presentation == "json":
        credential, public = json.dumps(credential), json.dumps(public)
    elif presentation == "json-log":
        credential, public = json.dumps({"log": credential}), json.dumps({"log": public})
    elif presentation == "backtick":
        credential, public = f"`{credential}`", f"`{public}`"
    with pytest.raises(ContractError):
        _sanitize({field: credential})
    assert _sanitize({field: public}) == {field: public}


@pytest.mark.parametrize(
    "text", EXPLICIT_KEY_REPAIR_CASES + PROSE_EXPLICIT_KEY_CASES + QUOTE_KEY_CROSS_PRODUCT
)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
@pytest.mark.parametrize(
    "field",
    (
        "route_task",
        "route_attachment",
        "work_objective_text",
        "authorized_context",
        "description",
        "attachment_refs",
    ),
)
def test_computed_explicit_keys_reject_before_dispatch_and_retention(
    tmp_path, text, presentation, field
):
    text = (
        text
        if presentation == "plain"
        else json.dumps(text)
        if presentation == "json"
        else json.dumps({"log": text})
        if presentation == "json-log"
        else f"`{text}`"
    )
    service = DevelopmentJudge(
        tmp_path / "judgment.db",
        scope={
            "project_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "producer": "synthetic-review",
            "operation": "discover",
        },
        authorization_revision="synthetic-review-only",
        max_calls=3,
        total_spend_microusd=8259,
        deadline_ms=int(time.time() * 1000) + 15_000,
        credential=lambda: "synthetic-local-only",
        authorize=lambda scope: True,
        base_url="http://127.0.0.1:1/v1",
    )
    attachment = {
        "reference": "public.txt",
        "authorized": True,
        "modality": "document",
        "representation_source": "supplied",
        "text_representation": text,
    }
    storage = SQLiteStorage(tmp_path / "route.db")
    with pytest.raises(ContractError, match="computed explicit key|escaped literal credential"):
        if field.startswith("route_"):
            payload = inputs()
            payload["judgment_policy"] = policy() | {"model_revision": service.model_revision}
            payload["inventory"]["candidates"][0]["quality_sufficient"] = None
            payload["settings_layers"] = [
                {"source": "request", "values": {"retain_raw_tasks": True}}
            ]
            payload["request"]["task_representation"] = (
                text if field == "route_task" else "Ordinary task"
            )
            if field == "route_attachment":
                payload["request"]["attachment_refs"] = [attachment]
            Application(storage, judgments=service).route(payload)
        else:
            payload = json.loads(
                (Path(__file__).parents[1] / "contracts/fixtures/discovery.json").read_text()
            )[0]["payload"]
            payload["catalog"]["resources"] = payload["catalog"]["resources"][:1]
            payload["descriptions"] = payload["descriptions"][:1]
            payload["judgment_policy"].update(
                model_revision=service.model_revision,
                max_input_tokens=200000,
                output_planning_reservation=0,
            )
            payload["limits"].update(
                max_input_tokens=200000, output_planning_reservation=0, max_rounds=1
            )
            payload["hard_constraints"]["context_token_limit"] = 200000
            payload["settings_layers"].append(
                {"source": "request", "values": {"retain_raw_tasks": True}}
            )
            if field == "description":
                payload["descriptions"][0]["description"] = text
            elif field == "attachment_refs":
                payload[field] = [attachment]
            else:
                payload[field] = text
            Application(storage, discovery_judgments=service).discover(payload)
    with sqlite3.connect(service.path) as db:
        assert db.execute("SELECT COUNT(*) FROM judgment_calls").fetchone()[0] == 0
    assert not (tmp_path / "artifacts").exists()
    assert all(b"SYNTHETIC_SENTINEL" not in path.read_bytes() for path in tmp_path.glob("*.db*"))


@pytest.mark.parametrize(
    "field",
    (
        "route_task",
        "route_attachment",
        "work_objective_text",
        "authorized_context",
        "description",
        "attachment_refs",
    ),
)
def test_local_escaped_labels_reject_before_six_application_effect_boundaries(tmp_path, field):
    test_computed_explicit_keys_reject_before_dispatch_and_retention(
        tmp_path, ESCAPED_LOCAL_RECORD_CASES[0], "plain", field
    )


@pytest.mark.parametrize("text", DOUBLED_QUOTE_EXPLICIT_KEY_CASES)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
@pytest.mark.parametrize(
    "field",
    (
        "route_task",
        "route_attachment",
        "work_objective_text",
        "authorized_context",
        "description",
        "attachment_refs",
    ),
)
def test_doubled_quote_keys_reject_before_dispatch_and_retention(
    tmp_path, text, presentation, field
):
    test_computed_explicit_keys_reject_before_dispatch_and_retention(
        tmp_path, text, presentation, field
    )


def test_private_context_is_excluded_before_provider_and_retention(tmp_path):
    payload = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]
    payload["request"]["task_representation"] = "password=PRIVATE_SENTINEL ordinary task"
    payload["request"]["attachment_refs"] = [
        {
            "reference": "/private/data",
            "authorized": True,
            "modality": "document",
            "text_representation": "PRIVATE_ATTACHMENT",
            "representation_source": "synthetic",
        }
    ]
    payload["settings_layers"] = [
        {
            "source": "project",
            "values": {
                "excluded_paths": ["/private"],
                "retain_raw_tasks": False,
                "retain_raw_outputs": False,
            },
        }
    ]

    class NeverJudge:
        def judge(self, *args):
            raise AssertionError("excluded context sent")

    store = SQLiteStorage(tmp_path / "route.db")
    response = Application(store, judgments=NeverJudge()).route(payload)
    assert response["status"] == "needs_context"
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert b"PRIVATE_SENTINEL" not in path.read_bytes()
            assert b"PRIVATE_ATTACHMENT" not in path.read_bytes()
