import copy
import json
from pathlib import Path

import pytest

FORMATS = {
    "json-name": lambda label: json.dumps({"name": label, "value": "SYNTHETIC_SENTINEL"}),
    "json-key": lambda label: json.dumps({"key": label, "payload": "SYNTHETIC_SENTINEL"}),
    "json-pairs": lambda label: json.dumps([[label, "SYNTHETIC_SENTINEL"]]),
    "json-duplicate": lambda label: (
        '{"name":' + json.dumps(label) + ',"value":"SYNTHETIC_SENTINEL","value":"[redacted]"}'
    ),
    "json-string": lambda label: json.dumps(
        json.dumps({"name": label, "value": "SYNTHETIC_SENTINEL"})
    ),
    "nested-string": lambda label: json.dumps(
        {"log": json.dumps(json.dumps({"name": label, "value": "SYNTHETIC_SENTINEL"}))}
    ),
    "yaml": lambda label: f'- name: "{label}"\n  value: SYNTHETIC_SENTINEL',
    "python": lambda label: repr({"name": label, "value": "SYNTHETIC_SENTINEL"}),
    "assignment": lambda label: f'headers[{json.dumps(label)}] = "SYNTHETIC_SENTINEL"',
    "plain": lambda label: f"{label}: correct horse SYNTHETIC_SENTINEL \r\n\tcontinued",
    "encoded-label": lambda label: json.dumps(
        {
            "header": json.dumps(label, ensure_ascii=True).replace("A", "\\u0041"),
            "payload": "SYNTHETIC_SENTINEL",
        }
    ),
    "credential-key": lambda label: json.dumps({label + " Bearer SYNTHETIC_SENTINEL": "x"}),
    "comment": lambda label: f"ordinary: context\n# {label}: SYNTHETIC_SENTINEL",
    "inline-comment": lambda label: f"ordinary: context # {label}: SYNTHETIC_SENTINEL",
    "comment-record": lambda label: (
        "ordinary: context\n# " + json.dumps({"header": label, "payload": "SYNTHETIC_SENTINEL"})
    ),
    "mixed-yaml": lambda label: f"Header for request.\nlabel: {label}\npayload: SYNTHETIC_SENTINEL",
    "mixed-yaml-reversed": lambda label: (
        f"Header for request.\npayload: SYNTHETIC_SENTINEL\nheader: {label}"
    ),
    "mixed-yaml-block": lambda label: (
        f"Header for request.\nheader: >\n  {label}\npayload: SYNTHETIC_SENTINEL"
    ),
    "scalar-alias": lambda label: (
        f"header:\n  name: {label}\n  value: &s SYNTHETIC_SENTINEL\ncopy: *s"
    ),
    "sequence-alias": lambda label: f"token: &s SYNTHETIC_SENTINEL\nheaders:\n  - {label}\n  - *s",
    "merge": lambda label: (
        f"defaults: &d\n  name: {label}\nheader:\n  <<: *d\n  value: SYNTHETIC_SENTINEL"
    ),
    "tag": lambda label: f'!!map {{"header": "{label}", "payload": "SYNTHETIC_SENTINEL"}}',
    "multiline-assignment": lambda label: (
        f'headers[{json.dumps(label)}] = """prefix\nSYNTHETIC_SENTINEL\n"""'
    ),
    "continued-assignment": lambda label: (
        f'headers[{json.dumps(label)}] = \\\n"SYNTHETIC_SENTINEL"'
    ),
}
LABELS = [
    "Authorization",
    "X-API-Key",
    "client_secret",
    "X-Goog-Api-Key",
    " access_token ",
    "PASSWORD",
]
UNSUPPORTED_CONTEXT = {
    formatter(label)
    for name, formatter in FORMATS.items()
    for label in LABELS
    if name
    in {
        "yaml",
        "python",
        "mixed-yaml",
        "mixed-yaml-reversed",
        "mixed-yaml-block",
        "scalar-alias",
        "sequence-alias",
        "merge",
        "tag",
        "multiline-assignment",
        "continued-assignment",
    }
}
WHOLE_CONTEXT = {
    formatter(label)
    for name, formatter in FORMATS.items()
    for label in LABELS
    if name in {"encoded-label", "credential-key", "comment", "inline-comment", "comment-record"}
}


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
        'Authorization: "prefix" \r\n\tSYNTHETIC_SENTINEL',
        "Authorization: 'prefix'\t\n\tSYNTHETIC_SENTINEL",
        "api_key: prefix \r\n\tSYNTHETIC_SENTINEL",
        "password: correct horse SYNTHETIC_SENTINEL",
        '{"name":"Authorization","value":"SYNTHETIC_SENTINEL","name":"Content-Type"}',
        '{"name":"Authorization","Name":"Content-Type","value":"SYNTHETIC_SENTINEL"}',
        '{"name":"Authorization","na_me":"Content-Type","value":"SYNTHETIC_SENTINEL"}',
        '{"name":"Authorization ","value":"SYNTHETIC_SENTINEL"}',
    ]
    + [
        pytest.param(formatter(label), id=f"{label.strip()}-{name}")
        for name, formatter in FORMATS.items()
        for label in LABELS
    ]
)
def credential_text(request):
    return request.param


@pytest.fixture
def credential_may_reject(credential_text):
    return credential_text in UNSUPPORTED_CONTEXT


@pytest.fixture
def credential_whole(credential_text):
    return credential_text in WHOLE_CONTEXT


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
