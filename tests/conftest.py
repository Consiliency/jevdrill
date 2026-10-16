import copy
import json
import shutil
from pathlib import Path

import pytest

from jevdrill.storage import SQLiteStorage

OPERATORS = ("+", "-", "*", "/", "%", "@", "&", "|", "^", ">>", "<<", "**", "//")

FORMATS = {
    "json-name": lambda label: json.dumps({"name": label, "value": "SYNTHETIC_SENTINEL"}),
    "json-key": lambda label: json.dumps({"key": label, "payload": "SYNTHETIC_SENTINEL"}),
    "json-pairs": lambda label: json.dumps([[label, "SYNTHETIC_SENTINEL"]]),
    "yaml-block-pairs": lambda label: f"- {label.strip()}\n- SYNTHETIC_SENTINEL",
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
    "raw-multiline-assignment": lambda label: (
        f'headers[{json.dumps(label)}] = r"""prefix\nSYNTHETIC_SENTINEL\n"""'
    ),
    "formatted-multiline-assignment": lambda label: (
        f'headers[{json.dumps(label)}] = f"""prefix\nSYNTHETIC_SENTINEL\n"""'
    ),
    "bytes-multiline-assignment": lambda label: (
        f'headers[{json.dumps(label)}] = b"""prefix\nSYNTHETIC_SENTINEL\n"""'
    ),
    "call-multiline-assignment": lambda label: (
        f'headers[{json.dumps(label)}] = str(\n"SYNTHETIC_SENTINEL"\n)'
    ),
    "augmented-assignment": lambda label: "\n".join(
        f'headers[{json.dumps(label)}] {operator}= "SYNTHETIC_SENTINEL"' for operator in OPERATORS
    ),
    "augmented-multiline-assignment": lambda label: (
        f'headers[{json.dumps(label)}] += (\n    "SYNTHETIC_SENTINEL"\n)'
    ),
    "escaped-assignment-label": lambda label: (
        "headers['" + "".join(f"\\x{ord(char):02x}" for char in label) + "'] = 'SYNTHETIC_SENTINEL'"
    ),
    "sequence-key": lambda label: f"? [{json.dumps(label)}]\n: SYNTHETIC_SENTINEL",
    "continued-assignment-target": lambda label: (
        f'headers[{json.dumps(label)}] \\\n += "SYNTHETIC_SENTINEL"'
    ),
    "continued-escaped-target": lambda label: (
        "headers['"
        + "".join(f"\\x{ord(char):02x}" for char in label)
        + "'] \\\n = 'SYNTHETIC_SENTINEL'"
    ),
    "concatenated-assignment-target": lambda label: (
        "headers["
        + json.dumps(label[: len(label) // 2])
        + " "
        + json.dumps(label[len(label) // 2 :])
        + '] = "SYNTHETIC_SENTINEL"'
    ),
    "concatenated-literal-label": lambda label: (
        "{'name': "
        + repr(label[: len(label) // 2])
        + " "
        + repr(label[len(label) // 2 :])
        + ", 'value': 'SYNTHETIC_SENTINEL'}"
    ),
    "concatenated-literal-key": lambda label: (
        "{"
        + repr(label[: len(label) // 2])
        + " "
        + repr(label[len(label) // 2 :])
        + ": 'SYNTHETIC_SENTINEL'}"
    ),
    "concatenated-literal-pairs": lambda label: (
        "[["
        + repr(label[: len(label) // 2])
        + " "
        + repr(label[len(label) // 2 :])
        + ", 'SYNTHETIC_SENTINEL']]"
    ),
    "implicit-assignment-target": lambda label: (
        f'headers[\n{json.dumps(label)}\n] = "SYNTHETIC_SENTINEL"'
    ),
    "tuple-assignment-target": lambda label: (
        f'(ordinary,\nheaders[{json.dumps(label)}]\n) = ("x", "SYNTHETIC_SENTINEL")'
    ),
    "implicit-augmented-target": lambda label: (
        "headers[\n"
        + repr(label[: len(label) // 2])
        + " "
        + repr(label[len(label) // 2 :])
        + '\n] += "SYNTHETIC_SENTINEL"'
    ),
    "cr-assignment-target": lambda label: (
        "ordinary = 0\rheaders["
        + repr(label[: len(label) // 2])
        + " "
        + repr(label[len(label) // 2 :])
        + '] = "SYNTHETIC_SENTINEL"'
    ),
    "yaml-assignment-label": lambda label: (
        f'header: |\n  {label.strip().replace("-", "_")} = "placeholder"'
        "\npayload: SYNTHETIC_SENTINEL"
    ),
    "yaml-augmented-label": lambda label: (
        f'header: >\n  {label.strip().replace("-", "_")} += "placeholder"'
        "\npayload: SYNTHETIC_SENTINEL"
    ),
    "yaml-subscript-label": lambda label: (
        f'header: |\n  headers[{json.dumps(label)}] = "placeholder"\npayload: SYNTHETIC_SENTINEL'
    ),
    "mapping-key": lambda label: f"? {{name: {json.dumps(label)}}}\n: SYNTHETIC_SENTINEL",
    "escaped-literal-label": lambda label: (
        "{'name':'"
        + "".join(f"\\x{ord(char):02x}" for char in label)
        + "','value':'SYNTHETIC_SENTINEL'}"
    ),
    "unicode-literal-label": lambda label: (
        "{'name':'"
        + "".join(f"\\u{ord(char):04x}" for char in label)
        + "','value':'SYNTHETIC_SENTINEL'}"
    ),
    "escaped-literal-key": lambda label: (
        "{'" + "".join(f"\\x{ord(char):02x}" for char in label) + "':'SYNTHETIC_SENTINEL'}"
    ),
    "nbsp-block": lambda label: (
        f"Header for request.\nheader: |\n\u00a0\u00a0{label}\npayload: SYNTHETIC_SENTINEL"
    ),
    "vertical-tab-block": lambda label: (
        f"Header for request.\nheader: |\n\v\v{label}\npayload: SYNTHETIC_SENTINEL"
    ),
    "form-feed-block": lambda label: (
        f"Header for request.\nheader: |\n\f\f{label}\npayload: SYNTHETIC_SENTINEL"
    ),
    "formatted-literal-label": lambda label: (
        "{'name': f" + repr(label[:2]) + " f" + repr(label[2:]) + ", 'value': 'SYNTHETIC_SENTINEL'}"
    ),
    "formatted-literal-key": lambda label: (
        "{f" + repr(label[:2]) + " f" + repr(label[2:]) + ": 'SYNTHETIC_SENTINEL'}"
    ),
    "formatted-literal-pairs": lambda label: (
        "[[f" + repr(label[:2]) + " f" + repr(label[2:]) + ", 'SYNTHETIC_SENTINEL']]"
    ),
    "mixed-formatted-label": lambda label: (
        "{'name': " + repr(label[:2]) + " f" + repr(label[2:]) + ", 'value': 'SYNTHETIC_SENTINEL'}"
    ),
    "constant-literal-label": lambda label: (
        "{'name': " + repr(label[:2]) + " + " + repr(label[2:]) + ", 'value': 'SYNTHETIC_SENTINEL'}"
    ),
    "constant-literal-key": lambda label: (
        "{" + repr(label[:2]) + " + " + repr(label[2:]) + ": 'SYNTHETIC_SENTINEL'}"
    ),
    "constant-assignment-target": lambda label: (
        "headers[" + repr(label[:2]) + " + " + repr(label[2:]) + "] = 'SYNTHETIC_SENTINEL'"
    ),
    "bytes-constant-target": lambda label: (
        "headers[b" + repr(label[:2]) + " + b" + repr(label[2:]) + "] = 'SYNTHETIC_SENTINEL'"
    ),
    "formatted-assignment-target": lambda label: (
        "headers[f" + repr(label[:2]) + " f" + repr(label[2:]) + "] = 'SYNTHETIC_SENTINEL'"
    ),
    "formatted-replacement-label": lambda label: (
        "{'name': f\"{"
        + repr(label[:2])
        + "}{"
        + repr(label[2:])
        + "}\", 'value': 'SYNTHETIC_SENTINEL'}"
    ),
    "call-assignment-target": lambda label: (
        "headers[''.join(("
        + repr(label[:2])
        + ", "
        + repr(label[2:])
        + "))] = 'SYNTHETIC_SENTINEL'"
    ),
    "call-literal-label": lambda label: (
        "{'name': ''.join(("
        + repr(label[:2])
        + ", "
        + repr(label[2:])
        + ")), 'value': 'SYNTHETIC_SENTINEL'}"
    ),
    **{
        f"{name}-{ending}": lambda label, separator=separator, shape=shape: separator.join(
            shape(label)
        )
        for ending, separator in (
            ("lf", "\n"),
            ("crlf", "\r\n"),
            ("cr", "\r"),
            ("nel", "\x85"),
            ("ls", "\u2028"),
            ("ps", "\u2029"),
        )
        for name, shape in (
            (
                "mixed-fields",
                lambda label: [
                    "Ordinary context.",
                    "header: " + label,
                    "payload: SYNTHETIC_SENTINEL",
                ],
            ),
            (
                "mixed-reversed",
                lambda label: [
                    "Ordinary context.",
                    "payload: SYNTHETIC_SENTINEL",
                    "header: " + label,
                ],
            ),
            (
                "mixed-sequence",
                lambda label: ["Ordinary context.", "- " + label.strip(), "- SYNTHETIC_SENTINEL"],
            ),
            (
                "mixed-dash-only",
                lambda label: [
                    "Ordinary context.",
                    "-",
                    "  " + label.strip(),
                    "- SYNTHETIC_SENTINEL",
                ],
            ),
            ("tab-dash-only", lambda label: ["-", "\t" + label.strip(), "- SYNTHETIC_SENTINEL"]),
        )
    },
}
COMPUTED_FORMATS = {
    f"computed-{shape}-{expression}": lambda label, template=template, expression=expression: (
        template.format(
            label=(
                "+".join(f"chr({ord(char)})" for char in label)
                if expression == "numeric"
                else "str(" + repr(label[:2]) + ") + str(" + repr(label[2:]) + ")"
            )
        )
    )
    for expression in ("numeric", "calls")
    for shape, template in (
        ("mapping", "{{'name': {label}, 'value': 'SYNTHETIC_SENTINEL'}}"),
        ("key", "{{{label}: 'SYNTHETIC_SENTINEL'}}"),
        ("pair", "[[{label}, 'SYNTHETIC_SENTINEL']]"),
        ("target", "headers[{label}] = 'SYNTHETIC_SENTINEL'"),
    )
}
COMPUTED_FORMATS.update(
    {
        "computed-bare-call": lambda label: (
            "{'name': header_name(), 'value': 'SYNTHETIC_SENTINEL'}"
        ),
        "computed-bare-target": lambda label: "headers[header_name()] = 'SYNTHETIC_SENTINEL'",
        "computed-names": lambda label: "{'name': prefix + suffix, 'value': 'SYNTHETIC_SENTINEL'}",
        "computed-names-target": lambda label: "headers[prefix + suffix] = 'SYNTHETIC_SENTINEL'",
        "computed-slice": lambda label: "{'name': header_name[:], 'value': 'SYNTHETIC_SENTINEL'}",
        "computed-lookup": lambda label: "{'name': config['field'], 'value': 'SYNTHETIC_SENTINEL'}",
        "computed-json-association": lambda label: json.dumps(
            {
                "name": "headers[" + repr(label[:2]) + "+" + repr(label[2:]) + "] = 'placeholder'",
                "value": "SYNTHETIC_SENTINEL",
            }
        ),
        "computed-yaml-association": lambda label: (
            "header: |\n  headers["
            + repr(label[:2])
            + "+"
            + repr(label[2:])
            + "] = 'placeholder'\npayload: SYNTHETIC_SENTINEL"
        ),
        "computed-attribute": lambda label: (
            "{'name': config.header, 'value': 'SYNTHETIC_SENTINEL'}"
        ),
        "computed-conditional": lambda label: (
            "{'name': first if selected else second, 'value': 'SYNTHETIC_SENTINEL'}"
        ),
        "computed-boolean": lambda label: (
            "{'name': first or second, 'value': 'SYNTHETIC_SENTINEL'}"
        ),
    }
)
INLINE_FORMATS = {
    f"inline-{placement}-{name}": lambda label, formatter=formatter, prefix=prefix, suffix=suffix: (
        prefix + formatter(label) + suffix
    )
    for placement, prefix, suffix in (
        ("prose", "Please inspect: ", " End notes."),
        ("markdown", "`", "`"),
    )
    for name, formatter in (
        list(COMPUTED_FORMATS.items())
        + [
            (name, FORMATS[name])
            for name in (
                "constant-literal-label",
                "constant-literal-key",
                "constant-assignment-target",
                "formatted-literal-label",
                "formatted-literal-key",
                "formatted-literal-pairs",
                "formatted-assignment-target",
                "formatted-replacement-label",
                "call-literal-label",
            )
        ]
    )
}
INLINE_FORMATS.update(
    {
        f"inline-nested-{name}": lambda label, formatter=formatter: (
            "Please [note " + formatter(label) + "]"
        )
        for name, formatter in (
            ("constant", FORMATS["constant-literal-label"]),
            ("formatted", FORMATS["formatted-literal-label"]),
            ("numeric", COMPUTED_FORMATS["computed-mapping-numeric"]),
        )
    }
)
FORMATS.update(COMPUTED_FORMATS)
FORMATS.update(INLINE_FORMATS)
SCHEME_FOLDS = {
    f"{scheme}-{ending}-{blank}": (
        "  "
        + scheme
        + separator
        + "  prefix"
        + (separator + " " if blank else "")
        + separator
        + "\tSYNTHETIC_SENTINEL"
        + separator
        + "Ordinary context"
    )
    for scheme in ("Basic", "Bearer")
    for ending, separator in (
        ("lf", "\n"),
        ("crlf", "\r\n"),
        ("cr", "\r"),
        ("nel", "\x85"),
        ("ls", "\u2028"),
        ("ps", "\u2029"),
    )
    for blank in (False, True)
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
    if name in COMPUTED_FORMATS
    or name in INLINE_FORMATS
    or name.startswith(
        (
            "mixed-fields-",
            "mixed-reversed-",
            "mixed-sequence-",
            "mixed-dash-only-",
            "tab-dash-only-",
        )
    )
    or name
    in {
        "yaml",
        "yaml-block-pairs",
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
        "raw-multiline-assignment",
        "formatted-multiline-assignment",
        "bytes-multiline-assignment",
        "call-multiline-assignment",
        "augmented-multiline-assignment",
        "sequence-key",
        "mapping-key",
        "concatenated-literal-label",
        "concatenated-literal-key",
        "concatenated-literal-pairs",
        "implicit-assignment-target",
        "tuple-assignment-target",
        "implicit-augmented-target",
        "yaml-assignment-label",
        "yaml-augmented-label",
        "yaml-subscript-label",
        "escaped-literal-label",
        "unicode-literal-label",
        "escaped-literal-key",
        "nbsp-block",
        "vertical-tab-block",
        "form-feed-block",
        "formatted-literal-label",
        "formatted-literal-key",
        "formatted-literal-pairs",
        "mixed-formatted-label",
        "constant-literal-label",
        "constant-literal-key",
        "formatted-replacement-label",
        "call-assignment-target",
        "call-literal-label",
    }
}
WHOLE_CONTEXT = {
    formatter(label)
    for name, formatter in FORMATS.items()
    for label in LABELS
    if name
    in {
        "encoded-label",
        "credential-key",
        "comment",
        "inline-comment",
        "comment-record",
        "sequence-key",
        "mapping-key",
        "escaped-literal-label",
        "unicode-literal-label",
        "escaped-literal-key",
    }
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
    + [pytest.param(text, id=f"scheme-fold-{name}") for name, text in SCHEME_FOLDS.items()]
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


@pytest.fixture(scope="session")
def privacy_database_template(tmp_path_factory):
    path = tmp_path_factory.mktemp("privacy-schema") / "empty.db"
    SQLiteStorage(path)
    return path


@pytest.fixture
def privacy_storage(tmp_path, privacy_database_template):
    path = tmp_path / "route.db"
    shutil.copyfile(privacy_database_template, path)
    return SQLiteStorage(path)


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
