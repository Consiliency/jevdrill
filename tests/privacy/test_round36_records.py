"""R35 review regressions for complete credential-assignment ownership."""

import pytest

from jevdrill.context import redact
from tests.privacy.test_round34_combined import (
    FIELDS,
    MARKER,
    PRESENTATIONS,
    assert_no_application_effects,
    present,
    reject_or_clean,
)

LABELS = ("password", "api_key", "secret", "access_token", "X-API-Key", "Authorization")
HIDDEN_LABELS = ("password\u0903", "api_key\u093e", "Authorization\u0903", "X-API-Key\u093e-backup")
WITNESSES = (
    f"Connection details\npassword\u0903: {MARKER}",
    f'Note that api_key\u093e ||= "{MARKER}"',
    f"Connection details\nAuthorization\u0903: Bearer {MARKER}",
    f'$cfg->{{password}} = "{MARKER}";',
    f'$c->{{a}}->{{secret}} = "{MARKER}";',
    f'$c->{{password}}->{{a}} = "{MARKER}";',
    f'$self->{{api_key}} .= "{MARKER}";',
    f'cfg = {{}}\ncfg.password or= "{MARKER}"',
    f'cfg = {{}}\ncfg.secret and= "{MARKER}"',
    f'password <- "{MARKER}"',
    f'secret <<- "{MARKER}"',
    f'"{MARKER}" -> password',
    f'"{MARKER}" ->> secret',
)


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("operator", ("or=", "and=", "<-", "<<-"))
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_word_and_left_arrow_assignments_are_clean(label, operator, presentation):
    reject_or_clean(present(f'{label} {operator} "{MARKER}"', presentation))


@pytest.mark.parametrize("label", HIDDEN_LABELS)
@pytest.mark.parametrize("operator", (":", "=", "||=", "or=", "<-"))
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_spacing_combining_suffix_records_are_clean(label, operator, presentation):
    reject_or_clean(present(f'Connection details\n{label} {operator} "{MARKER}"', presentation))


@pytest.mark.parametrize("label", ("password", "Authorization", "X-API-Key", "secret\u0903"))
@pytest.mark.parametrize(
    "target",
    (
        "$cfg->{{{label}}}",
        "$c->{{a}}->{{{label}}}",
        "$c->{{{label}}}->{{a}}",
        "$c->[0]->{{{label}}}",
    ),
)
@pytest.mark.parametrize("operator", ("=", ".="))
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_perl_dereference_owner_remains_sensitive(label, target, operator, presentation):
    reject_or_clean(present(f'{target.format(label=label)} {operator} "{MARKER}";', presentation))


@pytest.mark.parametrize("target", ("password", "cfg$password", "cfg[['password']]", "`api_key`"))
@pytest.mark.parametrize("operator", ("->", "->>"))
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_right_arrow_target_is_checked_before_its_value(target, operator, presentation):
    reject_or_clean(present(f'"{MARKER}" {operator} {target}', presentation))


@pytest.mark.parametrize("source", WITNESSES)
@pytest.mark.parametrize("presentation", PRESENTATIONS)
@pytest.mark.parametrize("field", FIELDS)
def test_sensitive_records_never_reach_six_application_sinks(tmp_path, source, presentation, field):
    assert_no_application_effects(
        tmp_path, present(source, presentation), field, allow_sanitized=True
    )


@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("operator", ("or=", "and=", "<-", "<<-"))
def test_complete_forward_values_keep_ordinary_next_line(newline, operator):
    source = f'password {operator} "{MARKER}"{newline}\t{MARKER}{newline}Ordinary next line.'
    assert redact(source) == f"[redacted]{newline}Ordinary next line."


@pytest.mark.parametrize(
    "source",
    (
        'content_type\u0903: "public"',
        'content_type\u093e = "public"',
        'content_type\u0903 ||= "public"',
        'password\u0903 == "public"',
        'secret\u093e >= "public"',
        'cfg = {}\ncfg.retries or= "public"',
        'cfg = {}\ncfg.retries and= "public"',
        '$cfg->{content_type} = "public";',
        '$c->{content_type}->{text} = "public";',
        '$c->{a}->{content_type} = "public";',
        'retries <- "public"',
        'retries <<- "public"',
        '"public" -> retries',
        '"public" ->> retries',
        '"public" -> retries # password is a field name',
        'password < "public"',
        'password <= "public"',
        'password > "public"',
        'password >= "public"',
        'Note that cfg[secret\u0903] = "application/json"',
        "The password\u0903 is long.",
        "The secret (to success) is patience.",
    ),
)
def test_public_and_non_assignment_controls_keep_original(source):
    assert redact(source) == source


def test_repeated_arrow_names_remain_bounded_and_public():
    # Many arrows inside one key must not trigger repeated suffix rescans.
    source = "$cfg->{" + "public->" * 5_000 + "text} = 1"
    assert redact(source) == source
