"""R39 review witnesses: nested owners and source-bearing parser failures."""

import pytest

from jevdrill.context import redact
from jevdrill.contracts import ContractError
from tests.privacy.test_round34_combined import (
    FIELDS,
    MARKER,
    assert_no_application_effects,
    present,
    reject_or_clean,
)

LABELS = ("password", "api_key", "secret", "access_token", "X-API-Key", "Authorization")
FORMS = (
    '$c{{{label}}}{{a}} = "{marker}";',
    '$c->{{{label}}}{{a}} = "{marker}";',
    '$c{{{label}}}->{{a}} = "{marker}";',
    '$c{{{label}}}->[0] = "{marker}";',
    '${label}->{{a}} = "{marker}";',
    '${label}->[0] = "{marker}";',
    '{label}->value[0] = "{marker}";',
    '{label}->value.other = "{marker}";',
    "***{label}***: {marker}",
    '**~~{label}~~** = "{marker}"',
    '{label} = "prefix"\nuR"({marker})";',
    '{label} = "prefix"\nUR"({marker})";',
    '{label} = "prefix"\nLR"({marker})";',
    '{label} = 1 << "A-B"\n{marker}\nA-B',
    '{label} = 1 << "E O F"\n{marker}\nE O F',
)


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_nested_owners_and_literal_bodies_stay_private(label, form, newline, presentation):
    text = form.format(label=label, marker=MARKER).replace("\n", newline)
    reject_or_clean(present(text, presentation))


@pytest.mark.parametrize("form", tuple(FORMS[i] for i in (0, 4, 6, 8, 10, 13)))
@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_rejects_before_application_effects(
    privacy_case_path, privacy_storage, form, field, presentation
):
    text = present(form.format(label="password", marker=MARKER), presentation)
    assert_no_application_effects(privacy_case_path, text, field, storage=privacy_storage)


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_public_twins_keep_their_text(form, presentation):
    text = present(form.format(label="display_name", marker=MARKER), presentation)
    assert redact(text) == text


def test_comment_only_assignment_prefix_does_not_crash():
    assert isinstance(redact("# Title\n= Heading"), str)


def test_yaml_parser_error_does_not_expose_source_in_traceback():
    import traceback

    text = f'Authorization: Bearer {MARKER} ? "\\q": 1'
    with pytest.raises(ContractError) as caught:
        redact(text)
    rendered = "".join(traceback.format_exception(caught.value))
    assert MARKER not in rendered
    assert caught.value.__suppress_context__


@pytest.mark.parametrize(
    "text", ("password->value == 1", "$c{password}{a}", "$c{password}{a} == 1")
)
def test_non_assignment_owner_references_keep_existing_behavior(text):
    assert redact(text) == text
