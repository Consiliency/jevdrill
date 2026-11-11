"""Inert R34 witnesses for the existing sanitize-before-effects contract."""

import copy
import json
from pathlib import Path

import pytest

from jevdrill.application import Application
from jevdrill.context import redact
from jevdrill.contracts import ContractError
from jevdrill.storage import SQLiteStorage

MARKER = "INERT_R34_CREDENTIAL_VALUE"
FIXTURES = Path(__file__).parents[1] / "contracts/fixtures"
FIELDS = (
    "route_task",
    "route_attachment",
    "work_objective_text",
    "authorized_context",
    "description",
    "attachment_refs",
)
PRESENTATIONS = ("plain", "json", "json_log", "backticks")
SUFFIX_LABELS = (
    "password\u200b",
    "api_key\ufeff",
    "secret\u00ad",
    "secret\u0327\u00a0",
    "X-API-Key\u200b",
    "password\u200b_backup",
    "X-API-Key\u200b-backup",
    "client_secret\u00ad_backup\u2060-v2",
    "api_key\ufeff.alt\u200b_tag",
)


def present(source, presentation):
    if presentation == "json":
        return json.dumps(source)
    if presentation == "json_log":
        return json.dumps({"message": source})
    if presentation == "backticks":
        return "```\n" + source + "\n```"
    return source


def reject_or_clean(text):
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert MARKER not in cleaned


@pytest.mark.parametrize("label", SUFFIX_LABELS)
@pytest.mark.parametrize("operator", (" = ", " += ", " >>= ", " := "))
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_intact_label_with_invisible_suffix_never_survives(label, operator, presentation):
    reject_or_clean(present(f'{label}{operator}"{MARKER}"', presentation))


@pytest.mark.parametrize("label", ("secret\u0327", "secret\u0307"))
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize(
    "comment", ("", " # ordinary comment", ' # comment with " quote and ] bracket')
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_raw_owner_spelling_survives_ast_normalization_only_as_rejection(
    label, newline, comment, presentation
):
    source = f'({label}{comment}{newline}) = "{MARKER}"'
    reject_or_clean(present(source, presentation))


@pytest.mark.parametrize("label", ("secret\u0327", "secret\u0307"))
@pytest.mark.parametrize("newline", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("comment", ("", ' # comment with " quote and ] bracket'))
@pytest.mark.parametrize("presentation", PRESENTATIONS)
def test_multiline_named_expression_checks_raw_owner(label, newline, comment, presentation):
    source = f'({label}{comment}{newline} := "{MARKER}")'
    reject_or_clean(present(source, presentation))


@pytest.mark.parametrize("label", ("secret\u0327", "secret\u0307"))
@pytest.mark.parametrize("operator", ("=", ":="))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_comment_delimiters_before_raw_owner_do_not_change_grouping(label, operator, presentation):
    source = f'( # comment with ] ) [ and "\n {label}\n'
    source += f' := "{MARKER}")' if operator == ":=" else f') = "{MARKER}"'
    reject_or_clean(present(source, presentation))


@pytest.mark.parametrize(
    "source",
    (
        'password\u200b == "INERT_R34_CREDENTIAL_VALUE"',
        'secret\u00ad >= "INERT_R34_CREDENTIAL_VALUE"',
        'Content-Type\u200b = "INERT_R34_CREDENTIAL_VALUE"',
        'Content-Type\u200b-backup = "INERT_R34_CREDENTIAL_VALUE"',
        'password\u200b_backup == "INERT_R34_CREDENTIAL_VALUE"',
        'X-API-Key\u200b-backup >= "INERT_R34_CREDENTIAL_VALUE"',
        '(content_type\u0327\n) = "INERT_R34_CREDENTIAL_VALUE"',
        'content_type = "INERT_R34_CREDENTIAL_VALUE"',
        'x: content_type\u0327 = "INERT_R34_CREDENTIAL_VALUE"',
        'Content-Type\u200b-backup = "INERT_R34_CREDENTIAL_VALUE"\nOrdinary next line.',
        "The password\u200b is long.",
        "The secret\u00a0(to success) is patience.",
    ),
)
def test_non_owner_and_public_controls_keep_original(source):
    assert redact(source) == source


def test_public_index_keeps_existing_fail_closed_classification():
    with pytest.raises(ContractError, match="unsupported computed literal record"):
        redact('headers[content_type\u0327] = "INERT_R34_CREDENTIAL_VALUE"')


@pytest.mark.parametrize(
    "source",
    (
        '\u200bpassword_backup = "INERT_R34_CREDENTIAL_VALUE"',
        '\u200bX-API-Key-backup = "INERT_R34_CREDENTIAL_VALUE"',
        'pre\u200bpassword_backup = "INERT_R34_CREDENTIAL_VALUE"',
    ),
)
def test_prefix_trivia_with_intact_credential_substring_is_already_clean(source):
    reject_or_clean(source)


def test_complete_plaintext_value_keeps_ordinary_next_line():
    assert redact(f'password = "{MARKER}"\nOrdinary next line.') == (
        "[redacted]\nOrdinary next line."
    )


@pytest.mark.parametrize("label", SUFFIX_LABELS)
@pytest.mark.parametrize("presentation", PRESENTATIONS)
@pytest.mark.parametrize("field", FIELDS)
def test_suffix_assignments_never_reach_six_application_sinks(
    privacy_case_path, privacy_storage, label, presentation, field
):
    source = f'{label} = "{MARKER}"'
    assert_no_application_effects(
        privacy_case_path,
        present(source, presentation),
        field,
        allow_sanitized=presentation == "json_log",
        storage=privacy_storage,
    )


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
@pytest.mark.parametrize("walrus", (False, True))
def test_raw_multiline_owner_rejects_before_six_application_effects_and_bytes(
    privacy_case_path, privacy_storage, field, presentation, walrus
):
    source = '(secret\u0327 # comment with " quote and ] bracket\r\n'
    source += f' := "{MARKER}")' if walrus else f') = "{MARKER}"'
    assert_no_application_effects(
        privacy_case_path, present(source, presentation), field, storage=privacy_storage
    )


def assert_no_application_effects(tmp_path, text, field, *, allow_sanitized=False, storage=None):
    fixture = "route-application.json" if field.startswith("route_") else "discovery.json"
    payload = copy.deepcopy(json.loads((FIXTURES / fixture).read_text())[0]["payload"])
    payload["settings_layers"] = [{"source": "request", "values": {"retain_raw_tasks": True}}]
    attachment = {
        "reference": "public.txt",
        "authorized": True,
        "modality": "document",
        "representation_source": "supplied",
        "text_representation": text,
    }
    if field == "route_task":
        payload["request"]["task_representation"] = text
    elif field == "route_attachment":
        payload["request"]["attachment_refs"] = [attachment]
    elif field == "description":
        payload["descriptions"][0]["description"] = text
    elif field == "attachment_refs":
        payload[field] = [attachment]
    else:
        payload[field] = text

    class SanitizedBoundary(Exception):
        """Stop an allowed, already-sanitized call without a provider."""

    class NeverJudge:
        def check(self, args, kwargs):
            assert MARKER not in repr((args, kwargs))
            if allow_sanitized:
                raise SanitizedBoundary
            raise AssertionError("rejected credential reached judgment")

        def judge(self, *args, **kwargs):
            self.check(args, kwargs)

        def observe_option(self, *args, **kwargs):
            self.check(args, kwargs)

    if storage is None:
        storage = SQLiteStorage(tmp_path / "route.db")
    assert storage.path == tmp_path / "route.db"
    app = Application(storage, judgments=NeverJudge(), discovery_judgments=NeverJudge())
    if allow_sanitized:
        # Sibling masking already cleans the JSON-log presentation. Allow it
        # to reach real local storage and the checked in-memory judge boundary.
        try:
            (app.route if field.startswith("route_") else app.discover)(payload)
        except (ContractError, SanitizedBoundary):
            pass
    else:
        with pytest.raises(ContractError):
            (app.route if field.startswith("route_") else app.discover)(payload)
    # These inspect actual local storage bytes. The route-attachment case must
    # reject at ingress; stage_artifact task-only captures cannot prove it.
    assert all(
        MARKER.encode() not in path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()
    )
