import copy
import json
from pathlib import Path

import pytest


@pytest.fixture(
    params=[
        "Authorization: Bearer SYNTHETIC_SENTINEL",
        'Authorization: "Bearer SYNTHETIC_SENTINEL"',
        '"Authorization": "Bearer SYNTHETIC_SENTINEL"',
        '{"api_key": "SYNTHETIC_SENTINEL"}',
        "Authorization: Digest username=SYNTHETIC_SENTINEL, nonce=SYNTHETIC_SENTINEL",
        "'password': 'SYNTHETIC_SENTINEL with spaces'",
        '{"name":"Authorization","value":"Bearer SYNTHETIC_SENTINEL"}',
        "Authorization: >\n  Bearer SYNTHETIC_SENTINEL",
        "Bearer SYNTHETIC_SENTINEL",
        '{"name":"Authorization","value":"Basic SYNTHETIC_SENTINEL"}',
        "Authorization: Bearer\r\n\tSYNTHETIC_SENTINEL",
        "Authorization: Basic\r\n\tSYNTHETIC_SENTINEL",
        "Authorization: Bearer\n  SYNTHETIC_SENTINEL",
        "Authorization: Basic\n  SYNTHETIC_SENTINEL",
        '{"name":"X-API-Key","value":"SYNTHETIC_SENTINEL"}',
        '{"value":"SYNTHETIC_SENTINEL","name":"X-API-Key"}',
        json.dumps({"name": "Authorization", "value": 'Digest response="SYNTHETIC_SENTINEL"'}),
        json.dumps({"name": "Authorization", "value": "Bearer\r\n\tSYNTHETIC_SENTINEL"}),
        json.dumps({"name": "Authorization", "value": "Basic\n  SYNTHETIC_SENTINEL"}),
        '{"name":"Authorization","value":"Negotiate SYNTHETIC_SENTINEL"}',
        '{"name":"Authorization","value":"token SYNTHETIC_SENTINEL"}',
        '[{"name":"Authorization","value":"SYNTHETIC_SENTINEL"}]',
        r'{"n\u0061me":"Authoriz\u0061tion","value":"SYNTHETIC_SENTINEL"}',
        "Authorization: Bearer\r\n \r\n\tSYNTHETIC_SENTINEL",
        "Authorization: Bearer\n \n\tSYNTHETIC_SENTINEL",
        'Authorization: "placeholder"\r\n\tSYNTHETIC_SENTINEL',
        "Authorization: 'placeholder'\r\n\tSYNTHETIC_SENTINEL",
        "Authorization: Bearer\r\tSYNTHETIC_SENTINEL",
        "Authorization: Bearer\n\u00a0SYNTHETIC_SENTINEL",
        "Authorization: Bearer\n\vSYNTHETIC_SENTINEL",
        "api_key: prefix\r\n\tSYNTHETIC_SENTINEL",
        "password: prefix\r\n\tSYNTHETIC_SENTINEL",
        "secret: 'prefix'\n \n\tSYNTHETIC_SENTINEL",
        "access_token: prefix\r\tSYNTHETIC_SENTINEL",
    ]
)
def credential_text(request):
    return request.param


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
