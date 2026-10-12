import copy
import json
from pathlib import Path

import pytest


@pytest.fixture
def discovery_inputs():
    path = Path(__file__).parent / "contracts/fixtures/discovery.json"
    return copy.deepcopy(json.loads(path.read_text())[0]["payload"])


@pytest.fixture
def discovery_observer():
    class Observer:
        def __init__(self):
            self.calls = []
            self.answer = lambda task, option: (
                option["level"] != "resource"
                or json.loads(task)["objective"] in (option["description"] or "")
            )

        def observe_option(self, task, offered, question_digest, option_id, deadline):
            option = json.loads(offered)
            self.calls.append(option)
            return {
                "schema_version": "1",
                "function_revision": "ObserveDiscoveryOption-v1",
                "model_revision": "jev-latest",
                "question_digest": question_digest,
                "judgments": {option_id: self.answer(task, option)},
                "measurements": [],
            }

    return Observer()
