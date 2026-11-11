"""R40 review regressions, with public twins and bounded execution controls."""

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
    '$c{{x}}{{{label}}} = "{marker}";',
    '$c[0]{{{label}}} = "{marker}";',
    '${{$c}}{{{label}}} = "{marker}";',
    '$c{{{label}}}\n  ->{{a}} = "{marker}";',
    '${label}\n  ->{{a}} = "{marker}";',
    '$c{{{label}}}\n  {{a}} = "{marker}";',
    '$c{{{label}}}{{a}}\n  = "{marker}";',
    "**Root {label}**: {marker}",
    '**{label} for root** = "{marker}"',
    '${label}->$field = "{marker}";',
    '${label}->@* = "{marker}";',
    '${label}->$* = "{marker}";',
    '{label}: "prefix"\nuR"({marker})";',
    '{label}: "prefix"\nUR"({marker})";',
    '{label}: "prefix"\nLR"({marker})";',
    '{label}->value\n= "{marker}";',
    "**{label}**\n: {marker}",
    "***{label}***\n: {marker}",
)


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_continued_owners_do_not_release_values(label, form, newline, presentation):
    reject_or_clean(
        present(form.format(label=label, marker=MARKER).replace("\n", newline), presentation)
    )


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_public_twins_are_unchanged(form, presentation):
    text = present(form.format(label="display_name", marker=MARKER), presentation)
    assert redact(text) == text


@pytest.mark.parametrize("form", tuple(FORMS[i] for i in (0, 3, 7, 9, 12, 15, 16)))
@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_rejects_before_judgment_and_storage(
    privacy_case_path, privacy_storage, form, field, presentation
):
    text = present(form.format(label="password", marker=MARKER), presentation)
    assert_no_application_effects(
        privacy_case_path, text, field, storage=privacy_storage, allow_sanitized=True
    )


@pytest.mark.parametrize(
    "text",
    (
        "password->value\nOrdinary next line.",
        "$password->value\n== 1",
        "**Greeting**\n: hello",
        "***Greeting***: hello",
    ),
)
def test_non_assignment_controls_are_unchanged(text):
    assert redact(text) == text


def test_delimiter_runs_and_snake_case_do_not_block_deadlines():
    # A process watchdog detects uninterruptible regex work even if the shared
    # deadline can only be checked after that regex returns.
    code = """import json
from jevdrill.context import redact
from time import monotonic
for text in ("_" * 2000, "*" * 2000, "ordinary_snake_case " * 2500):
    start = monotonic()
    assert redact(text, deadline=start + 2) == text
print(json.dumps({"passed": True}))
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], capture_output=True, text=True, timeout=8, check=True
    )
    assert json.loads(result.stdout) == {"passed": True}


@pytest.mark.parametrize("label", ("api__key", "access__token", "client__api__key"))
def test_internal_underscore_runs_are_label_text(label):
    for presentation in ("plain", "json"):
        reject_or_clean(present(f"**Root {label}**: {MARKER}", presentation))
