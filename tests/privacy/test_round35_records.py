"""R34 review witnesses: inert records must be clean before application effects."""

import pytest

from jevdrill.context import redact
from jevdrill.contracts import ContractError
from tests.privacy.test_round34_combined import (
    FIELDS,
    MARKER,
    PRESENTATIONS,
    assert_no_application_effects,
    present,
    reject_or_clean,
)

OPERATORS = ("||=", "&&=", "??=", "?=", ".=")
LABELS = ("password", "api_key", "secret", "access_token", "X-API-Key", "client_secret")
HIDDEN_LABELS = (
    "password\u200b",
    "secret\u0301",
    "X-API-Key\u200b-backup",
    "api_key\ufeff.alt\u200b_tag",
)
WITNESSES = (
    f"Connection details\npassword\u0301: {MARKER}",
    f"Connection details\npassword\u200b: {MARKER}",
    f'password ||= "{MARKER}"',
    f'api_key ??= "{MARKER}"',
    f'secret ?= "{MARKER}"',
    f'cfg.access_token &&= "{MARKER}"',
    f'X-API-Key .= "{MARKER}"',
    f'cfg[`password`] = "{MARKER}";',
    f'$cfg{{password}} = "{MARKER}";',
    f'cfg[`password\u200b`] ||= "{MARKER}";',
    f'$cfg{{secret\u0301}} ??= "{MARKER}";',
    f'$cfg{{"password\u200b"}} = "{MARKER}";',
)


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("operator", OPERATORS)
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_logical_and_conditional_assignments_are_clean(label, operator, presentation):
    reject_or_clean(present(f'{label} {operator} "{MARKER}"', presentation))


@pytest.mark.parametrize("label", HIDDEN_LABELS)
@pytest.mark.parametrize("operator", (":", *OPERATORS))
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_hidden_suffix_records_after_prose_are_clean(label, operator, presentation):
    reject_or_clean(present(f'Connection details\n{label} {operator} "{MARKER}"', presentation))


@pytest.mark.parametrize(
    "label", ("password", "Authorization", "X-API-Key", "access_token", *HIDDEN_LABELS)
)
@pytest.mark.parametrize("target", ("cfg[`{label}`]", "$cfg{{{label}}}", '$cfg{{"{label}"}}'))
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_alternate_key_delimiters_are_clean(label, target, presentation):
    reject_or_clean(present(f'{target.format(label=label)} = "{MARKER}";', presentation))


@pytest.mark.parametrize("source", WITNESSES)
@pytest.mark.parametrize("presentation", PRESENTATIONS)
@pytest.mark.parametrize("field", FIELDS)
def test_sensitive_records_never_reach_six_application_sinks(
    privacy_case_path, privacy_storage, source, presentation, field
):
    # The shared helper checks real SQLite/artifact bytes and every fake judge
    # argument. A route attachment is checked at ingress, not by task-only staging.
    assert_no_application_effects(
        privacy_case_path,
        present(source, presentation),
        field,
        allow_sanitized=True,
        storage=privacy_storage,
    )


@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("operator", OPERATORS)
def test_complete_values_keep_the_ordinary_next_line(newline, operator):
    source = f'password {operator} "{MARKER}"  {newline}\t{MARKER}{newline}Ordinary next line.'
    assert redact(source) == f"[redacted]{newline}Ordinary next line."


@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("label", HIDDEN_LABELS)
def test_hidden_colon_records_reject_folded_values(newline, label):
    with pytest.raises(ContractError, match="unsupported credential assignment"):
        redact(f"Connection details{newline}{label}: {MARKER}{newline}\t{MARKER}")


@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("target", ("cfg[`password\u200b`]", "$cfg{secret\u0301}"))
@pytest.mark.parametrize("operator", ("=", "||=", "??="))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_delimited_hidden_key_owns_operator_after_newline(newline, target, operator, presentation):
    reject_or_clean(present(f'{target}{newline}{operator} "{MARKER}"', presentation))


@pytest.mark.parametrize(
    "source",
    (
        "retries ||= 3",
        'x ??= "public"',
        "count &&= 1",
        "NAME ?= value",
        '$s .= "public"',
        'cfg[`content_type`] = "public";',
        '$cfg{content_type} = "public";',
        'Content-Type\u200b ||= "public"',
        'content_type\u0301: "public"',
        'password\u200b == "public"',
        'secret\u0301 >= "public"',
        'Note that cfg[secret\u0327] = "application/json"',
        'Note that cfg[{secret\u0327}] = "application/json"',
        "The password\u200b is long.",
        "The secret (to success) is patience.",
    ),
)
def test_public_and_comparison_controls_keep_original(source):
    assert redact(source) == source
