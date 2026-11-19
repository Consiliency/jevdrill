"""R36 review witnesses: credential owners must retain their multiline values."""

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
LITERAL_FORMS = (
    "{label} = `\n{marker}\n`",
    "{label} := `\n{marker}\n`",
    "{label}: `\n{marker}\n`",
    "{label} = <<~EOS\n{marker}\nEOS",
    "{label} = <<-EOS\n{marker}\nEOS",
    "${label} = <<<'EOT'\n{marker}\nEOT;",
    "${label} = <<<EOT\n{marker}\nEOT;",
    "{label}=<<EOF\n{marker}\nEOF",
)
INCOMPLETE_FORMS = (
    '{label} <-\n"{marker}"',
    '{label} <<-\n"{marker}"',
    '{label} <- # assigned value follows\n"{marker}"',
    '{label} <- (\n"{marker}"\n)',
    '$cfg->{{{label}}} =\n"{marker}";',
    '$cfg->{{{label}}} = # assigned value follows\n"{marker}";',
    '$cfg->{{{label}}} .= (\n"{marker}"\n);',
    '{label} or=\n  "{marker}"',
    '{label} <- "prefix" + # expression continues\n"{marker}"',
    '$cfg->{{{label}}} = $prefix .\n"{marker}";',
    '$cfg->{{{label}}} = \\\n"{marker}";',
)
WITNESSES = (
    f"apiKey := `\n{MARKER}\n`",
    f"secret: `\n{MARKER}\n`",
    f"password = <<~EOS\n{MARKER}\nEOS",
    f"$password = <<<'EOT'\n{MARKER}\nEOT;",
    f"access_token=<<EOF\n{MARKER}\nEOF",
    f'password <-\n"{MARKER}"',
    f'$cfg->{{password}} =\n"{MARKER}";',
)


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("form", LITERAL_FORMS)
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_open_literal_values_never_escape_owner(label, form, presentation):
    source = form.format(label=label, marker=MARKER)
    reject_or_clean(present(source, presentation))


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("form", INCOMPLETE_FORMS)
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_incomplete_assignment_values_never_escape_owner(label, form, presentation):
    source = form.format(label=label, marker=MARKER)
    reject_or_clean(present(source, presentation))


@pytest.mark.parametrize("source", WITNESSES)
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_original_witness_line_boundaries_are_clean(source, newline, presentation):
    reject_or_clean(present(source.replace("\n", newline), presentation))


@pytest.mark.parametrize("source", WITNESSES)
@pytest.mark.parametrize("presentation", PRESENTATIONS)
@pytest.mark.parametrize("field", FIELDS)
def test_multiline_values_never_reach_six_application_sinks(
    privacy_case_path, privacy_storage, source, presentation, field
):
    assert_no_application_effects(
        privacy_case_path,
        present(source, presentation),
        field,
        allow_sanitized=True,
        storage=privacy_storage,
    )


@pytest.mark.parametrize(
    "source",
    (
        "retries := `\npublic\n`",
        "content_type: `\npublic\n`",
        "greeting = <<~EOS\npublic\nEOS",
        "$greeting = <<<'EOT'\npublic\nEOT;",
        'retries <-\n"public"',
        '$cfg->{content_type} =\n"public";',
    ),
)
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_public_multiline_twins_keep_original(source, newline, presentation):
    text = present(source.replace("\n", newline), presentation)
    assert redact(text) == text


@pytest.mark.parametrize(
    "value",
    ("`complete value`", '"complete value"', "1 << SHIFT", "'literal ` tick'"),
)
@pytest.mark.parametrize("operator", ("=", "or=", "<-", "<<-"))
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
def test_complete_values_preserve_ordinary_next_line(value, operator, newline):
    source = f"password {operator} {value}{newline}Ordinary next line."
    assert redact(source) == f"[redacted]{newline}Ordinary next line."


@pytest.mark.parametrize("opener", ('<<"?END"', "<<'END-TAG'", "<<~ΔΕΛΤΑ", "<< 'EOF'"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_heredoc_delimiter_spelling_does_not_detach_body(opener, presentation):
    reject_or_clean(present(f"password = {opener}\n{MARKER}\nEND", presentation))
