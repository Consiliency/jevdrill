import json
from pathlib import Path

import pytest

from jevdrill.application import Application
from jevdrill.contracts import canonical_digest
from jevdrill.storage import SQLiteStorage
from tests.application.test_route_integration import inputs, policy


@pytest.mark.parametrize(
    "text",
    (
        "Ordinary task. Keep the public instructions.",
        "Don't [['Content-Type', 'application/json']]",
    ),
)
def test_round27_public_controls_dispatch_unchanged(tmp_path, text):
    calls = []

    class CapturingJudge:
        def judge(self, task, candidates, deadline):
            calls.append(task)
            return {
                "schema_version": "1",
                "function_revision": "JudgeCandidate-v2",
                "model_revision": "jev-latest",
                "candidate_digest": canonical_digest(list(candidates)),
                "judgments": {row["candidate_id"]: True for row in candidates},
                "measurements": [],
            }

    payload = inputs()
    payload["judgment_policy"] = policy()
    payload["inventory"]["candidates"][0]["quality_sufficient"] = None
    payload["request"]["task_representation"] = text
    response = Application(SQLiteStorage(tmp_path / "route.db"), judgments=CapturingJudge()).route(
        payload
    )
    assert response["status"] == "ready"
    assert len(calls) == 1
    assert text in calls[0]


def test_private_context_is_excluded_before_provider_and_retention(tmp_path):
    payload = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]
    payload["request"]["task_representation"] = "PRIVATE_SENTINEL ordinary task"
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
