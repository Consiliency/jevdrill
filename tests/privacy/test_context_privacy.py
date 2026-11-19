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

LOCAL_JSON_PROSE_CASES = (
    'Size 10" {"name":"Authorization","value":"SYNTHETIC_SENTINEL"}',
    'Log 5" pipe [["Authorization", "SYNTHETIC_SENTINEL"]]',
    'Escaped \\"quote\\" [["Authorization", "SYNTHETIC_SENTINEL"]]',
    'Log "col1\tcol2" {"name":"Authorization","value":"SYNTHETIC_SENTINEL"}',
    'Context log [["Authorization\t", "SYNTHETIC_SENTINEL"]]',
    'See payload {"name":"Authorization\t","value":"SYNTHETIC_SENTINEL"}',
    'Here\'s [["Authorization\t", "SYNTHETIC_SENTINEL"]]',
    'See payload {"note":"col1\tcol2","name":"Authorization","value":"SYNTHETIC_SENTINEL"}',
    'Size 10" {"name":"Content-Type","value":"application/json","name":"Authorization","value":"SYNTHETIC_SENTINEL"}',
)


@pytest.mark.parametrize("source", LOCAL_JSON_PROSE_CASES)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_local_json_fragments_after_prose_do_not_leak(source, presentation):
    from jevdrill.context import redact

    presented = _present_public_document(source, presentation)
    try:
        cleaned = redact(presented)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize("prefix", ('Size 10" ', 'Escaped \\"quote\\" ', "Context log "))
@pytest.mark.parametrize(
    "shape",
    ('{"name":"Content-Type","value":"application/json"}', '[["Content-Type","application/json"]]'),
)
def test_public_local_json_after_prose_stays_visible(prefix, shape):
    from jevdrill.context import redact

    source = prefix + shape + "\nNext ordinary line."
    assert redact(source) == source


@pytest.mark.parametrize("expression", ("name is other", "name in other", "name <", "{name:}"))
def test_unresolved_explicit_key_after_prose_rejects(expression):
    from jevdrill.context import redact

    with pytest.raises(ContractError, match="computed explicit key"):
        redact(f"Ordinary context. ? {expression}: SYNTHETIC_SENTINEL")


def test_multiline_subscript_assignment_keeps_value_attached():
    from jevdrill.context import redact

    source = 'if True: headers[\n"Authorization"\n] = "SYNTHETIC_SENTINEL"'
    assert redact(source) == "if True: [redacted]"


@pytest.mark.parametrize("witness_id", range(15))
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_round30_assignment_target_ownership(witness_id, presentation):
    from jevdrill.context import redact

    # These values are inert strings. The sanitizer only parses assignment
    # syntax and must never evaluate a supplied expression.
    sources = (
        'Ordinary "prose ["secret", "SYNTHETIC_SENTINEL"] = 1"',
        'Ordinary "prose ["secret", "SYNTHETIC_SENTINEL"] == 1"',
        'Ordinary "prose ["secret", "SYNTHETIC_SENTINEL"] += 1"',
        'Ordinary "prose headers["secret", "public"] = SYNTHETIC_SENTINEL"',
        'Ordinary "prose headers["secret key"] = SYNTHETIC_SENTINEL"',
        'Ordinary "prose headers["secret/prod"] = SYNTHETIC_SENTINEL"',
        'Ordinary "prose headers["secret"]["public"] = SYNTHETIC_SENTINEL"',
        'Ordinary "prose headers["secret"].value = SYNTHETIC_SENTINEL"',
        'It\'s headers["secret key"] = "SYNTHETIC_SENTINEL" and don\'t',
        'It\'s headers["secret"]["public"] = "SYNTHETIC_SENTINEL" and don\'t',
        'It\'s headers["secret"].value = "SYNTHETIC_SENTINEL" and don\'t',
        'if True: headers[\n"Authorization"\n] = \\\n"SYNTHETIC_SENTINEL"',
        'if True: headers[\n"Authorization"\n] = (\n"SYNTHETIC_SENTINEL"\n)',
        'if True: headers[\n"Authorization key"\n] = "SYNTHETIC_SENTINEL"',
        'if True: (\napi_key,\nother\n) = "SYNTHETIC_SENTINEL", 1',
    )
    source = sources[witness_id]
    if presentation == "json":
        source = json.dumps(source)
    elif presentation == "json-log":
        source = "LOG " + json.dumps(source)
    elif presentation == "backtick":
        source = "`" + source + "`"
    try:
        cleaned = redact(source)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize("break_text", ("\r", "\n", "\r\n"))
@pytest.mark.parametrize("suffix", (" \\{br}= ", " \\{br}: str = ", " \\{br}, other = "))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round30_continued_targets_keep_values_attached(break_text, suffix, presentation):
    from jevdrill.context import redact

    source = (
        "if True: headers["
        + break_text
        + '"Authorization"'
        + break_text
        + "]"
        + suffix.replace("{br}", break_text)
        + '"SYNTHETIC_SENTINEL"'
    )
    if presentation == "json":
        source = json.dumps(source)
    try:
        cleaned = redact(source)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize(
    "source",
    (
        'Ordinary "prose ["Content-Type", "application/json"] = 1"',
        'Ordinary "prose ["Content-Type", "application/json"] == 1"',
        'Ordinary "prose headers["Content-Type"]["public"] = application_json"',
        'if True: headers[\n"Content-Type"\n] = \\\n"application/json"\nNext ordinary line.',
        'if True: headers[\n"Content-Type"\n] = (\n"application/json"\n)\nNext ordinary line.',
        'if True: (\ncontent_type,\nother\n) = "application/json", 1\nNext ordinary line.',
    ),
)
def test_round30_public_assignment_controls_unchanged(source):
    from jevdrill.context import redact

    assert redact(source) == source


def test_round30_dynamic_nested_target_does_not_detach_value():
    from jevdrill.context import redact

    source = 'Ordinary "prose headers["secret"][key].value = SYNTHETIC_SENTINEL"'
    with pytest.raises(ContractError):
        redact(source)
    public = 'Ordinary "prose headers["Content-Type"][key].value = application_json"'
    with pytest.raises(ContractError, match="computed assignment target"):
        redact(public)


@pytest.mark.parametrize(
    "label",
    (
        "s\\u0065cret",
        "\\u0073ecret",
        "Authoriz\\u0061tion",
        "X-API-K\\u0065y",
        "access_tok\\u0065n",
        "client_s\\u0065cret",
    ),
)
@pytest.mark.parametrize(
    "template",
    (
        'Ordinary "prose ["{label}", "SYNTHETIC_SENTINEL"] = 1"',
        'Ordinary "prose ["{label}", "SYNTHETIC_SENTINEL"] == 1"',
        'Ordinary "prose ["{label}", "SYNTHETIC_SENTINEL"] += 1"',
        'Ordinary "prose headers["{label}"]["public"].value = SYNTHETIC_SENTINEL"',
        'It\'s headers["{label}"].value = "SYNTHETIC_SENTINEL" and don\'t',
        'Ordinary "prose [["{label}", "SYNTHETIC_SENTINEL"]] = 1"',
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round30_decoded_local_json_labels_keep_values_attached(label, template, presentation):
    from jevdrill.context import redact

    source = template.format(label=label)
    if presentation == "json":
        source = json.dumps(source)
    try:
        cleaned = redact(source)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize("label", ("Content-Type", "Content-T\\u0079pe"))
@pytest.mark.parametrize(
    "template",
    (
        'Ordinary "prose ["{label}", "application/json"] = 1"',
        'Ordinary "prose headers["{label}"]["public"].value = application_json"',
        'headers[\n"{label}"\n] = "application/json"\nNext ordinary line.',
    ),
)
def test_round30_decoded_public_label_preserves_original_text(label, template):
    from jevdrill.context import redact

    source = template.format(label=label)
    assert redact(source) == source


@pytest.mark.parametrize(
    "fragment",
    (
        '["public", ["s\\u0065cret", "SYNTHETIC_SENTINEL"]]',
        '[["public", 1], ["Authoriz\\u0061tion", "SYNTHETIC_SENTINEL"]]',
        '{"name":"public","name":"X-API-K\\u0065y","value":"SYNTHETIC_SENTINEL"}',
    ),
)
def test_round30_nested_and_duplicate_encoded_members_do_not_detach(fragment):
    from jevdrill.context import redact

    source = 'Ordinary "prose ' + fragment + ' = 1"'
    try:
        cleaned = redact(source)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize(
    "prefix",
    ("if True: ", "while ready: ", "if True:\n    ", "for item in items:\n    "),
)
@pytest.mark.parametrize("continuation", (" \\\n= ", " \\\r\n= ", " \\\n += "))
@pytest.mark.parametrize("label", ('"Authorization"', '"X-API-Key"'))
def test_continued_multiline_subscript_assignment_owns_sensitive_value(prefix, continuation, label):
    from jevdrill.context import redact

    source = prefix + f"headers[\n{label}\n]" + continuation + '"SYNTHETIC_SENTINEL"'
    try:
        cleaned = redact(source)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize("continuation", (" \\\n= ", " \\\r\n= ", " \\\n += "))
def test_continued_public_subscript_assignment_keeps_next_line(continuation):
    from jevdrill.context import redact

    source = (
        'if True: headers[\n"Content-Type"\n]'
        + continuation
        + '"application/json"\nNext ordinary line.'
    )
    assert redact(source) == source


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

ESCAPED_LOCAL_RECORD_CASES = (
    "Don't {'Auth\\x6frization': SYNTHETIC_SENTINEL}",
    "It's fine ? 'Auth\\x6frization': SYNTHETIC_SENTINEL",
    "Don't [? 'Auth\\x6frization': SYNTHETIC_SENTINEL]",
    "It's fine; headers['Auth\\x6frization'] = 'SYNTHETIC_SENTINEL'",
    "He said \"hi ? 'Auth\\x6frization': SYNTHETIC_SENTINEL",
    "It's fine ? 'Auth\\157rization': SYNTHETIC_SENTINEL",
    "It's fine ? 'Auth\\N{LATIN SMALL LETTER O}rization': SYNTHETIC_SENTINEL",
    'It\'s fine ? "Auth\\x6frization": SYNTHETIC_SENTINEL',
    "It's fine ? 'api\\x5fkey': SYNTHETIC_SENTINEL",
    "It's fine ? 'pass\\x77ord': SYNTHETIC_SENTINEL",
    "It's fine ? 'se\\x63ret': SYNTHETIC_SENTINEL",
    "It's fine ? 'access_\\x74oken': SYNTHETIC_SENTINEL",
    "It's fine ? 'X-API-\\x4bey': SYNTHETIC_SENTINEL",
)

TRIPLE_QUOTED_COMPOSITION = "It's fine ? '''Author'' ''ization''': SYNTHETIC_SENTINEL"

PUBLIC_NEL_MEMBER = (
    "Ordinary context.\x85? 'str(''Content'')\x85 +str(''-Type'')'\x85: application/json"
)

STRUCTURAL_RECORD_SHAPES = (
    "[['Authorization', 'SYNTHETIC_SENTINEL']]",
    "[['X-API-Key', 'SYNTHETIC_SENTINEL']]",
    "[('Authorization', 'SYNTHETIC_SENTINEL')]",
    "{'Auth\\x6frization': 'SYNTHETIC_SENTINEL'}",
    "{'Auth\\x6frization\\'x': 'SYNTHETIC_SENTINEL'}",
    "{'name':'Auth\\x6frization','value':'SYNTHETIC_SENTINEL'}",
    "{'name':'\\u0041uthorization','value':'SYNTHETIC_SENTINEL'}",
    "[['Auth\\x6frization', 'SYNTHETIC_SENTINEL']]",
    "headers['Auth\\x6frization']: str = 'SYNTHETIC_SENTINEL'",
    "headers['Auth\\x6frization'] @= 'SYNTHETIC_SENTINEL'",
    "headers['Auth\\x6frization'], x = 'SYNTHETIC_SENTINEL', 1",
    "headers['Auth\\x6frization'][0] = 'SYNTHETIC_SENTINEL'",
    "headers['Auth\\x6frization'] \\\n= 'SYNTHETIC_SENTINEL'",
    "headers['Auth\\x6frization'\n] = 'SYNTHETIC_SENTINEL'",
    "? prefix and suffix: SYNTHETIC_SENTINEL",
    "? prefix if condition else suffix: SYNTHETIC_SENTINEL",
) + tuple(
    f"? prefix {operator} suffix: SYNTHETIC_SENTINEL"
    for operator in ("*", "**", "@", "%", "&", "|", "^", "<<", ">>", "//", "-", "/")
)


PROSE_SUBSCRIPT_ASSIGNMENT_PREFIXES = (
    "Here is ",
    "Ordinary ",
    "It's fine ",
    'He said "hi ',
)
PROSE_SUBSCRIPT_ASSIGNMENT_KEYS = (
    "'Author'+'ization'",
    "'Authorization'",
    "'Auth\\x6frization'",
)


@pytest.mark.parametrize("prefix", PROSE_SUBSCRIPT_ASSIGNMENT_PREFIXES)
@pytest.mark.parametrize("key", PROSE_SUBSCRIPT_ASSIGNMENT_KEYS)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_prose_prefixed_subscript_assignments_do_not_leak(prefix, key, presentation):
    from jevdrill.context import redact

    source = _present_public_document(
        f"{prefix}headers[{key}] = 'SYNTHETIC_SENTINEL'", presentation
    )
    try:
        cleaned = redact(source)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize("key", PROSE_SUBSCRIPT_ASSIGNMENT_KEYS)
def test_standalone_subscript_assignment_preserves_next_line(key):
    from jevdrill.context import redact

    source = f"headers[{key}] = 'SYNTHETIC_SENTINEL'\nNext ordinary line."
    cleaned = redact(source)
    assert cleaned == "[redacted]\nNext ordinary line."


@pytest.mark.parametrize("prefix", PROSE_SUBSCRIPT_ASSIGNMENT_PREFIXES)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_prose_prefixed_public_subscript_assignment_stays_visible(prefix, presentation):
    from jevdrill.context import redact

    source = _present_public_document(
        prefix + "headers['Content-Type'] = 'application/json'", presentation
    )
    assert redact(source) == source


@pytest.mark.parametrize("prefix", ("Don't ", 'He said "hi ', "Ordinary "))
@pytest.mark.parametrize("shape", STRUCTURAL_RECORD_SHAPES)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_local_complete_records_survive_no_presentation(prefix, shape, presentation):
    from jevdrill.context import redact

    source = _present_public_document(prefix + shape, presentation)
    try:
        cleaned = redact(source)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize("prefix", ("Don't ", 'He said "hi ', "Ordinary "))
@pytest.mark.parametrize(
    "separator", ("\n", "\r", "\r\n", "\x85", "\u2028", "\u2029", " # comment\n")
)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_local_map_key_colon_line_boundaries(prefix, separator, presentation):
    from jevdrill.context import redact

    source = _present_public_document(
        prefix + "{'Auth\\x6frization'" + separator + ": 'SYNTHETIC_SENTINEL'}",
        presentation,
    )
    try:
        cleaned = redact(source)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_structural_public_and_assignment_controls(presentation):
    from jevdrill.context import redact

    for text in (
        "Don't [['Content-Type', 'application/json']]",
        "Don't [('Content-Type', 'application/json')]",
        "Don't {'Content\\x2dType'\n: 'application/json'}",
        "Don't {'Content\\x2dType\\'x': 'application/json'}",
        "Ordinary context. ? Content-Type: application/json",
        "Ordinary context. ? application/json: visible",
        "Ordinary context. ? +7: visible",
        "Ordinary context. ? a.b: visible",
    ):
        source = _present_public_document(text, presentation)
        assert redact(source) == source
    assert redact("headers['Auth\\x6frization'] = 'SYNTHETIC_SENTINEL'\nNext ordinary line.") == (
        "[redacted]\nNext ordinary line."
    )


def _present_public_document(text, presentation):
    return (
        text
        if presentation == "plain"
        else json.dumps(text)
        if presentation == "json"
        else json.dumps({"log": text})
        if presentation == "json-log"
        else f"`{text}`"
    )


@pytest.mark.parametrize(
    "prose", ("Ordinary context.", "It's ready.", 'She said "hello".', "Don't panic.")
)
@pytest.mark.parametrize("newline", ("\n", "\r\n", "\x85", "\u2028"))
@pytest.mark.parametrize(
    "key",
    (
        "'str(''Content'')+str(''-Type'')'",
        "'str(''X'') + str(''-Mode'')'",
        "'Ac''cept'",
        "'X-Trace-Id'",
        "'Content\\x2dType'",
    ),
)
@pytest.mark.parametrize("value", ("application/json", "text/plain; charset=utf-8", "enabled"))
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_complete_public_explicit_key_metamorphic(prose, newline, key, value, presentation):
    from jevdrill.context import redact

    text = f"{prose}{newline}? {key}{newline}: {value}"
    source = _present_public_document(text, presentation)
    assert redact(source) == source


@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
@pytest.mark.parametrize(
    "suffix",
    (
        "? 'str(''Author'')+str(''ization'')'\x85: visible",
        "? 'unknown(''Content'')'\x85: visible",
        "? 'str(''Content'')+str(''-Type'')\x85: visible",
        "? 'str(''Content'')+str(''-Type'')'\x85: Bearer SYNTHETIC_SENTINEL",
        "? 'str(''Content'')+str(''-Type'')'\x85: visible\x85Authorization: SYNTHETIC_SENTINEL",
        "? 'str(''Content'')+str(''-Type'')'\x85: visible; Authorization: SYNTHETIC_SENTINEL",
    ),
)
def test_public_explicit_key_paired_controls(presentation, suffix):
    from jevdrill.context import redact

    source = _present_public_document("She said 'hello'.\x85" + suffix, presentation)
    try:
        cleaned = redact(source)
    except ContractError:
        return
    assert cleaned != source
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize("text", ESCAPED_LOCAL_RECORD_CASES)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_local_escaped_credential_labels_reject(text, presentation):
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


@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_triple_quoted_composition_behind_prose_rejects(presentation):
    from jevdrill.context import redact

    text = TRIPLE_QUOTED_COMPOSITION
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
    assert redact("It's fine ? '''Content'' ''-Type''': application/json") == (
        "It's fine ? '''Content'' ''-Type''': application/json"
    )


@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_complete_public_nel_member_preserves_all_presentations(presentation):
    from jevdrill.context import redact

    text = PUBLIC_NEL_MEMBER
    source = (
        text
        if presentation == "plain"
        else json.dumps(text)
        if presentation == "json"
        else json.dumps({"log": text})
        if presentation == "json-log"
        else f"`{text}`"
    )
    assert redact(source) == source
    public_escape = "It's fine ? 'Content\\x2dType': application/json"
    assert redact(public_escape) == public_escape


@pytest.mark.parametrize(
    "text",
    (
        "Ordinary context.\x85? 'str(''Author'')\x85 +str(''ization'')'\x85: SYNTHETIC_SENTINEL",
        "Ordinary context.\x85? 'str(''Content'')\x85 +unknown(''-Type'')'\x85: application/json",
        "Ordinary context.\x85? 'str(''Content'')\x85 +str(''-Type'')\x85: application/json",
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_public_nel_exception_keeps_computed_and_incomplete_rejections(text, presentation):
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


@pytest.mark.parametrize("label_parts", (("Author", "ization"), ("api_", "key"), ("pass", "word")))
@pytest.mark.parametrize("presentation", ("plain", "json", "json-log", "backtick"))
def test_multiline_quoted_composed_credential_key_rejects(label_parts, presentation):
    from jevdrill.context import redact

    left, right = label_parts
    text = (
        "Ordinary context.\x85? 'str(''"
        + left
        + "'')\x85 +str(''"
        + right
        + "'')'\x85: SYNTHETIC_SENTINEL"
    )
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


ROUND31_MARKER = "SYNTHETIC_R30_ASTRA_SENTINEL"
ROUND31_TARGET_WITNESSES = (
    'It\'s headers["secret"].é = "' + ROUND31_MARKER + "\" and don't",
    'Ordinary "prose headers["secret"]: \\\nstr = "' + ROUND31_MARKER + '""',
    'Ordinary "prose headers["secret"][key \\\n] = "' + ROUND31_MARKER + '""',
)


@pytest.mark.parametrize("source", ROUND31_TARGET_WITNESSES)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round31_exact_target_ownership_witnesses(source, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert ROUND31_MARKER not in cleaned


@pytest.mark.parametrize("break_text", ("\r", "\n", "\r\n"))
@pytest.mark.parametrize("label", ("secret", "s\\u0065cret"))
@pytest.mark.parametrize(
    "tail",
    (
        '.é = "{marker}"',
        '.e\u0301 = "{marker}"',
        '.K = "{marker}"',
        '[outer[inner]] = "{marker}"',
        ': \\{break_text}dict[str, list[int]] = "{marker}"',
        ', other \\{break_text}= "{marker}"',
        ' \\{break_text}+= "{marker}"',
        ' \\{break_text}== "{marker}"',
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round31_sensitive_target_tail_remains_attached(break_text, label, tail, presentation):
    from jevdrill.context import redact

    source = (
        'Ordinary "prose headers["'
        + label
        + '"]'
        + tail.format(break_text=break_text, marker=ROUND31_MARKER)
        + '"'
    )
    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert ROUND31_MARKER not in cleaned


@pytest.mark.parametrize("source", ROUND31_TARGET_WITNESSES)
def test_round31_exact_public_content_type_twins_remain_unchanged(source):
    from jevdrill.context import redact

    public = source.replace("secret", "Content-Type").replace(ROUND31_MARKER, "application/json")
    assert redact(public) == public


def test_round31_ordinary_following_line_is_not_credential_value():
    from jevdrill.context import redact

    source = 'Ordinary "prose headers["secret"]\nordinary next line ' + ROUND31_MARKER + '"'
    assert ROUND31_MARKER in redact(source)
    public = source.replace("secret", "Content-Type").replace(ROUND31_MARKER, "application/json")
    assert redact(public) == public


ROUND31_ALT_TARGET_WITNESSES = (
    'Ordinary "prose headers["secret"]. value = SYNTHETIC_SENTINEL"',  # R30-W1
    'It\'s headers["secret"]. value = "SYNTHETIC_SENTINEL" and don\'t',  # R30-W2
    'Ordinary "prose headers["secret"]: str \\\n= SYNTHETIC_SENTINEL"',  # R30-W3
    'Ordinary "prose headers["secret"], other \\\n= SYNTHETIC_SENTINEL"',  # R30-W4
    'Note that secret["public"] = "SYNTHETIC_SENTINEL"',  # R30-W5
    'Note that api_key["public"] = "SYNTHETIC_SENTINEL"',  # R30-W6
    'Note that cfg.secret["public"] = "SYNTHETIC_SENTINEL"',  # R30-W7
    'Note that secret, other = "SYNTHETIC_SENTINEL", 1',  # R30-W8
    'Ordinary "prose" secret["public"] = "SYNTHETIC_SENTINEL"',  # R30-W9
    'It\'s secret["public"] = "SYNTHETIC_SENTINEL" and don\'t',  # R30-W10
    'Note that api_key \\\n= "SYNTHETIC_SENTINEL"',  # R30-W11
)

ROUND31_ALT_PUBLIC_TWINS = (
    'Ordinary "prose headers["Content-Type"]. value = application/json"',  # R30-W1
    'It\'s headers["Content-Type"]. value = "application/json" and don\'t',  # R30-W2
    'Ordinary "prose headers["Content-Type"]: str \\\n= application/json"',  # R30-W3
    'Ordinary "prose headers["Content-Type"], other \\\n= application/json"',  # R30-W4
    'Note that content_type["public"] = "application/json"',  # R30-W5
    'Note that content_type["public"] = "application/json"',  # R30-W6
    'Note that cfg.content_type["public"] = "application/json"',  # R30-W7
    'Note that content_type, other = "application/json", 1',  # R30-W8
    'Ordinary "prose" content_type["public"] = "application/json"',  # R30-W9
    'It\'s content_type["public"] = "application/json" and don\'t',  # R30-W10
    'Note that content_type \\\n= "application/json"',  # R30-W11
)


@pytest.mark.parametrize("source", ROUND31_ALT_TARGET_WITNESSES)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round31_alt_exact_target_ownership_witnesses(source, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize("source", ROUND31_ALT_PUBLIC_TWINS[:2] + ROUND31_ALT_PUBLIC_TWINS[3:])
def test_round31_alt_supported_public_twins_remain_unchanged(source):
    from jevdrill.context import redact

    assert redact(source) == source


def test_round31_alt_public_annotation_retains_baseline_rejection():
    from jevdrill.context import redact

    with pytest.raises(ContractError):
        redact(ROUND31_ALT_PUBLIC_TWINS[2])


@pytest.mark.parametrize("break_text", ("\r", "\n", "\r\n"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round31_alt_bare_name_explicit_continuations(break_text, presentation):
    from jevdrill.context import redact

    source = "Note that api_key " + chr(92) + break_text + '= "SYNTHETIC_SENTINEL"'
    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert "SYNTHETIC_SENTINEL" not in cleaned


@pytest.mark.parametrize(
    "source",
    (
        'Note that content_type["public"] = "application/json"',
        'Note that cfg.content_type["public"] = "application/json"',
        'Note that content_type, other = "application/json", 1',
        "Note that content_type " + chr(92) + chr(10) + '= "application/json"',
        "Note that the secret, however, is x=1",
    ),
)
def test_round31_alt_public_name_and_prose_controls(source):
    from jevdrill.context import redact

    assert redact(source) == source


ROUND31_VALID_IDENTIFIER_WITNESSES = (
    'Note that secret́["public"] = "SYNTHETIC_PARENT_SENTINEL"',
    'It\'s secret́["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that cfg.secret́["public"] = "SYNTHETIC_PARENT_SENTINEL"',
    'It\'s cfg.secret́["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that secret́, other = "SYNTHETIC_PARENT_SENTINEL"',
    "It's secret́, other = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
    'Note that secret·x["public"] = "SYNTHETIC_PARENT_SENTINEL"',
    'It\'s secret·x["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that cfg.secret·x["public"] = "SYNTHETIC_PARENT_SENTINEL"',
    'It\'s cfg.secret·x["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that secret·x, other = "SYNTHETIC_PARENT_SENTINEL"',
    "It's secret·x, other = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
    'Note that ｓｅｃｒｅｔ["public"] = "SYNTHETIC_PARENT_SENTINEL"',
    'It\'s ｓｅｃｒｅｔ["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that cfg.ｓｅｃｒｅｔ["public"] = "SYNTHETIC_PARENT_SENTINEL"',
    'It\'s cfg.ｓｅｃｒｅｔ["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that ｓｅｃｒｅｔ, other = "SYNTHETIC_PARENT_SENTINEL"',
    "It's ｓｅｃｒｅｔ, other = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
    'Note that 𝓼𝓮𝓬𝓻𝓮𝓽["public"] = "SYNTHETIC_PARENT_SENTINEL"',
    'It\'s 𝓼𝓮𝓬𝓻𝓮𝓽["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that cfg.𝓼𝓮𝓬𝓻𝓮𝓽["public"] = "SYNTHETIC_PARENT_SENTINEL"',
    'It\'s cfg.𝓼𝓮𝓬𝓻𝓮𝓽["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that 𝓼𝓮𝓬𝓻𝓮𝓽, other = "SYNTHETIC_PARENT_SENTINEL"',
    "It's 𝓼𝓮𝓬𝓻𝓮𝓽, other = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
    'Note that api_ｋｅｙ["public"] = "SYNTHETIC_PARENT_SENTINEL"',
    'It\'s api_ｋｅｙ["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that cfg.api_ｋｅｙ["public"] = "SYNTHETIC_PARENT_SENTINEL"',
    'It\'s cfg.api_ｋｅｙ["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that api_ｋｅｙ, other = "SYNTHETIC_PARENT_SENTINEL"',
    "It's api_ｋｅｙ, other = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
)


@pytest.mark.parametrize("source", ROUND31_VALID_IDENTIFIER_WITNESSES)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round31_valid_unicode_identifier_ownership(source, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert "SYNTHETIC_PARENT_SENTINEL" not in cleaned


ROUND31_VALID_IDENTIFIER_PUBLIC_TWINS = (
    'Note that content_typé["public"] = "application/json"',
    'It\'s content_typé["public"] = "application/json" and don\'t',
    'Note that cfg.content_typé["public"] = "application/json"',
    'It\'s cfg.content_typé["public"] = "application/json" and don\'t',
    'Note that content_typé, other = "application/json"',
    "It's content_typé, other = \"application/json\" and don't",
    'Note that content·type["public"] = "application/json"',
    'It\'s content·type["public"] = "application/json" and don\'t',
    'Note that cfg.content·type["public"] = "application/json"',
    'It\'s cfg.content·type["public"] = "application/json" and don\'t',
    'Note that content·type, other = "application/json"',
    "It's content·type, other = \"application/json\" and don't",
    'Note that ｐｕｂｌｉｃ["public"] = "application/json"',
    'It\'s ｐｕｂｌｉｃ["public"] = "application/json" and don\'t',
    'Note that cfg.ｐｕｂｌｉｃ["public"] = "application/json"',
    'It\'s cfg.ｐｕｂｌｉｃ["public"] = "application/json" and don\'t',
    'Note that ｐｕｂｌｉｃ, other = "application/json"',
    "It's ｐｕｂｌｉｃ, other = \"application/json\" and don't",
    'Note that 𝓹𝓾𝓫𝓵𝓲𝓬["public"] = "application/json"',
    'It\'s 𝓹𝓾𝓫𝓵𝓲𝓬["public"] = "application/json" and don\'t',
    'Note that cfg.𝓹𝓾𝓫𝓵𝓲𝓬["public"] = "application/json"',
    'It\'s cfg.𝓹𝓾𝓫𝓵𝓲𝓬["public"] = "application/json" and don\'t',
    'Note that 𝓹𝓾𝓫𝓵𝓲𝓬, other = "application/json"',
    "It's 𝓹𝓾𝓫𝓵𝓲𝓬, other = \"application/json\" and don't",
    'Note that content_ｔｙｐｅ["public"] = "application/json"',
    'It\'s content_ｔｙｐｅ["public"] = "application/json" and don\'t',
    'Note that cfg.content_ｔｙｐｅ["public"] = "application/json"',
    'It\'s cfg.content_ｔｙｐｅ["public"] = "application/json" and don\'t',
    'Note that content_ｔｙｐｅ, other = "application/json"',
    "It's content_ｔｙｐｅ, other = \"application/json\" and don't",
)


@pytest.mark.parametrize("source", ROUND31_VALID_IDENTIFIER_PUBLIC_TWINS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round31_valid_unicode_public_identifier_twins(source, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    if "𝓹𝓾𝓫𝓵𝓲𝓬" in source and presentation == "json":
        with pytest.raises(ContractError):
            redact(text)
    else:
        assert redact(text) == text


ROUND31_MIXED_VALID_IDENTIFIER_WITNESSES = (
    'Note that secret́["public"] = "SYNTHETIC_PARENT_SENTINEL"wrong',
    'It\'s secret́["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that cfg.secret́["public"] = "SYNTHETIC_PARENT_SENTINEL"wrong',
    'It\'s cfg.secret́["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that secret́, other = "SYNTHETIC_PARENT_SENTINEL"wrong',
    "It's secret́, other = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
    'Note that secret . value = "SYNTHETIC_PARENT_SENTINEL"wrong',
    "It's secret . value = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
    'Note that secret ["public"] = "SYNTHETIC_PARENT_SENTINEL"wrong',
    'It\'s secret ["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that secret: str = "SYNTHETIC_PARENT_SENTINEL"wrong',
    "It's secret: str = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
    'Note that api_keý \\\n = "SYNTHETIC_PARENT_SENTINEL"wrong',
    "It's api_keý \\\n = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
    'Note that secret·x["public"] = "SYNTHETIC_PARENT_SENTINEL"wrong',
    'It\'s secret·x["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
)


@pytest.mark.parametrize("source", ROUND31_MIXED_VALID_IDENTIFIER_WITNESSES)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round31_mixed_valid_unicode_identifier_ownership(source, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert "SYNTHETIC_PARENT_SENTINEL" not in cleaned


@pytest.mark.parametrize("break_text", ("\r", "\n", "\r\n"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round31_combining_public_continuation_twin(break_text, presentation):
    from jevdrill.context import redact

    source = "Note that content_typé " + chr(92) + break_text + '= "application/json"'
    text = source if presentation == "plain" else json.dumps(source)
    assert redact(text) == text


ROUND31_MIXED_VALID_IDENTIFIER_LEAK_WITNESSES = (
    'Note that secret́["public"] = "SYNTHETIC_PARENT_SENTINEL"wrong',
    'It\'s secret́["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that cfg.secret́["public"] = "SYNTHETIC_PARENT_SENTINEL"wrong',
    'It\'s cfg.secret́["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
    'Note that secret́, other = "SYNTHETIC_PARENT_SENTINEL"wrong',
    "It's secret́, other = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
    'Note that api_keý \\\n = "SYNTHETIC_PARENT_SENTINEL"wrong',
    "It's api_keý \\\n = \"SYNTHETIC_PARENT_SENTINEL\" and don't",
    'Note that secret·x["public"] = "SYNTHETIC_PARENT_SENTINEL"wrong',
    'It\'s secret·x["public"] = "SYNTHETIC_PARENT_SENTINEL" and don\'t',
)


# Exact C31 assignment witnesses W1–W5/W7 and A31 raw-XID witnesses.
# W6 is a comparison and remains an ordinary-data control.
ROUND32_ASSIGNMENT_WITNESSES = (
    'Ordinary prose, (secret) = "SYNTHETIC_R31_CORRECTNESS_SENTINEL"',
    'Ordinary prose, (api_key) = "SYNTHETIC_R31_CORRECTNESS_SENTINEL"',
    'Ordinary prose, (secret, other) = "SYNTHETIC_R31_CORRECTNESS_SENTINEL", 1',
    'Ordinary prose, [secret, other] = ["SYNTHETIC_R31_CORRECTNESS_SENTINEL", 1]',
    "It's (password) = \"SYNTHETIC_R31_CORRECTNESS_SENTINEL\" and don't",
    'Ordinary "prose" (authorization) = "SYNTHETIC_R31_CORRECTNESS_SENTINEL"',
    'Note that secret\u0301 = "SYNTHETIC_R31_ASTRA_MARKER"',
    'Note that secret\u0301 += "SYNTHETIC_R31_ASTRA_MARKER"',
    "It's secret\u0301 = \"SYNTHETIC_R31_ASTRA_MARKER\" and don't",
    "It's secret\u0301 += \"SYNTHETIC_R31_ASTRA_MARKER\" and don't",
)

ROUND32_NAMED_EXPR_WITNESSES = (
    'Note that (secret\u0301 := "SYNTHETIC_R32_PARENT_SENTINEL")',
    "It's (secret\u0301 := \"SYNTHETIC_R32_PARENT_SENTINEL\") and don't",
)


@pytest.mark.parametrize("source", ROUND32_ASSIGNMENT_WITNESSES)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_exact_assignment_owners_never_reach_output(source, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    with pytest.raises(ContractError, match="credential assignment"):
        redact(text)


@pytest.mark.parametrize("source", ROUND32_NAMED_EXPR_WITNESSES)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_exact_named_expression_owners_reject(source, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    with pytest.raises(ContractError, match="credential assignment"):
        redact(text)


@pytest.mark.parametrize(
    "expression",
    (
        '(secret\u0301 := "SYNTHETIC_R32_SENTINEL")',
        '((secret\u0301 := "SYNTHETIC_R32_SENTINEL"))',
        '[secret\u0301 := "SYNTHETIC_R32_SENTINEL"]',
        'cfg[secret\u0301 := "SYNTHETIC_R32_SENTINEL"]',
        '((secret\u0301 := "SYNTHETIC_R32_SENTINEL") if True else 0)',
        '(lambda: (secret\u0301 := "SYNTHETIC_R32_SENTINEL"))',
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_named_expression_balanced_owner_grammar(expression, presentation):
    import ast

    from jevdrill.context import redact

    assert isinstance(ast.parse(expression, mode="eval"), ast.Expression)
    source = "Note that " + expression
    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert "SYNTHETIC_R32_SENTINEL" not in cleaned


@pytest.mark.parametrize("keyword", ("if", "while"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_named_expression_condition_owner(keyword, presentation):
    import ast

    from jevdrill.context import redact

    statement = f'{keyword} secret\u0301 := "SYNTHETIC_R32_SENTINEL": pass'
    assert isinstance(ast.parse(statement), ast.Module)
    source = "Note that " + statement
    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert "SYNTHETIC_R32_SENTINEL" not in cleaned


@pytest.mark.parametrize(
    "name",
    (
        "secret\u0301",
        "secret\u00b7x",
        "secret\u200c",
        "secret\u200d",
        "ｓｅｃｒｅｔ",
        "𝓼𝓮𝓬𝓻𝓮𝓽",
        "api_ｋｅｙ",
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_named_expression_runtime_identifier_spellings(name, presentation):
    import ast

    from jevdrill.context import redact

    assert name.isidentifier()
    assert isinstance(ast.parse(f"({name} := 1)", mode="eval"), ast.Expression)
    source = f'Note that ({name} := "SYNTHETIC_R32_SENTINEL")'
    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert "SYNTHETIC_R32_SENTINEL" not in cleaned


@pytest.mark.parametrize(
    "name",
    (
        "content_type\u0301",
        "public\u00b7x",
        "public\u200c",
        "public\u200d",
        "ｃｏｎｔｅｎｔ_ｔｙｐｅ",
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_public_named_expression_runtime_identifier_twins(name, presentation):
    from jevdrill.context import redact

    source = f'Note that ({name} := "application/json")'
    text = source if presentation == "plain" else json.dumps(source)
    assert redact(text) == text


@pytest.mark.parametrize(
    "source",
    (
        'Note that (content_type := "application/json")',
        "It's (content_type := \"application/json\") and don't",
        'Note that ((content_type := "application/json") if True else 0)',
        'Note that if content_type := "application/json": pass',
        'Note that while content_type := "application/json": pass',
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_public_named_expression_controls(source, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    assert redact(text) == text


ROUND32_GRAMMAR_TARGETS = (
    "secret",
    "api_key",
    "secret\u0301",
    "secret\u00b7x",
    "secret\u200c",
    "secret\u200d",
    "ｓｅｃｒｅｔ",
    "cfg.secret\u0301",
    "(secret)",
    "((secret))",
    "(secret, other)",
    "[secret, other]",
    "(secret, (other,))",
    "[other, *secret]",
    'secret[\n"public"\n]',
)


def _round32_valid_target_operator(target, operator):
    import ast

    try:
        ast.parse(target + operator + '"SYNTHETIC_R32_SENTINEL"')
    except SyntaxError:
        return False
    return True


ROUND32_VALID_TARGET_OPERATOR_PAIRS = tuple(
    (target, operator)
    for target in ROUND32_GRAMMAR_TARGETS
    for operator in (" = ", " += ", " : str = ")
    if _round32_valid_target_operator(target, operator)
)
assert len(ROUND32_VALID_TARGET_OPERATOR_PAIRS) == 37


@pytest.mark.parametrize("target,operator", ROUND32_VALID_TARGET_OPERATOR_PAIRS)
@pytest.mark.parametrize("prefix", ("Note that ", "It's "))
def test_round32_runtime_valid_local_target_grammar(target, operator, prefix):
    import ast

    from jevdrill.context import redact

    statement = target + operator + '"SYNTHETIC_R32_SENTINEL"'
    assert isinstance(ast.parse(statement), ast.Module)
    source = prefix + statement + (" and don't" if prefix.startswith("It's") else "")
    for text in (source, json.dumps(source)):
        try:
            cleaned = redact(text)
        except ContractError:
            continue
        assert "SYNTHETIC_R32_SENTINEL" not in cleaned


@pytest.mark.parametrize("linebreak", ("\n", "\r", "\r\n"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_explicit_continuation_owns_sensitive_name(linebreak, presentation):
    from jevdrill.context import redact

    source = "Note that api_key\u0301 " + chr(92) + linebreak + '= "SYNTHETIC_R32_SENTINEL"'
    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert "SYNTHETIC_R32_SENTINEL" not in cleaned


@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_complete_standalone_target_still_redacts(presentation):
    from jevdrill.context import redact

    for source in (
        '(secret) = "SYNTHETIC_R32_SENTINEL"',
        '(secret, other) = "SYNTHETIC_R32_SENTINEL", 1',
        '[secret, other] = ["SYNTHETIC_R32_SENTINEL", 1]',
    ):
        text = source if presentation == "plain" else json.dumps(source)
        assert redact(text) == ("[redacted]" if presentation == "plain" else '"[redacted]"\n')


@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_public_and_ordinary_following_line_controls(presentation):
    from jevdrill.context import redact

    for source in (
        'Ordinary prose, (content_type) = "application/json"',
        'Note that cfg.public["content_type"] = "application/json"',
        'Note that public["content_type"] = "application/json"',
        'Note that cfg[content_type] = "application/json"',
        "The secret (to success) is patience.",
        'Ordinary prose, (secret) == "SYNTHETIC_R31_CORRECTNESS_SENTINEL"',
    ):
        text = source if presentation == "plain" else json.dumps(source)
        assert redact(text) == text
    source = 'secret = "SYNTHETIC_R32_SENTINEL"\nOrdinary next line.'
    text = source if presentation == "plain" else json.dumps(source)
    cleaned = redact(text)
    assert "SYNTHETIC_R32_SENTINEL" not in cleaned
    assert "Ordinary next line." in cleaned


@pytest.mark.parametrize("character", ("\u0301", "\u00b7", "\u200c", "\u200d"))
def test_round32_identifier_continuation_matches_runtime_parser(character):
    import ast

    spelling = "secret" + character
    assert spelling.isidentifier()
    assert ("a" + character).isidentifier()
    assert isinstance(ast.parse(spelling + " = 1").body[0], ast.Assign)


@pytest.mark.parametrize(
    "name",
    (
        "content_type\u0301",
        "public\u00b7x",
        "public\u200c",
        "public\u200d",
        "ｃｏｎｔｅｎｔ_ｔｙｐｅ",
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_runtime_valid_public_identifier_controls(name, presentation):
    import ast

    from jevdrill.context import redact

    assert name.isidentifier()
    assert isinstance(ast.parse(name + " = 1").body[0], ast.Assign)
    source = f'Note that {name}["public"] = "application/json"'
    text = source if presentation == "plain" else json.dumps(source)
    assert redact(text) == text


def test_round32_ordinary_long_paragraph_stays_ordinary():
    from jevdrill.context import redact

    source = "The secret is patience. " * 1000 + "public = 1"
    assert redact(source) == source


@pytest.mark.parametrize(
    "source,expected",
    (
        (
            "alpha objective-private-sentinel api_key=credential-sentinel",
            "alpha objective-private-sentinel [redacted]",
        ),
        (
            "alpha description-private-sentinel password=secret-sentinel",
            "alpha description-private-sentinel [redacted]",
        ),
        ("alpha access_token=context-secret-sentinel", "alpha [redacted]"),
        (
            'alpha api_key = "synthetic"\nordinary next line',
            "alpha [redacted]\nordinary next line",
        ),
        (
            "alpha api_key=one two\n  folded synthetic\nordinary next line",
            "alpha [redacted]\nordinary next line",
        ),
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round32_complete_plain_records_keep_redaction_path(source, expected, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    cleaned = expected if presentation == "plain" else json.dumps(expected) + "\n"
    assert redact(text) == cleaned


# Round 33: shift assignments and raw-sensitive owner spellings.
ROUND33_SHIFT_EXACT_WITNESSES = (
    'Note that secret\u0301 >>= "SYNTHETIC_R32_CORRECTNESS_SENTINEL"',
    'Note that secret\u0301 <<= "SYNTHETIC_R32_CORRECTNESS_SENTINEL"',
    'Ordinary prose, (secret) >>= "SYNTHETIC_R32_CORRECTNESS_SENTINEL"',
    'Ordinary prose, (secret) <<= "SYNTHETIC_R32_CORRECTNESS_SENTINEL"',
    'Ordinary prose, (api_key) >>= "SYNTHETIC_R32_CORRECTNESS_SENTINEL"',
    "It's (password) <<= \"SYNTHETIC_R32_CORRECTNESS_SENTINEL\" and don't",
    "It's secret\u0301 >>= \"SYNTHETIC_R32_CORRECTNESS_SENTINEL\" and don't",
    'Ordinary "prose" (authorization) >>= "SYNTHETIC_R32_CORRECTNESS_SENTINEL"',
)
ROUND33_GROK_EXACT_WITNESSES = (
    'Ordinary prose, (secret\u200c) >>= "SYNTHETIC_R32_GROK_SENTINEL"',
    'Note that secret\u200d >>= "SYNTHETIC_R32_GROK_SENTINEL"',
)
ROUND33_RAW_EXACT_WITNESSES = tuple(
    template.format(name="secret" + suffix, marker="SYNTHETIC_R32_ASTRA_MARKER")
    for suffix in ("\u0327", "\u0307")
    for template in (
        'Note that {name} = "{marker}"',
        'Note that {name} += "{marker}"',
        'Note that ({name}) = "{marker}"',
        "It's {name} = \"{marker}\" and don't",
    )
)

# This is the Python operator grammar, listed independently of the local guard.
ROUND33_PYTHON_AUGMENTED = (
    "+=",
    "-=",
    "*=",
    "/=",
    "//=",
    "%=",
    "**=",
    "@=",
    "&=",
    "|=",
    "^=",
    "<<=",
    ">>=",
)
ROUND33_RAW_OWNER_TARGETS = (
    "secret\u0327",
    "secret\u0307",
    "cfg.secret\u0327",
    "cfg.secret\u0307",
    "api_key\u0307",
    "access_token\u0327",
    "cfg.api_key\u0307",
    'secret\u0327["public"]',
    "(secret\u0327, other)",
    "[secret\u0307, other]",
    "[other, *secret\u0327]",
    "secret\u0327 \\\n",
    "secret\u0307 \\\r",
    "secret\u0327 \\\r\n",
)
ROUND33_VALID_TARGET_OPERATOR_PAIRS = tuple(
    (target, operator)
    for target in ROUND33_RAW_OWNER_TARGETS
    for operator in ("=", "+=", ": str =")
    if _round32_valid_target_operator(target, " " + operator + " ")
)


@pytest.mark.parametrize(
    "source",
    ROUND33_SHIFT_EXACT_WITNESSES + ROUND33_GROK_EXACT_WITNESSES + ROUND33_RAW_EXACT_WITNESSES,
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round33_exact_assignment_witnesses_never_return_marker(source, presentation):
    from jevdrill.context import redact

    marker = "SYNTHETIC_R32_"
    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert marker not in cleaned


@pytest.mark.parametrize("operator", ROUND33_PYTHON_AUGMENTED)
@pytest.mark.parametrize("target", ("(secret)", "secret\u0327", "cfg.secret\u0307"))
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round33_complete_python_augmented_operator_family(operator, target, presentation):
    import ast

    from jevdrill.context import redact

    statement = f'{target} {operator} "SYNTHETIC_R33_SENTINEL"'
    assert isinstance(ast.parse(statement).body[0], ast.AugAssign)
    source = "Ordinary prose, " + statement
    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert "SYNTHETIC_R33_SENTINEL" not in cleaned


@pytest.mark.parametrize("target,operator", ROUND33_VALID_TARGET_OPERATOR_PAIRS)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round33_raw_sensitive_actual_owner_grammar(target, operator, presentation):
    import ast

    from jevdrill.context import redact

    statement = f'{target} {operator} "SYNTHETIC_R33_SENTINEL"'
    assert isinstance(ast.parse(statement), ast.Module)
    source = "Note that " + statement
    text = source if presentation == "plain" else json.dumps(source)
    try:
        cleaned = redact(text)
    except ContractError:
        return
    assert "SYNTHETIC_R33_SENTINEL" not in cleaned


@pytest.mark.parametrize(
    "name",
    ("secret\u0327", "secret\u0307", "api_key\u0307", "access_token\u0327"),
)
def test_round33_raw_sensitive_name_is_runtime_valid_but_normalized_label_is_not(name):
    import ast
    import unicodedata

    from jevdrill.context import _credential_label

    assert name.isidentifier()
    assert isinstance(ast.parse(name + " = 1").body[0], ast.Assign)
    assert _credential_label(name)
    assert not _credential_label(unicodedata.normalize("NFKC", name))


@pytest.mark.parametrize(
    "source",
    (
        'Note that (secret\u0327 := "SYNTHETIC_R33_SENTINEL")',
        'Note that cfg[secret\u0327] = "application/json"',
        'Note that cfg.public["secret\u0327"] = "application/json"',
        'Note that public: secret\u0327 = "application/json"',
        'Note that content_type\u0327 >>= "application/json"',
        'Ordinary prose, (content_type) <<= "application/json"',
        'Ordinary prose, (secret) >= "SYNTHETIC_R33_SENTINEL"',
        'Ordinary prose, (secret) <= "SYNTHETIC_R33_SENTINEL"',
        'Ordinary prose, (secret) == "SYNTHETIC_R33_SENTINEL"',
        "The secret (to success) is patience.",
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round33_owner_and_comparison_controls_match_established_path(source, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    if "secret\u0327 :=" in source:
        with pytest.raises(ContractError):
            redact(text)
    elif 'cfg.public["secret\u0327"]' in source:
        with pytest.raises(ContractError, match="unsupported credential assignment"):
            redact(text)
    elif "public: secret\u0327" in source:
        expected = "Note that public: '[redacted]'\n"
        assert redact(text) == (
            expected if presentation == "plain" else json.dumps(expected) + "\n"
        )
    else:
        assert redact(text) == text


@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round33_complete_redaction_and_ordinary_next_line(presentation):
    from jevdrill.context import redact

    source = 'secret = "SYNTHETIC_R33_SENTINEL"\nOrdinary next line.'
    text = source if presentation == "plain" else json.dumps(source)
    cleaned = redact(text)
    assert "SYNTHETIC_R33_SENTINEL" not in cleaned
    assert "Ordinary next line." in cleaned
    metadata = "alpha objective-private-sentinel api_key=credential-sentinel"
    presented = metadata if presentation == "plain" else json.dumps(metadata)
    expected = "alpha objective-private-sentinel [redacted]"
    assert redact(presented) == (
        expected if presentation == "plain" else json.dumps(expected) + "\n"
    )


@pytest.mark.parametrize(
    "source",
    (
        '(secret) >>= "SYNTHETIC_R33_SENTINEL"',
        '(secret) <<= "SYNTHETIC_R33_SENTINEL"',
        'secret\u200c >>= "SYNTHETIC_R33_SENTINEL"',
    ),
)
@pytest.mark.parametrize("presentation", ("plain", "json"))
def test_round33_standalone_shift_controls_keep_complete_redaction(source, presentation):
    from jevdrill.context import redact

    text = source if presentation == "plain" else json.dumps(source)
    assert redact(text) == ("[redacted]" if presentation == "plain" else '"[redacted]"\n')


@pytest.mark.parametrize("character", ("\u200c", "\u200d"))
def test_round33_grok_identifier_continuations_follow_runtime(character):
    import ast

    name = "secret" + character
    assert name.isidentifier()
    assert isinstance(ast.parse(name + " >>= 1").body[0], ast.AugAssign)


def test_round33_known_ordinary_question_rejection_is_unchanged():
    from jevdrill.context import redact

    with pytest.raises(ContractError, match="unsupported computed explicit key"):
        redact("Why? Here is context: visible")
