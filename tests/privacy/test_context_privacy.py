import json
from pathlib import Path

import pytest

from jevdrill.context import collect_context, workspace_id
from jevdrill.contracts import ContractError

EXPLICIT_KEY_REPAIR_CASES = (
    "Ordinary context. ? f'Author' f'ization': SYNTHETIC_SENTINEL",
    "LOG\n{? f'Author' f'ization': SYNTHETIC_SENTINEL}",
    "LOG\n[? f'Author' f'ization': SYNTHETIC_SENTINEL]",
    "Ordinary context. ? f'Author' + f'ization': SYNTHETIC_SENTINEL",
    "Ordinary context. ? 'Author' f'ization': SYNTHETIC_SENTINEL",
    "Ordinary context. ? prefix + suffix: SYNTHETIC_SENTINEL",
    "Ordinary context. ? $prefix + suffix: SYNTHETIC_SENTINEL",
)

PROSE_EXPLICIT_KEY_CASES = (
    "It's fine ? 'Author' + 'ization': SYNTHETIC_SENTINEL",
    "Don't panic. ? f'Author' f'ization': SYNTHETIC_SENTINEL",
    "Don't {? 'Author'+'ization': SYNTHETIC_SENTINEL}",
    "He said \"hi ? 'Author' + 'ization': SYNTHETIC_SENTINEL",
    'He said "hi ? "Author"+"ization": SYNTHETIC_SENTINEL',
    'He said "hi {? "Author"+"ization": SYNTHETIC_SENTINEL}',
)

DOUBLED_QUOTE_EXPLICIT_KEY_CASES = (
    "It's fine ? 'Author''ization': SYNTHETIC_SENTINEL",
    "Don't {? 'Author''ization': SYNTHETIC_SENTINEL}",
    "He said \"hi ? 'Author''ization': SYNTHETIC_SENTINEL",
    'It\'s fine ? "Author""ization": SYNTHETIC_SENTINEL',
    "Don't {? 'Author'\"ization\": SYNTHETIC_SENTINEL}",
)

QUOTE_KEY_CROSS_PRODUCT = tuple(
    f"{prose} {'{?' if flow else '?'} {key}: SYNTHETIC_SENTINEL{' }' if flow else ''}"
    for prose in ("It's fine", 'He said "hi', "He said 'hi", 'He said "hi" then')
    for key in (
        "'Author'+'ization'",
        '"Author"+"ization"',
        "f'Author' f'ization'",
        'f"Author" f"ization"',
    )
    for flow in (False, True)
)


@pytest.mark.parametrize("text", EXPLICIT_KEY_REPAIR_CASES)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_computed_explicit_keys_reject_in_prose_and_wrappers(text, presentation):
    from jevdrill.context import redact

    source = (
        text
        if presentation == "plain"
        else json.dumps(text)
        if presentation == "json"
        else json.dumps({"log": text})
        if presentation == "json-log"
        else f"`{text}`"
    )
    with pytest.raises(ContractError, match="computed explicit key"):
        redact(source)


@pytest.mark.parametrize("text", PROSE_EXPLICIT_KEY_CASES + QUOTE_KEY_CROSS_PRODUCT)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_prose_quotes_cannot_hide_computed_explicit_keys(text, presentation):
    from jevdrill.context import redact

    source = (
        text
        if presentation == "plain"
        else json.dumps(text)
        if presentation == "json"
        else json.dumps({"log": text})
        if presentation == "json-log"
        else f"`{text}`"
    )
    with pytest.raises(ContractError):
        redact(source)


@pytest.mark.parametrize("text", DOUBLED_QUOTE_EXPLICIT_KEY_CASES)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_doubled_quote_explicit_keys_reject_in_prose_and_wrappers(text, presentation):
    from jevdrill.context import redact

    source = (
        text
        if presentation == "plain"
        else json.dumps(text)
        if presentation == "json"
        else json.dumps({"log": text})
        if presentation == "json-log"
        else f"`{text}`"
    )
    with pytest.raises(ContractError):
        redact(source)


@pytest.mark.parametrize(
    "text",
    (
        "Ordinary context. ? f'Content' f'-Type': application/json",
        "Ordinary context. ? f'Content' + f'-Type': application/json",
        "Ordinary context. ? 'Content''-Type': application/json",
        "It's fine ? 'Content''-Type': application/json",
        "Ordinary context. ? Content-Type: application/json",
    ),
)
def test_public_explicit_key_compositions_keep_source(text):
    from jevdrill.context import redact

    assert redact(text) == text


def test_dynamic_explicit_key_rejects_without_running_expression():
    from jevdrill.context import redact

    with pytest.raises(ContractError, match="computed explicit key"):
        redact("Ordinary context. ? f'{must_not_execute()}': SYNTHETIC_SENTINEL")


def test_credentials_and_excluded_path_descendants_are_removed():
    result = collect_context(
        "password=sentinel ordinary",
        [
            {"reference": "/private/nested.txt", "authorized": True},
            {"reference": "C:\\project\\.env.local", "authorized": True},
            {
                "reference": "/public.txt",
                "authorized": True,
                "text_representation": "api_key=sentinel",
            },
        ],
        ["/private"],
    )
    assert "sentinel" not in str(result)
    assert len(result["attachments"]) == 1
    assert result["unavailable"]


def test_workspace_paths_are_distinct_and_symlinks_resolve(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir()
    second.mkdir()
    assert workspace_id(first) != workspace_id(second)
    assert workspace_id(first / ".." / "one") == workspace_id(first)
    assert workspace_id(Path(str(first))) == workspace_id(first)


@pytest.mark.parametrize("scheme", ["Bearer", "Basic", "bearer"])
@pytest.mark.parametrize("separator", [" ", "\n  ", "\r\n\t"])
def test_authorization_credentials_are_removed_from_task_and_attachments(scheme, separator):
    header = f"Authorization: {scheme}{separator}SYNTHETIC_SENTINEL\nOrdinary context"
    result = collect_context(
        header,
        [{"reference": "public", "authorized": True, "text_representation": header}],
        [],
    )
    assert "SYNTHETIC_SENTINEL" not in str(result)
    assert "Ordinary context" in result["task_representation"]


def test_authorization_removes_all_folded_continuations():
    header = (
        "Authorization: Digest username=SYNTHETIC_SENTINEL\r\n"
        "  nonce=SYNTHETIC_SENTINEL\r\n\tresponse=SYNTHETIC_SENTINEL\nOrdinary context"
    )
    result = collect_context(header, [], [])
    assert "SYNTHETIC_SENTINEL" not in str(result)
    assert "Ordinary context" in result["task_representation"]


@pytest.mark.parametrize("mixed", [False, True])
def test_quoted_credentials_are_removed_from_task_and_attachments(
    credential_text, credential_may_reject, mixed
):
    text = "Ordinary context.\n" + credential_text if mixed else credential_text
    try:
        result = collect_context(
            text,
            [{"reference": "public", "authorized": True, "text_representation": text}],
            [],
        )
    except ContractError:
        assert credential_may_reject
        return
    assert "SYNTHETIC_SENTINEL" not in str(result)


def test_ordinary_context_keeps_basic_instructions():
    text = "Use basic arithmetic and explain the result."
    assert collect_context(text, [], [])["task_representation"] == text


@pytest.mark.parametrize(
    "text",
    [
        "ordinary\\\n" * 2_000,
        "Basic\n  SYNTHETIC_SENTINEL",
        "-----BEGIN PRIVATE KEY-----\nSYNTHETIC_SENTINEL\n-----END PRIVATE KEY-----",
    ],
    ids=["plain-continuations", "folded-basic", "private-key"],
)
def test_plain_context_preserves_ordinary_text_and_scrubs_credentials(text):
    result = collect_context(text, [], [])["task_representation"]
    if "SYNTHETIC_SENTINEL" in text:
        assert "SYNTHETIC_SENTINEL" not in result
    else:
        assert result == text


@pytest.mark.parametrize("scheme", ["Basic", "Bearer"])
@pytest.mark.parametrize("separator", ["\n", "\r\n", "\r", "\x85", "\u2028", "\u2029"])
def test_standalone_credentials_remove_folds_and_keep_ordinary_following_text(scheme, separator):
    text = (
        scheme
        + " prefix"
        + separator
        + " "
        + separator
        + "\tSYNTHETIC_SENTINEL"
        + separator
        + "Ordinary context"
    )
    result = collect_context(text, [], [])["task_representation"]
    assert "SYNTHETIC_SENTINEL" not in result
    assert "Ordinary context" in result


def test_private_key_redaction_keeps_original_structured_label_associations():
    text = "header: |\n  -----BEGIN PRIVATE KEY-----\n  Authorization\n  -----END PRIVATE KEY-----\npayload: SYNTHETIC_SENTINEL"
    assert "SYNTHETIC_SENTINEL" not in collect_context(text, [], [])["task_representation"]


@pytest.mark.parametrize("count", [1, 20])
def test_complete_private_key_blocks_preserve_following_context(count):
    text = (
        "-----BEGIN EC PRIVATE KEY-----\nSYNTHETIC_SENTINEL\n-----END EC PRIVATE KEY-----\n" * count
        + "Ordinary context"
    )
    result = collect_context(text, [], [])["task_representation"]
    assert "SYNTHETIC_SENTINEL" not in result
    assert "Ordinary context" in result


def test_noncredential_json_preserves_context_and_format():
    text = 'Headers: [{"name":"Content-Type", "value":"application/json"}]\nUse basic arithmetic.'
    assert collect_context(text, [], [])["task_representation"] == text


@pytest.mark.parametrize("label", ["Authorization", "api_key", "password"])
def test_yaml_block_header_pairs_mask_all_siblings(label):
    text = f"- {label}\n- SYNTHETIC_SENTINEL"
    assert "SYNTHETIC_SENTINEL" not in collect_context(text, [], [])["task_representation"]


@pytest.mark.parametrize("label", ["Authorization", "api_key", "password"])
@pytest.mark.parametrize("separator", ["\n", "\r\n", "\r", "\x85", "\u2028", "\u2029"])
def test_whole_dash_only_yaml_header_pairs_still_sanitize(label, separator):
    text = separator.join(["-", "  " + label, "- SYNTHETIC_SENTINEL"])
    assert "SYNTHETIC_SENTINEL" not in collect_context(text, [], [])["task_representation"]


@pytest.mark.parametrize(
    "value",
    [
        'r"SYNTHETIC_SENTINEL"',
        'b"SYNTHETIC_SENTINEL"',
        'f"SYNTHETIC_SENTINEL"',
        'str("SYNTHETIC_SENTINEL")',
    ],
)
@pytest.mark.parametrize(
    "target",
    [
        "password",
        "headers['X-API-Key']",
        "password: str",
        "ordinary = password",
        r"headers[b'\x61pi_key']",
        'headers["Author" + "ization"]',
        'headers[f"Author" f"ization"]',
        r'headers["\x41uthor" + "ization"]',
    ],
)
def test_complete_single_line_assignments_keep_ordinary_next_line(target, value):
    text = f"{target} = {value}\nOrdinary context"
    result = collect_context(text, [], [])["task_representation"]
    assert "SYNTHETIC_SENTINEL" not in result
    assert "Ordinary context" in result


def test_ordinary_assignments_and_escaped_literals_keep_content(recwarn):
    for text in (
        'ordinary = "context"',
        'headers["Content" "-Type"] = "application/json"',
        'headers["Content" + "-Type"] = "application/json"',
        'headers[f"Content" f"-Type"] = "application/json"',
        '{"name": f"Content" f"-Type", "value": "application/json"}',
        "Please inspect: {'name': 'Content' + '-Type', 'value': 'application/json'} End notes.",
        "`{'name': f'Content' f'-Type', 'value': 'application/json'}`",
        '`headers["Content" + "-Type"] = "application/json"`',
        'config.headers["Content" + "-Type"] = "application/json"',
        '- {"name": "Content-Type", "value": "application/json"}',
        'Inspect({"name": "Content-Type", "value": "application/json"})',
        '{"number": -1, "values": [-2, 3]}',
        "Please [note {'name': f'Content' f'-Type', 'value': 'application/json'}]",
        r"{'path': 'C:\public', 'text': 'ordinary'}",
        "Here's {'name': 'Content' + '-Type', 'value': 'application/json'}",
        "Here's `headers['Content-Type'] = mime()`\nOrdinary context",
        "headers['Content-Type'] = mime()\nOrdinary context",
        "\"{'name': 'Content-Type', 'value': 'application/json'}\"",
        "dict(name='Content-Type', value='application/json')",
        "{count: -2, label: notes}",
        "name: Content-Type\nvalue: application/json",
        '{"revision": "public-array-bounds-spec-v1"}',
        "revision: public-array-bounds-spec-v1",
        "-\n  ordinary context\n- ordinary value",
        '"Ordinary context\nMore ordinary context"',
        '"name: Content-Type\nvalue: application/json"',
        "Here's dict (name='Content-Type', value='application/json')",
        "Here's (dict)(name='Content-Type', value='application/json')",
        "`dict\t(name='Content-Type', value='application/json')`",
        "Ordinary context.\n-\n  Content-Type\n- application/json",
        "name: ordinary public\n  context\nvalue: notes",
        "'name: ''Content-Type''\nvalue: application/json'",
        '"name: \\"Content-Type\\"\nvalue: application/json"',
        'Ordinary context.\nnote: "name: Content-Type\nvalue: application/json"',
        "Ordinary context.\n?\n  Content-Type\n: application/json",
        "Ordinary context.\nname:\n  Content-Type\nvalue: application/json",
        "Ordinary context.\nname: ordinary public # keep\n  context\nvalue: notes",
        "config.headers['Content-Type'] = mime()\nOrdinary context",
        "headers['Content-Type'] = mime(\n  public\n)\nOrdinary context",
    ):
        assert collect_context(text, [], [])["task_representation"] == text
    assert not recwarn.list


@pytest.mark.parametrize("prefix", ["Here's ", "It's ", "'", '"', "# ", "```\n# "])
@pytest.mark.parametrize("separator", ["\n", "\r\n", "\r", "\x85", "\u2028", "\u2029"])
def test_presentation_does_not_hide_adjacent_literal_records(prefix, separator):
    text = prefix + "{'name': 'Author' 'ization', 'value': 'SYNTHETIC_SENTINEL'}"
    text += separator + "Ordinary context"
    try:
        result = collect_context(text, [], [])
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in str(result)


def test_computed_literal_records_reject_without_executing_expressions():
    text = """{"name": f"{must_not_execute()}", "value": "SYNTHETIC_SENTINEL"}"""
    with pytest.raises(ContractError, match="computed"):
        collect_context(text, [], [])


def test_deep_context_fails_with_a_boundary_error():
    with pytest.raises(ContractError, match="nesting"):
        collect_context("[" * 1500 + "0" + "]" * 1500, [], [])


def test_ordinary_structured_context_remains_usable():
    text = json.dumps({"items": ["ordinary"] * 200})
    assert collect_context(text, [], [])["task_representation"] == text


def test_composition_checks_the_deadline(monkeypatch):
    from jevdrill.context import _DeadlineLoader

    loader = _DeadlineLoader("[ordinary]", deadline=1)
    monkeypatch.setattr("jevdrill.context.monotonic", lambda: 2)
    try:
        with pytest.raises(TimeoutError, match="sanitization deadline"):
            loader.get_single_node()
    finally:
        loader.dispose()


@pytest.mark.parametrize("target", ["password", "config.password"])
@pytest.mark.parametrize("operator", ["=", "+="])
@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_implicit_assignment_targets_reject_before_collection(target, operator, newline):
    text = newline.join(["(", target, f') {operator} "SYNTHETIC_SENTINEL"'])
    with pytest.raises(ContractError, match="multiline credential assignment"):
        collect_context(text, [], [])


@pytest.mark.parametrize("style", ["|", ">"])
@pytest.mark.parametrize(
    "assignment",
    [
        'password = "placeholder"',
        'password += "placeholder"',
        'headers["X-API-Key"] = "placeholder"',
    ],
)
def test_original_yaml_assignment_labels_mask_sibling_values(style, assignment):
    text = f"header: {style}\n  {assignment}\npayload: SYNTHETIC_SENTINEL"
    result = collect_context(text, [], [])["task_representation"]
    assert "SYNTHETIC_SENTINEL" not in result


def test_literal_parser_resource_failure_is_a_boundary_error(monkeypatch):
    def exhausted(_):
        raise MemoryError("synthetic parser resource limit")

    monkeypatch.setattr("jevdrill.context.ast.literal_eval", exhausted)
    with pytest.raises(ContractError, match="sanitization limit"):
        collect_context(r"{'name': '\x61pi_key', 'value': 'SYNTHETIC_SENTINEL'}", [], [])


def test_yaml_aliases_cannot_restore_credentials():
    text = "header: &h\n  name: X-API-Key\n  value: SYNTHETIC_SENTINEL\ncopy: *h"
    with pytest.raises(ContractError, match="YAML graph"):
        collect_context(text, [], [])


def test_sanitization_checks_deadline_during_processing(monkeypatch):
    times = iter([0, 0, 0, 2])
    monkeypatch.setattr("jevdrill.context.monotonic", lambda: next(times))
    with pytest.raises(TimeoutError, match="sanitization deadline"):
        collect_context('{"ordinary": ["context", "more context"]}', [], [], deadline=1)


@pytest.mark.parametrize("label", ["Authorization", "api_key", "password"])
def test_complete_credential_values_preserve_ordinary_next_line(label):
    text = f'{label}: "prefix" \r\n\tSYNTHETIC_SENTINEL\nOrdinary context'
    result = collect_context(text, [], [])["task_representation"]
    assert "SYNTHETIC_SENTINEL" not in result
    assert "Ordinary context" in result


@pytest.mark.parametrize(
    "text",
    [
        'Review the quote "public text\nMore public text',
        "Review the quote 'public text\nMore public text",
        'Ordinary context.\nnote: "name: Content-Type\nvalue: application/json',
        "Ordinary context.\nnote: 'name: Content-Type\nvalue: application/json",
        "Ordinary context.\nname:\n# public note\n  Content-Type\nvalue: application/json",
        "Ordinary context.\n?\n# public note\n  Content-Type\n: application/json",
        "Ordinary context.\nname:\n\vContent-Type\nvalue: application/json",
        "Ordinary context.\u2028?\u2028\u00a0Content-Type\u2028: application/json",
        "'name: ''Content''+''-Type''\nvalue: application/json'",
    ],
)
def test_ordinary_comment_indentation_and_unclosed_quotes_preserve_text(text):
    assert collect_context(text, [], [])["task_representation"] == text


@pytest.mark.parametrize(
    "text",
    [
        "Ordinary context.\nname:\n  'Content'\u00a0+\u00a0'-Type'\nvalue: application/json",
        "Ordinary context.\nname:\n  'Content'\v+\v'-Type'\nvalue: application/json",
        "Ordinary context.\nname: \"'Content'\n\u00a0+'-Type'\"\nvalue: application/json",
        "Ordinary context.\nname: 'Content-Type\u2028 application/json'\nvalue: public",
        'Ordinary context.\nname:\n  "public value\nvalue: application/json',
        "Ordinary context.\n?\n# public note\n  'Content-Type\n: application/json",
        "Ordinary context.\nname: `Content-Type`\nvalue: application/json",
        "Ordinary context.\nname: `'Content'+'-Type'`\nvalue: application/json",
        "headers['Content-Type'] = mime('\u00a0')\nOrdinary context",
        "Ordinary context.\nname: `Content-Type\nvalue: application/json",
        "name: 'str(''Content'')\u2028 +str(''-Type'')'\u2028value: application/json",
        "Ordinary context.\x85? 'str(''Content'')\x85 +str(''-Type'')'\x85: application/json",
    ],
)
def test_ordinary_decoded_and_markdown_members_preserve_source(text):
    assert collect_context(text, [], [])["task_representation"] == text


@pytest.mark.parametrize(
    "text",
    [
        "Ordinary context.\nname: '''Content'' + ''-Type'''\nvalue: application/json",
        "Ordinary context.\nname: 'str(''Content'') + str(''-Type'')'\nvalue: application/json",
        "Ordinary context.\nname:\n# public\n '''Content'' + ''-Type'''\nvalue: application/json",
        "Ordinary context.\n?\n# public\n '''Content'' + ''-Type'''\n: application/json",
        '- "Content"\n "-Type"\n- application/json',
        'Ordinary context.\n- "Content"\n "-Type"\n- application/json',
        "? \vstr('Content')+str('-Type')\n: application/json",
        "Ordinary context.\n? \v'Content' + '-Type'\n: application/json",
        "name: str('Content')\u2028 +str('-Type')\u2028value: application/json",
        "? str('Content')\u2029 +str('-Type')\u2029: application/json",
    ],
)
@pytest.mark.parametrize("presentation", ["plain", "json", "log"])
def test_complete_public_members_preserve_original_source(text, presentation):
    # These unsupported presentations already reject on the preceding head;
    # preserve that boundary as well as its accepted public representations.
    unsupported = (
        "\u2028" in text
        or "\u2029" in text
        or presentation != "plain"
        and (text.startswith('- "') or '\n- "' in text)
        or presentation != "plain"
        and text.startswith("? \vstr(")
        or presentation == "log"
        and "name: 'str(" in text
    )
    if presentation != "plain":
        text = ("LOG " if presentation == "log" else "") + json.dumps(text)
    if unsupported:
        with pytest.raises(ContractError):
            collect_context(text, [], [])
        return
    assert collect_context(text, [], [])["task_representation"] == text


@pytest.mark.parametrize(
    "text",
    [
        'Ordinary context.\nname: "pub\\\nlic"\nvalue: application/json',
        "Ordinary context.\n? str('Content')+str('-Type'): application/json",
        "? \fstr('Content')+str('-Type'): application/json",
        "? \tstr('Content')+str('-Type'): application/json",
    ],
)
@pytest.mark.parametrize("presentation", ["plain", "json", "log"])
def test_decoded_public_members_preserve_source(text, presentation):
    if presentation == "json":
        text = json.dumps(text)
    elif presentation == "log":
        text = json.dumps({"log": text})
    assert collect_context(text, [], [])["task_representation"] == text


def test_public_same_line_vertical_tab_key_preserves_source():
    text = "? \vstr('Content')+str('-Type'): application/json"
    assert collect_context(text, [], [])["task_representation"] == text


@pytest.mark.parametrize(
    "text",
    [
        '{"name": "Content-Type\\nordinary", "value": "application/json"}',
        '{"Content-Type\\nordinary": "application/json"}',
        '["Content-Type\\nordinary", "application/json"]',
        '{"header": "Content-Type: ordinary\\npublic", "payload": "application/json"}',
        "?str('Content')+str('-Type'): application/json",
        "?'Content' + '-Type': application/json",
        "LOG \"? 'Content' + '-Type': application/json\"",
        "`str('Content')+str('-Type'): application/json`",
    ],
)
@pytest.mark.parametrize("encoding", ["plain", "json", "object"])
def test_composed_public_members_preserve_original_source(text, encoding):
    from jevdrill.context import redact

    source = (
        text if encoding == "plain" else json.dumps(text if encoding == "json" else {"log": text})
    )
    assert redact(source) == source


@pytest.mark.parametrize(
    "text",
    [
        "Ordinary context. ? str('Content')+str('-Type'): application/json",
        "LOG ?str('Content')+str('-Type'): application/json",
        "{? 'Content'+'-Type': application/json}",
        "LOG\n[?str('Content')+str('-Type'): application/json]",
        "LOG\u2028? str('Content')+str('-Type'): application/json",
        "The price is $5; why? Content-Type: application/json",
        *[
            "LOG" + ending + "? 'Content'+'-Type': application/json"
            for ending in ("\n", "\r", "\r\n", "\x85", "\u2028", "\u2029")
        ],
    ],
)
@pytest.mark.parametrize("encoding", ["plain", "json", "object"])
def test_explicit_key_placements_preserve_public_source(text, encoding):
    from jevdrill.context import redact

    source = (
        text if encoding == "plain" else json.dumps(text if encoding == "json" else {"log": text})
    )
    assert redact(source) == source
