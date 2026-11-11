"""R41 ownership and bounded-scan regressions; no real credentials or providers."""

import json
import subprocess
import sys

import pytest

from jevdrill.context import redact
from tests.privacy.test_round34_combined import (
    FIELDS,
    MARKER,
    assert_no_application_effects,
    present,
    reject_or_clean,
)

LABELS = ("password", "api_key", "secret", "access_token", "X-API-Key", "Authorization")
FORMS = (
    '$c{{{label}}}{{"a;b"}} = "{marker}";',
    '${label}->{{"a;b"}} = "{marker}";',
    '{label}->value["a;b"] = "{marker}";',
    '{label}->*member = "{marker}";',
    '{label}()->value = "{marker}";',
    '${label}->%* = ("a", "{marker}");',
    '${label}->&* = "{marker}";',
    '${label}->$#* = "{marker}";',
    "`**{label}**`: {marker}",
    "**{label}** (prod): {marker}",
    "**{label}**\n\n: {marker}",
    '$c{{{label}}} # note\n ->{{a}} = "{marker}";',
    '$c{{{label}}}{{a}} # note\n = "{marker}";',
    '$c{{{label}}}\n # note\n ->{{a}} = "{marker}";',
    '{label}->value # note\n= "{marker}";',
    '$c{{\n {label}\n}}{{a}} = "{marker}";',
    '$c{{\n {label}\n}}->{{a}} = "{marker}";',
    "**Root _{label}_ for server**: {marker}",
    "**Root _{label}_ for server**\n: {marker}",
    '**Root _{label}_ for server** = "{marker}"',
    "**{label} * note**: {marker}",
)


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_sensitive_owner_survives_presentation(label, form, newline, presentation):
    reject_or_clean(
        present(form.format(label=label, marker=MARKER).replace("\n", newline), presentation)
    )


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_public_twins_remain_unchanged(form, presentation):
    text = present(form.format(label="display_name", marker=MARKER), presentation)
    assert redact(text) == text


@pytest.mark.parametrize("form", tuple(FORMS[i] for i in (0, 3, 4, 8, 11, 15, 17)))
@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_no_judgment_or_retention_effects(
    privacy_case_path, privacy_storage, form, field, presentation
):
    text = present(form.format(label="password", marker=MARKER), presentation)
    assert_no_application_effects(
        privacy_case_path, text, field, storage=privacy_storage, allow_sanitized=True
    )


@pytest.mark.parametrize(
    "text",
    (
        "**password** ordinary text **Greeting**: hello",
        "password->value # comment\nOrdinary next line.",
        "password->value == 1",
        'password->value; unrelated = "hello";',
        "**Greeting**\n\n: hello",
    ),
)
def test_independent_public_records_remain_unchanged(text):
    assert redact(text) == text


def test_repeated_labels_do_not_block_deadlines():
    code = """import json
from time import monotonic
from jevdrill.context import redact
from jevdrill.contracts import ContractError
for text in ("password" * 25000, "secret_" * 28572, "api_" * 50000,
             "_" * 50000, "*" * 50000, "ordinary_snake_case " * 2500):
    start = monotonic()
    assert redact(text, deadline=start + 1) == text
    assert monotonic() - start < 1
for text in ("**password** (" * 2000, "**password** (" + "(" * 200000):
    start = monotonic()
    try:
        redact(text, deadline=start + 1)
    except ContractError:
        pass
    assert monotonic() - start < 1
print(json.dumps({"passed": True}))
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=8, check=True
    )
    assert json.loads(result.stdout) == {"passed": True}
