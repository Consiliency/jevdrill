"""Keep credential ownership until a first-line value is demonstrably complete."""

from time import monotonic

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
    "{label} = Base64.strict_decode64(<<~B64)\n{marker}\nB64",
    '{label} = "a" + <<~EOS\n{marker}\nEOS',
    "my ${label} = lc <<EOT;\n{marker}\nEOT",
    "${label} = 'a' . <<<'EOT'\n{marker}\nEOT;",
    'const {label}: string =\n"{marker}";',
    'val {label}: String =\n"{marker}"',
    'const {label}: string = "a" +\n"{marker}";',
    'let {label}: String = "a" +\n"{marker}"',
    'const {label} = "prefix" + // rest below\n"{marker}";',
    '{label} = -- set below\n"{marker}"',
    '{label} = "a" ..\n"{marker}"',
    '{label} = os.getenv("P") or\n"{marker}"',
    "${label} = 'a'.\n'{marker}';",
    'const cfg = {{secret: 1}}; const {label} =\n"{marker}";',
    '{label} <- if (TRUE)\n"{marker}"',
    "$cfg->{{{label}}} = q!\n{marker}\n!;",
    "{label} = (<<~EOS)\n{marker}\nEOS",
    "{label}: (\n{marker}\n)",
    "{label}: 1 +\n{marker}",
    "{label} = $fallback // <<'EOF'\n{marker}\nEOF",
    '{label} = "prefix"\n+ "{marker}"',
    '${label} = "prefix"\n. "{marker}";',
    '{label} = "prefix"\nor "{marker}"',
    '$cfg->{{{label}}} = lc\n"{marker}";',
    '{label} <- if (TRUE) "first"\nelse "{marker}"',
    '{label} = "prefix",\n"{marker}"',
    '{label} = r#"\n{marker}\n"#',
    'const char *{label} = "prefix"\n"{marker}";',
)
WITNESSES = tuple(form.format(label="password", marker=MARKER) for form in FORMS)


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_owned_expression_bodies_are_clean(label, form, presentation):
    reject_or_clean(present(form.format(label=label, marker=MARKER), presentation))


@pytest.mark.parametrize("source", WITNESSES)
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_original_witnesses_keep_ownership_across_line_boundaries(source, newline, presentation):
    reject_or_clean(present(source.replace("\n", newline), presentation))


@pytest.mark.parametrize("source", WITNESSES)
@pytest.mark.parametrize("presentation", PRESENTATIONS)
@pytest.mark.parametrize("field", FIELDS)
def test_expression_bodies_never_reach_six_application_sinks(tmp_path, source, presentation, field):
    assert_no_application_effects(
        tmp_path,
        present(source, presentation),
        field,
        allow_sanitized=presentation == "json_log",
    )


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_public_expression_twins_preserve_classification(form, presentation):
    source = form.format(label="display_name", marker=MARKER).replace("secret: 1", "public_name: 1")
    text = present(source, presentation)
    existing_json_rejections = {
        '{label} = "prefix"\n+ "{marker}"': "unsupported computed literal record",
        '{label} = r#"\n{marker}\n"#': "unsupported split decoded credential record",
    }
    if presentation == "json" and form in existing_json_rejections:
        # This exact public JSON string already rejects at the frozen R37
        # source. Preserve its classification; it is not a wire-positive row.
        with pytest.raises(ContractError, match=existing_json_rejections[form]):
            redact(text)
        return
    assert redact(text) == text


@pytest.mark.parametrize(
    "source",
    (
        'password = "{marker}"',
        "password = '{marker}'",
        "password = `{marker}`",
        'password = str("{marker}")',
        'password = f"{marker}"',
        "password = 1 << SHIFT",
        'password <- if (TRUE) "{marker}"',
        "$cfg->{{password}} = q!{marker}!;",
        "$cfg->{{password}} = qq[{marker}];",
        "password: correct horse battery staple",
        "password: hunter2.",
        "password=one two",
        'password = str("password = {marker}")',
    ),
)
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
def test_complete_scalars_keep_ordinary_next_line(source, newline):
    text = source.format(marker=MARKER) + newline + "Ordinary next line."
    cleaned = redact(text)
    assert MARKER not in cleaned
    assert cleaned.endswith(newline + "Ordinary next line.")


@pytest.mark.parametrize(
    "prefix", ("choose()", "function(x)", "q!", "qr!", "if (TRUE)", "BEGIN", "case")
)
def test_unknown_code_shaped_values_fail_closed(prefix):
    with pytest.raises(ContractError, match="unsupported multiline credential assignment"):
        redact(f"password = {prefix}\n{MARKER}")


def test_many_inner_owners_obey_shared_work_and_deadline_bounds():
    source = 'password = "' + ("password=literal " * 1000) + MARKER + '"\nOrdinary next line.'
    started = monotonic()
    try:
        cleaned = redact(source, deadline=started + 2)
    except (ContractError, TimeoutError):
        pass
    else:
        assert MARKER not in cleaned
        assert cleaned.endswith("Ordinary next line.")
    assert monotonic() - started < 3


@pytest.mark.parametrize("newline", ("\n\n", "\r\n\r\n"))
@pytest.mark.parametrize("indent", ("", "  "))
def test_leading_operator_after_blank_lines_cannot_detach_body(newline, indent):
    source = f'password = "prefix"{newline}{indent}+ "{MARKER}"'
    with pytest.raises(ContractError, match="unsupported multiline credential assignment"):
        redact(source)


def test_literal_value_does_not_emit_parser_warnings(recwarn):
    source = f'password = "{MARKER}\\q"\nOrdinary next line.'
    cleaned = redact(source)
    assert MARKER not in cleaned
    assert cleaned.endswith("Ordinary next line.")
    assert not recwarn
