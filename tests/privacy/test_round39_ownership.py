"""R38 board witnesses: retain owners across markup, literals and block bodies."""

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

LABELS = ("password", "api_key", "secret", "access_token", "X-API-Key", "Authorization")
FORMS = (
    "**{label}**: {marker}",
    "* **{label}**: {marker}",
    '**{label}** = "{marker}"',
    "*{label}*: {marker}",
    "~~{label}~~: {marker}",
    'const char *{label} = "prefix"\nu8"{marker}";',
    'const wchar_t *{label} = L"prefix"\nL"{marker}";',
    'const char16_t *{label} = u"prefix"\nu"{marker}";',
    'const char32_t *{label} = U"prefix"\nU"{marker}";',
    "Please rotate this.\n{label}: |\n\n  {marker}\n",
    "Please rotate this.\n{label}: >-\n\n\n  {marker}\n",
    '${label}->value = "{marker}";',
    '${label}->inner->value += "{marker}";',
    "{label} = 1 << EOF\n{marker}\nEOF",
    "{label} = (1 << EOF)\n{marker}\nEOF",
    '{label} = 1 << "SHIFT"\n{marker}\nSHIFT',
)
BOUNDARY_FORMS = tuple(FORMS[i] for i in (0, 5, 9, 11, 13))


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_credential_bodies_keep_their_owner(label, form, newline, presentation):
    source = form.format(label=label, marker=MARKER).replace("\n", newline)
    reject_or_clean(present(source, presentation))


@pytest.mark.parametrize("form", BOUNDARY_FORMS)
@pytest.mark.parametrize("presentation", PRESENTATIONS)
@pytest.mark.parametrize("field", FIELDS)
def test_ownership_failures_never_reach_application_effects(
    privacy_case_path, privacy_storage, form, presentation, field
):
    text = present(form.format(label="password", marker=MARKER), presentation)
    assert_no_application_effects(
        privacy_case_path,
        text,
        field,
        allow_sanitized=presentation == "json_log",
        storage=privacy_storage,
    )


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_public_twins_are_preserved(form, presentation):
    text = present(form.format(label="display_name", marker=MARKER), presentation)
    if form == "*{label}*: {marker}":
        # This spelling already rejects as a YAML alias at the frozen R38
        # head, including inside a JSON string. Preserve that classification.
        with pytest.raises(ContractError, match="unsupported YAML graph or tag"):
            redact(text)
        return
    assert redact(text) == text


@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("expression", ("1 << 2", "1 << SHIFT", '"contains << EOF"'))
def test_complete_values_keep_an_ordinary_next_line(newline, expression):
    text = "password = " + expression + newline + "Ordinary next line."
    assert redact(text) == "[redacted]" + newline + "Ordinary next line."


@pytest.mark.parametrize(
    "literal", ('"contains << EOF"', "`contains << EOF`", "q!contains << EOF!")
)
def test_literal_text_is_not_a_heredoc_even_with_a_later_matching_word(literal):
    if literal.startswith("`"):
        # The frozen source already rejects this backtick/computed-record
        # spelling. This repair must not change its classification.
        with pytest.raises(ContractError, match="unsupported computed literal record"):
            redact(f"password = {literal}\nOrdinary next line.\nEOF")
        return
    assert redact(f"password = {literal}\nOrdinary next line.\nEOF") == (
        "[redacted]\nOrdinary next line.\nEOF"
    )


def test_valid_yaml_block_with_leading_blank_line_still_sanitizes():
    reject_or_clean(f"password: |\n\n  {MARKER}\n")


def test_many_spaced_heredoc_owners_share_a_bounded_closer_index():
    from time import monotonic

    text = ("password = 1 << SHIFT\nOrdinary next line.\n" * 500) + "EOF"
    start = monotonic()
    try:
        cleaned = redact(text, deadline=start + 2)
    except (ContractError, TimeoutError):
        pass
    else:
        assert cleaned.count("Ordinary next line.") == 500
    assert monotonic() - start < 3
