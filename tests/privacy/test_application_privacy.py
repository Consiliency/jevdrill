import json
from pathlib import Path

from jevdrill.application import Application
from jevdrill.storage import SQLiteStorage


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
