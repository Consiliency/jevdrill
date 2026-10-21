"""Supplied context only; never follow attachment references or search user files."""

import ast
import fnmatch
import json
import os
import posixpath
import re
import sys
import tokenize
import unicodedata
import uuid
import warnings
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from time import monotonic
from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.tokens import (
    AliasToken,
    AnchorToken,
    BlockEndToken,
    BlockMappingStartToken,
    BlockSequenceStartToken,
    FlowMappingEndToken,
    FlowMappingStartToken,
    FlowSequenceEndToken,
    FlowSequenceStartToken,
    ScalarToken,
    TagToken,
)

from .contracts import ContractError

EXCLUDED_COMPONENTS = frozenset({".env", ".ssh", ".gnupg", "credentials", "id_rsa", "id_ed25519"})
CREDENTIAL_LABEL = r"authorization|api[\s_-]*key|access[\s_-]*token|password|secret"
LINE_BREAK = r"(?:\r\n|[\r\n\x85\u2028\u2029])"
LINE_START = r"(?<![^\r\n\x85\u2028\u2029])"
INDENT = r"[^\S\r\n\x85\u2028\u2029]"
LINE_TEXT = r"[^\r\n\x85\u2028\u2029]"
CONTINUATION = rf"{LINE_BREAK}{INDENT}+{LINE_TEXT}*"
STRUCTURED_CONTINUATION = rf"{LINE_BREAK}(?:{INDENT}+{LINE_TEXT}*|{INDENT}*\#{LINE_TEXT}*)"
PRIVATE_KEY_BEGIN = re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----", re.IGNORECASE)
PRIVATE_KEY_END = re.compile(r"-----END [^-]*PRIVATE KEY-----", re.IGNORECASE)
QUOTED_SCALAR = re.compile(r"""(?:'(?:[^']|'')*'|"(?:[^"\\]|\\[\s\S])*")""")
PYTHON_QUOTED_SCALAR = re.compile(r"""(?:'(?:[^'\\]|\\[\s\S])*'|"(?:[^"\\]|\\[\s\S])*")""")
ESCAPED_LABEL_COLON = re.compile(rf"(?:{INDENT}|{LINE_BREAK}|\#{LINE_TEXT}*{LINE_BREAK})*:")
ESCAPED_LABEL_ASSIGNMENT = re.compile(
    r"[^\S\r\n\x85\u2028\u2029]*\][^\S\r\n\x85\u2028\u2029]*(?:\+|\-|\*|/|%|&|\||\^|<<|>>|//|\*\*)?="
)
CREDENTIAL = re.compile(
    rf"""(?i)(?<![\w.-])(?:[\w.]+\s*+\[\s*+)?(?:["'][^\S\r\n]*+)?[\w.-]*(?:{CREDENTIAL_LABEL})"""
    r"""[\w.-]*[^\S\r\n]*+["']?\s*+\]?\s*+(?::|(?:\*\*|//|<<|>>|[+\-*/%@&|^])?=)"""
    rf"{LINE_TEXT}*"
    rf"(?:{CONTINUATION})*"
    + rf"""|(?<![^\r\n\x85\u2028\u2029"']){INDENT}*(?:bearer|basic)\s+[^\s"',;}}\]]+"""
    + rf"""[^\r\n\x85\u2028\u2029"',;}}\]]*(?:{CONTINUATION})*"""
)
TARGET_AUGMENTED = re.compile(r"(?:\*\*|//|<<|>>|[+\-*/%@&|^])=")
TARGET_COMPARISON_WORD = re.compile(r"(?:is|in|not\s+in)\b")
CONTEXT_PART = re.compile(
    "(?P<credential>" + CREDENTIAL.pattern.removeprefix("(?i)") + r")|[\[{\"]",
    re.IGNORECASE,
)


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None and monotonic() >= deadline:
        raise TimeoutError("context sanitization deadline exceeded")


def _validation_view(text: str, deadline: float | None) -> str:
    _check_deadline(deadline)
    text = re.sub(LINE_BREAK, "\n", text)
    text = re.sub(INDENT, " ", text)
    _check_deadline(deadline)
    return text


class _DeadlineLoader(yaml.SafeLoader):
    def __init__(self, stream: str, deadline: float | None):
        super().__init__(stream)
        self.deadline = deadline

    def compose_node(self, parent: Node | None, index: Any) -> Node | None:
        _check_deadline(self.deadline)
        return super().compose_node(parent, index)


def _literal_string(node: ast.AST, deadline: float | None) -> str | None:
    pending = [node]
    parts = []
    kind = None
    while pending:
        _check_deadline(deadline)
        item = pending.pop()
        if isinstance(item, ast.Constant) and isinstance(item.value, (str, bytes)):
            if kind is not None and type(item.value) is not kind:
                return None
            kind = type(item.value)
            parts.append(
                item.value.decode("latin1") if isinstance(item.value, bytes) else item.value
            )
        elif isinstance(item, ast.JoinedStr):
            pending.extend(reversed(item.values))
        elif isinstance(item, ast.BinOp) and isinstance(item.op, ast.Add):
            pending.extend((item.right, item.left))
        elif (
            isinstance(item, ast.Call)
            and isinstance(item.func, ast.Name)
            and item.func.id == "str"
            and len(item.args) == 1
            and not item.keywords
            and isinstance(item.args[0], ast.Constant)
            and isinstance(item.args[0].value, str)
        ):
            if kind is not None and kind is not str:
                return None
            kind = str
            parts.append(item.args[0].value)
        else:
            return None
    return "".join(parts)


def _redact_private_keys(text: str, deadline: float | None) -> str:
    chunks: list[str] = []
    end = 0
    for begin in PRIVATE_KEY_BEGIN.finditer(text):
        _check_deadline(deadline)
        if begin.start() < end:
            continue
        closing = PRIVATE_KEY_END.search(text, begin.end())
        if closing is None:
            raise ContractError("incomplete private-key block")
        chunks.extend((text[end : begin.start()], "[redacted]"))
        end = closing.end()
    return "".join(chunks) + text[end:]


def _credential_label(value: str, deadline: float | None = None) -> bool:
    while re.match(r"(?:\(\s*)*[rRuUbBfF]{0,2}[\"']", value.strip()):
        _check_deadline(deadline)
        try:
            try:
                decoded = json.loads(value)
            except ValueError:
                with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                    decoded = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            try:
                decoded = _literal_string(ast.parse(value.strip(), mode="eval").body, deadline)
            except (ValueError, SyntaxError):
                break
            if decoded is None:
                raise ContractError("unsupported computed string literal")
        if isinstance(decoded, bytes):
            decoded = decoded.decode("latin1")
        if not isinstance(decoded, str) or decoded == value:
            break
        value = decoded
    return re.search(CREDENTIAL_LABEL, value.strip(), re.IGNORECASE) is not None


def _check_escaped_record_labels(text: str, deadline: float | None) -> None:
    """Inspect quoted labels from their own opening, ignoring prose quote state."""
    work = 0
    for opening in re.finditer(r"['\"]", text):
        _check_deadline(deadline)
        candidates = [
            match
            for pattern in (QUOTED_SCALAR, PYTHON_QUOTED_SCALAR)
            if (match := pattern.match(text, opening.start())) is not None
        ]
        quoted = max(candidates, key=lambda match: match.end(), default=None)
        # A failed match may have scanned the whole remaining input before it
        # discovers an unterminated quote. Charge that scan, too.
        work += (quoted.end() if quoted is not None else len(text)) - opening.start()
        if work > 16 * len(text) + 100_000:
            raise ContractError("context fragment work exceeds sanitization limit")
        if quoted is None or "\\" not in quoted.group():
            continue
        # A mapping/explicit key ends at a colon. A subscript target ends at
        # its bracket and assignment operator. Neither depends on the prose
        # preceding this local literal.
        colon = ESCAPED_LABEL_COLON.match(text, quoted.end())
        assignment = ESCAPED_LABEL_ASSIGNMENT.match(text, quoted.end())
        if colon is None and assignment is None:
            continue
        readings = []
        try:
            with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                readings.append(ast.literal_eval(quoted.group()))
        except (SyntaxError, ValueError):
            pass
        try:
            readings.append(yaml.safe_load(quoted.group()))
        except yaml.YAMLError:
            pass
        if any(
            isinstance(literal, (str, bytes))
            and _credential_label(
                literal.decode("latin1") if isinstance(literal, bytes) else literal,
                deadline,
            )
            for literal in readings
        ):
            if (
                assignment is not None
                and colon is None
                and _supported_escaped_assignment(text, opening.start(), deadline)
            ):
                continue
            raise ContractError("unsupported escaped literal credential")


def _supported_escaped_assignment(text: str, label_start: int, deadline: float | None) -> bool:
    """Defer only a whole, valid assignment the existing sanitizer removes."""
    line_start = text.rfind("\n", 0, label_start) + 1
    line_end = text.find("\n", label_start)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end]
    _check_deadline(deadline)
    try:
        with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
            parsed = ast.parse(line)
    except (SyntaxError, ValueError):
        return False
    if len(parsed.body) != 1 or not isinstance(
        parsed.body[0], (ast.Assign, ast.AnnAssign, ast.AugAssign)
    ):
        return False
    try:
        return _redact_assignments(line, deadline) == "[redacted]"
    except ContractError:
        return False


def _complete_public_explicit_key(text: str, deadline: float | None) -> bool:
    """Validate one complete public explicit-key document in a decoded scalar."""
    view = _validation_view(text, deadline)
    match = re.fullmatch(
        r"(?P<prose>[^\n]*)\n\?[ \t]*(?P<key>'(?:[^']|'')*'|\"(?:[^\"\\]|\\[\s\S])*\")[ \t]*\n:[ \t]*(?P<value>[^\n]+)",
        view,
    )
    if match is None:
        return False
    prose = match.group("prose")
    # The prose is outside the record. Do not allow it to carry another
    # assignment, bracketed record, explicit key, or Markdown presentation.
    if not prose or any(char in prose for char in "?:={}[]`"):
        return False
    if redact(prose, deadline) != prose:
        return False
    try:
        loader = _DeadlineLoader(
            "? " + match.group("key") + "\n: " + match.group("value"), deadline
        )
        try:
            node = loader.get_single_node()
        finally:
            loader.dispose()
    except yaml.YAMLError:
        return False
    if not isinstance(node, MappingNode) or len(node.value) != 1:
        return False
    key_node, value_node = node.value[0]
    if not isinstance(key_node, ScalarNode) or not isinstance(value_node, ScalarNode):
        return False
    if key_node.style not in {"'", '"'} or value_node.style is not None:
        return False
    key = key_node.value
    if _credential_label(key, deadline):
        return False
    try:
        with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
            alternate = _literal_string(ast.parse(match.group("key"), mode="eval").body, deadline)
    except (SyntaxError, ValueError):
        alternate = None
    if alternate is not None and _credential_label(alternate, deadline):
        return False
    # A key that spells an expression must have a fully resolved static
    # reading. Unknown calls and unfinished compositions cannot qualify.
    if any(char in key for char in "()+\"'"):
        try:
            with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                composed = _literal_string(ast.parse("(" + key + "\n)", mode="eval").body, deadline)
        except (SyntaxError, ValueError):
            return False
        if composed is None or _credential_label(composed, deadline):
            return False
    # Require the scalar to be a single public value. A second record cannot
    # be swallowed as part of an accepted first record.
    value = value_node.value
    if not value or value != match.group("value"):
        return False
    if (
        CREDENTIAL.search(value) is not None
        or redact(value, deadline) != value
        or _redact_assignments(value, deadline, record_member=True) != value
    ):
        raise ContractError("unsupported credential explicit value")
    return True


def _redact_node(node: Node, seen: set[int], deadline: float | None) -> bool:
    _check_deadline(deadline)
    if id(node) in seen:
        return False
    seen.add(id(node))
    changed = False
    if isinstance(node, MappingNode):
        if any(not isinstance(key, ScalarNode) for key, _ in node.value):
            raise ContractError("unsupported structured mapping key")
        sensitive = any(
            isinstance(item, ScalarNode) and _credential_label(item.value, deadline)
            for pair in node.value
            for item in pair
        )
        for index, (key, value) in enumerate(node.value):
            _check_deadline(deadline)
            if isinstance(key, ScalarNode) and _credential_label(key.value, deadline):
                key.value = "[redacted]"
                changed = True
            else:
                changed = _redact_node(key, seen, deadline) or changed
            if sensitive:
                node.value[index] = (key, ScalarNode("tag:yaml.org,2002:str", "[redacted]"))
                changed = True
            else:
                changed = _redact_node(value, seen, deadline) or changed
    elif isinstance(node, SequenceNode):
        if any(
            isinstance(item, ScalarNode) and _credential_label(item.value, deadline)
            for item in node.value
        ):
            node.value = [ScalarNode("tag:yaml.org,2002:str", "[redacted]") for _ in node.value]
            return True
        for item in node.value:
            changed = _redact_node(item, seen, deadline) or changed
    elif isinstance(node, ScalarNode):
        if _complete_public_explicit_key(node.value, deadline):
            return False
        if re.search(LINE_BREAK, node.value) is not None and node.style is None:
            _redact_assignments(
                "(" + _validation_view(node.value, deadline) + "\n)",
                deadline,
                record_member=True,
            )
        if (
            not _credential_label(node.value, deadline)
            and _redact_assignments(node.value, deadline, record_member=True) != node.value
        ):
            raise ContractError("unsupported embedded credential assignment")
        if re.match(r"\s*str\s*\(", node.value) and "#" not in node.value:
            try:
                literal = _literal_string(
                    ast.parse(
                        "(" + _validation_view(node.value, deadline) + "\n)", mode="eval"
                    ).body,
                    deadline,
                )
            except (SyntaxError, ValueError):
                literal = None
            if literal is not None:
                if _credential_label(literal, deadline) or redact(literal, deadline) != literal:
                    raise ContractError("unsupported computed credential record")
                return False
        cleaned = redact(node.value, deadline)
        changed = cleaned != node.value
        node.value = cleaned
    return changed


def _structured(text: str, deadline: float | None) -> str | None:
    spans = []
    depth = 0
    nodes = 0
    credential_block = False
    credential_sequence = False
    sequence_count = 0
    quoted_work = 0
    decoded_spans: list[tuple[int, int]] = []
    public_spans: set[tuple[int, int]] = set()
    decoded_end = 0
    escaped_quotes: set[int] = set()
    for opening in re.finditer(r"""['"]""", text):
        _check_deadline(deadline)
        if opening.start() in escaped_quotes or opening.start() < decoded_end:
            continue
        quoted = QUOTED_SCALAR.match(text, opening.start())
        complete_public = False
        quoted_work += (quoted.end() if quoted is not None else len(text)) - opening.start()
        if quoted_work > 16 * len(text) + 100_000:
            raise ContractError("context fragment work exceeds sanitization limit")
        if quoted is not None and quoted.group().startswith('"'):
            try:
                decoded = json.loads(quoted.group())
            except ValueError:
                pass
            else:
                # Validate the complete decoded record before YAML can split its
                # original spelling across a key and its sibling value.
                cleaned = redact(decoded, deadline)
                if cleaned != decoded:
                    decoded_spans.append((opening.start(), quoted.end()))
                    decoded_end = quoted.end()
                else:
                    complete_public = _complete_public_explicit_key(decoded, deadline)
                    if complete_public:
                        try:
                            loader = _DeadlineLoader(quoted.group(), deadline)
                            try:
                                yaml_reading = loader.get_single_data()
                            finally:
                                loader.dispose()
                            with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                                python_reading = ast.literal_eval(quoted.group())
                        except (yaml.YAMLError, SyntaxError, ValueError):
                            complete_public = False
                        else:
                            complete_public = yaml_reading == decoded == python_reading
                    if complete_public:
                        decoded_end = quoted.end()
                        public_spans.add((opening.start(), quoted.end()))
        if (
            quoted is not None
            and (re.search(LINE_BREAK, quoted.group()) is not None or "''" in quoted.group()[1:-1])
            and not complete_public
        ):
            _redact_assignments(quoted.group(), deadline, record_member=True)
            if quoted.group().startswith("'"):
                for escaped in re.compile("''").finditer(
                    text, opening.start() + 1, quoted.end() - 1
                ):
                    _check_deadline(deadline)
                    escaped_quotes.update((escaped.start(), escaped.start() + 1))
    # Retain original labels until the enclosing node decides sibling sensitivity.
    # Unstructured prose is handled by redact's complete JSON-fragment decoder.
    for sequence in re.finditer(
        rf"{LINE_START}{INDENT}*-(?:{INDENT}+{LINE_TEXT}*|(?={LINE_BREAK}|$))"
        rf"(?:{STRUCTURED_CONTINUATION})*",
        text,
    ):
        _check_deadline(deadline)
        sequence_text = sequence.group()
        sequence_member = re.sub(rf"^{INDENT}*-{INDENT}*", "", sequence_text)
        _redact_assignments(
            "(" + _validation_view(sequence_member, deadline) + "\n)", deadline, record_member=True
        )
        credential_sequence = (
            credential_sequence
            or _credential_label(sequence_text, deadline)
            or _redact_assignments(sequence_text, deadline) != sequence_text
        )
        try:
            sequence_view = _validation_view(sequence_text, deadline)
            for token in yaml.scan(sequence_view):
                _check_deadline(deadline)
                if isinstance(token, ScalarToken):
                    sequence_count += 1
                    if sequence_count > 10_000:
                        raise ContractError("context structure exceeds sanitization limit")
                    source = sequence_view[token.start_mark.index : token.end_mark.index]
                    if token.style in {"'", '"'}:
                        _redact_assignments(source, deadline, record_member=True)
                    credential_sequence = (
                        credential_sequence
                        or _credential_label(token.value, deadline)
                        or _redact_assignments(token.value, deadline, record_member=True)
                        != token.value
                    )
        except yaml.YAMLError:
            pass
    try:
        for token in yaml.scan(text):
            _check_deadline(deadline)
            if isinstance(
                token,
                (
                    ScalarToken,
                    BlockMappingStartToken,
                    BlockSequenceStartToken,
                    FlowMappingStartToken,
                    FlowSequenceStartToken,
                ),
            ):
                nodes += 1
                if nodes > 10_000:
                    raise ContractError("context structure exceeds sanitization limit")
            if isinstance(token, (AliasToken, AnchorToken, TagToken)):
                raise ContractError("unsupported YAML graph or tag")
            if isinstance(token, ScalarToken):
                if token.style in {"|", ">"} and _credential_label(token.value, deadline):
                    credential_block = True
                if token.value == "<<":
                    raise ContractError("unsupported YAML merge")
                source = text[token.start_mark.index : token.end_mark.index]
                if (
                    token.style in {"'", '"'}
                    and (token.start_mark.index, token.end_mark.index) not in public_spans
                ):
                    _redact_assignments(source, deadline, record_member=True)
                if "\\" in token.value and re.match(r"[rRuUbB]*[\"']", source):
                    try:
                        with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                            literal = ast.literal_eval(source)
                    except (SyntaxError, ValueError):
                        literal = None
                    if (
                        isinstance(literal, (str, bytes))
                        and _credential_label(str(literal), deadline)
                        and not _credential_label(token.value, deadline)
                    ):
                        raise ContractError("unsupported escaped literal credential")
                spans.append((token.start_mark.index, token.end_mark.index))
            if isinstance(
                token,
                (
                    BlockMappingStartToken,
                    BlockSequenceStartToken,
                    FlowMappingStartToken,
                    FlowSequenceStartToken,
                ),
            ):
                depth += 1
                if depth >= sys.getrecursionlimit():
                    raise ContractError("context nesting exceeds sanitization limit")
            elif isinstance(token, (BlockEndToken, FlowMappingEndToken, FlowSequenceEndToken)):
                depth -= 1
        loader = _DeadlineLoader(text, deadline)
        try:
            node = loader.get_single_node()
        finally:
            loader.dispose()
    except yaml.YAMLError:
        for member in re.finditer(
            rf"[:?]\s*(?:\#{LINE_TEXT}*{LINE_BREAK}\s*)*"
            rf"(?P<quote>['\"])(?P<value>{LINE_TEXT}*"
            rf"(?:{STRUCTURED_CONTINUATION})*)",
            text,
        ):
            _check_deadline(deadline)
            quoted = QUOTED_SCALAR.match(text, member.start("quote"))
            if quoted is not None and re.compile(rf"{INDENT}*(?:[,}}\];#]|{LINE_BREAK}|$)").match(
                text, quoted.end()
            ):
                _redact_assignments(
                    quoted.group()
                    if re.search(LINE_BREAK, quoted.group()) is not None
                    or quoted.group().startswith("'")
                    and "''" in quoted.group()[1:-1]
                    else "(" + _validation_view(quoted.group()[1:-1], deadline) + "\n)",
                    deadline,
                    record_member=True,
                )
                continue
            original = _validation_view(member.group("value"), deadline)
            _redact_assignments(original, deadline, record_member=True)
            if quoted is None:
                quote = member.group("quote")
                _redact_assignments(quote + original + "\n" + quote, deadline, record_member=True)
        for member in re.finditer(
            rf"{LINE_START}(?:(?P<explicit>{INDENT}*\?{INDENT}*)|"
            rf"[^\r\n\x85\u2028\u2029:=]+:{INDENT}*)"
            rf"(?P<value>{LINE_TEXT}*(?:{STRUCTURED_CONTINUATION})*)",
            text,
        ):
            _check_deadline(deadline)
            original = _validation_view(member.group("value"), deadline)
            # Keep a same-line key/value separator visible to the scalar-span
            # validation before enclosing a multiline member.
            if member.group("explicit") is not None:
                _redact_assignments(original, deadline, record_member=True)
            _redact_assignments(
                original.strip()
                if QUOTED_SCALAR.fullmatch(original.strip()) is not None
                else "(" + original + "\n)",
                deadline,
                record_member=True,
            )
        if credential_sequence:
            raise ContractError("unsupported structured credential sequence") from None
        for block in re.finditer(r"[:=][^\S\r\n]*[|>][^\r\n]*" + rf"(?:{CONTINUATION})+", text):
            _check_deadline(deadline)
            credential_block = (
                credential_block
                or _credential_label(block.group(), deadline)
                or _redact_assignments(block.group(), deadline) != block.group()
            )
        if credential_block:
            raise ContractError("unsupported structured credential block") from None
        if re.search(rf"{LINE_START}{INDENT}*\?{INDENT}*[\[{{]", text):
            raise ContractError("unsupported structured mapping key") from None
        if re.search(r"(?:^|[\s:\[,])(?:[&*][\w-]+|![!\w])", text):
            raise ContractError("unsupported YAML graph or tag")
        return None
    _check_deadline(deadline)
    span_index = 0
    comments = False
    for marker in re.finditer("#", text):
        _check_deadline(deadline)
        while span_index < len(spans) and spans[span_index][1] <= marker.start():
            span_index += 1
        if span_index == len(spans) or marker.start() < spans[span_index][0]:
            comments = True
            break
    if isinstance(node, (MappingNode, SequenceNode)) or (
        isinstance(node, ScalarNode) and node.style in ("'", '"')
    ):
        scalar_spans = set(spans)
        if any(span not in scalar_spans for span in decoded_spans):
            raise ContractError("unsupported split decoded credential record")
        _redact_assignments(text, deadline, structured_source=True)
        changed = _redact_node(node, set(), deadline)
        if decoded_spans and not changed:
            raise ContractError("unsupported decoded credential record")
        result = yaml.serialize(node) if changed or comments else text
        _check_deadline(deadline)
        return result
    if credential_sequence:
        raise ContractError("unsupported structured credential sequence")
    if comments:
        _redact_assignments(text, deadline)
        return redact(node.value, deadline) if isinstance(node, ScalarNode) else ""
    return None


def _validate_explicit_keys(text: str, deadline: float | None) -> None:
    """Inspect original explicit keys independently of prose and flow placement."""
    view = _validation_view(text, deadline)
    if view[:1] in {'"', "{", "["}:
        try:
            decoded = json.loads(view, object_pairs_hook=tuple)
        except ValueError:
            pass
        else:
            pending = [decoded]
            while pending:
                _check_deadline(deadline)
                item = pending.pop()
                if isinstance(item, str):
                    if item != view:
                        _validate_explicit_keys(item, deadline)
                elif isinstance(item, (list, tuple)):
                    pending.extend(item)
            return
    # A log prefix may be followed by one complete JSON value. Establish its
    # boundary by parsing the entire suffix, then inspect the decoded content.
    # A quote in prose cannot qualify if later key fragments remain outside it.
    first_quote = view.find('"')
    if first_quote >= 0 and "?" not in view[:first_quote]:
        try:
            decoded_suffix = json.loads(view[first_quote:])
        except ValueError:
            pass
        else:
            if isinstance(decoded_suffix, str):
                _validate_explicit_keys(decoded_suffix, deadline)
                return
    # Inspect each indicator in the original view first. A quoted span found
    # by a regex may start in prose and end at a later key fragment, so it
    # cannot establish that the indicator belongs only to a JSON string.
    scan_work = 0
    for marker in re.finditer(r"\?", view):
        _check_deadline(deadline)
        # Start at the indicator itself. A quote or apostrophe in surrounding
        # prose is not allowed to establish the key's lexical state.
        cursor = marker.end()
        brackets: list[str] = []
        quote = ""
        comment = False
        colon = None
        while cursor < len(view):
            _check_deadline(deadline)
            scan_work += 1
            if scan_work > 16 * len(view) + 100_000:
                raise ContractError("context fragment work exceeds sanitization limit")
            char = view[cursor]
            if comment:
                if char == "\n":
                    comment = False
            elif quote:
                if char == "\\":
                    cursor += 2
                    continue
                if view.startswith(quote, cursor):
                    cursor += len(quote)
                    quote = ""
                    continue
            elif char in "\"'":
                quote = char * 3 if view.startswith(char * 3, cursor) else char
                cursor += len(quote)
                continue
            elif char == "#":
                comment = True
            elif char in "([{":
                brackets.append(char)
            elif char in ")]}":
                if not brackets:
                    break
                brackets.pop()
            elif char == ":" and not brackets:
                colon = cursor
                break
            elif char in ",?" and not brackets:
                break
            cursor += 1
        if colon is None:
            continue
        expression = view[marker.end() : colon].strip()
        significant: list[tuple[int, str]] = []
        malformed = False
        try:
            for token in tokenize.generate_tokens(StringIO(expression).readline):
                _check_deadline(deadline)
                if token.type not in {tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER}:
                    significant.append((token.type, token.string))
        except (tokenize.TokenError, IndentationError):
            malformed = True
        strings = sum(kind in {tokenize.STRING, tokenize.FSTRING_START} for kind, _ in significant)
        call = any(
            kind == tokenize.NAME and significant[index + 1][1] == "("
            for index, (kind, _) in enumerate(significant[:-1])
        )
        computed = (
            call
            or strings > 1
            or any(
                kind == tokenize.STRING and value.startswith(("'''", '"""'))
                for kind, value in significant
            )
            or any(kind == tokenize.FSTRING_START for kind, _ in significant)
            or any(value == "+" for _, value in significant)
            or (
                malformed
                and (
                    "(" in expression or "+" in expression or "'" in expression or '"' in expression
                )
            )
        )
        numeric_public = (
            re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", expression) is not None
        )
        if numeric_public:
            computed = False
        # Token spellings alone cannot enumerate computed keys: multiplication,
        # shifts, boolean composition and later Python operators all have the
        # same unresolved-record semantics. Classify the complete key AST.
        # Bare hyphenated/dotted labels and MIME spellings remain public text.
        public_spelling = re.sub(r"(?m)^[ \t]*\#[^\n]*(?:\n|$)", "", expression).strip()
        static_public = re.fullmatch(r"[\w.][\w.-]*(?:/[\w.][\w.-]*)*", public_spelling) is not None
        try:
            with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                key_node = ast.parse("(" + expression + "\n)", mode="eval").body
        except (SyntaxError, ValueError):
            key_node = None
        if (
            key_node is not None
            and not (static_public or numeric_public)
            and isinstance(
                key_node,
                (ast.BinOp, ast.BoolOp, ast.IfExp, ast.UnaryOp, ast.NamedExpr, ast.Subscript),
            )
        ):
            computed = True
        if static_public or numeric_public:
            continue
        # Keep the established operator/token decision ahead of ordinary
        # punctuation handling. In particular, a prose-adjacent ? must not
        # hide multiplication, matrix multiplication, or another old reject.
        if not computed and marker.start() and view[marker.start() - 1].isalnum():
            before = view[: marker.start()]
            # Assignment/reference scans also pass a URL suffix beginning
            # with //, so recognize that same absolute-URL path here.
            url = re.search(r"(?:https?:)?//[^\s?#]+$", before)
            if url is not None and re.fullmatch(r"[\w.-]+=(?:https?|[\w.-]+)", expression):
                continue
        if QUOTED_SCALAR.fullmatch(expression) is not None:
            # YAML doubles single quotes, while Python reads adjacent quoted
            # fragments as one literal. Both readings must be safe before a
            # surrounding prose quote can hide this member from later scans.
            decoded = (
                expression[1:-1].replace("''", "'")
                if expression.startswith("'")
                else yaml.safe_load(expression)
            )
            try:
                with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                    literal = _literal_string(ast.parse(expression, mode="eval").body, deadline)
            except (SyntaxError, ValueError):
                literal = None
            for value in (decoded, literal):
                if not isinstance(value, str):
                    continue
                if _credential_label(value, deadline):
                    raise ContractError("unsupported computed explicit key")
                # A decoded YAML key can itself spell a multiline, constant
                # composition. Inspect its static result before recursively
                # treating the source spelling as an unresolved record.
                composed = None
                if "#" not in value:
                    try:
                        with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                            node = ast.parse("(" + value + "\n)", mode="eval").body
                        composed = _literal_string(node, deadline)
                    except (SyntaxError, ValueError):
                        pass
                checked = composed if composed is not None else value
                if _credential_label(checked, deadline) or redact(checked, deadline) != checked:
                    raise ContractError("unsupported computed explicit key")
            continue
        # Word-only public YAML labels that are not Python expressions remain
        # plain text. A parsed comparison (is, in, is not, not in) is always
        # unresolved, including when its spelling also reads as prose.
        if key_node is None and not computed and re.fullmatch(r"\w+(?:[ \t]+\w+)+", expression):
            continue
        literal = _literal_string(key_node, deadline) if key_node is not None else None
        if (
            literal is None
            or _credential_label(literal, deadline)
            or redact(literal, deadline) != literal
        ):
            raise ContractError("unsupported computed explicit key")
    # A JSON string embedded in a log line may encode another explicit key.
    # Decode it only after every original candidate has been checked.
    for quoted in re.finditer(r'"(?:[^"\\]|\\.)*"', view):
        _check_deadline(deadline)
        try:
            decoded = json.loads(quoted.group())
        except ValueError:
            continue
        if "?" in decoded and decoded != quoted.group():
            _validate_explicit_keys(decoded, deadline)


def _redact_assignments(
    text: str,
    deadline: float | None,
    *,
    record_member: bool = False,
    structured_source: bool = False,
) -> str:
    _check_deadline(deadline)
    if "?" in text:
        _validate_explicit_keys(text, deadline)
    for member in re.finditer(r"`+([^`]+)", text):
        original = _validation_view(member.group(1), deadline)
        if _complete_public_explicit_key(member.group(1), deadline) and redact(
            member.group(1), deadline
        ) == member.group(1):
            continue
        enclosed = "(" + original + "\n)"
        if (
            _redact_assignments(enclosed, deadline, record_member=True) != enclosed
            or redact(original, deadline) != original
        ):
            raise ContractError("unsupported Markdown credential record")
    if (
        record_member
        and text[:1] in {"'", '"'}
        and text[-1:] == text[:1]
        and (re.search(LINE_BREAK, text) is not None or "''" in text[1:-1])
    ):
        original = text[1:-1]
        if text.startswith("'"):
            original = original.replace("''", "'")
        else:
            # YAML joins escaped physical line breaks. Validate that original
            # decoding as well as the line-preserving view used below.
            try:
                for token in yaml.scan(text):
                    _check_deadline(deadline)
                    if isinstance(token, ScalarToken) and (
                        _credential_label(token.value, deadline)
                        or redact(token.value, deadline) != token.value
                    ):
                        raise ContractError("unsupported multiline quoted credential record")
            except yaml.YAMLError:
                pass
            try:
                for token in yaml.scan(re.sub(LINE_BREAK, r"\\n", text)):
                    _check_deadline(deadline)
                    if isinstance(token, ScalarToken):
                        original = token.value
            except yaml.YAMLError:
                pass
        original = _validation_view(original, deadline)
        if QUOTED_SCALAR.fullmatch(text) is not None:
            try:
                literal = _literal_string(
                    ast.parse("(" + original + "\n)", mode="eval").body, deadline
                )
            except (SyntaxError, ValueError):
                literal = None
            if literal is not None:
                if _credential_label(literal, deadline) or redact(literal, deadline) != literal:
                    raise ContractError("unsupported multiline quoted credential record")
                return text
        if (
            _redact_assignments("(" + original + "\n)", deadline, record_member=True)
            != "(" + original + "\n)"
            or redact(original, deadline) != original
        ):
            raise ContractError("unsupported multiline quoted credential record")
        if QUOTED_SCALAR.fullmatch(text) is not None:
            return text
    line_offsets = [0]
    for marker in re.finditer(r"\r\n|[\r\n]", text):
        _check_deadline(deadline)
        line_offsets.append(marker.end())
    groups = []
    source = StringIO(text, newline=None)
    rows = 0

    def readline() -> str:
        nonlocal rows
        line = source.readline()
        if line:
            rows += 1
        return line

    while rows < len(line_offsets):
        _check_deadline(deadline)
        base = rows
        begin = line_offsets[base]
        finish = len(text)
        tokens = []
        incomplete = False
        try:
            for token in tokenize.generate_tokens(readline):
                _check_deadline(deadline)
                token = token._replace(
                    start=(token.start[0] + base, token.start[1]),
                    end=(token.end[0] + base, token.end[1]),
                )
                tokens.append(token)
                if token.type in {tokenize.NEWLINE, tokenize.ENDMARKER}:
                    finish = (
                        line_offsets[token.start[0] - 1] + token.start[1]
                        if token.start[0] <= len(line_offsets)
                        else len(text)
                    )
                    break
        except (tokenize.TokenError, IndentationError):
            incomplete = True
        groups.append((begin, finish, tokens, incomplete))
        if rows == base:
            break

    chunks = []
    end = 0
    continuation = re.compile(rf"(?:{CONTINUATION})*")
    for begin, finish, tokens, incomplete in groups:
        _check_deadline(deadline)
        if record_member and incomplete and re.search(r"\b\w+\s*\(", text[begin:finish]):
            raise ContractError("unsupported incomplete computed member")
        literals = []
        concatenated = False
        unresolved = False
        for token in tokens:
            _check_deadline(deadline)
            if token.type == tokenize.STRING:
                literals.append(token.string)
            elif token.type not in {tokenize.NL, tokenize.COMMENT}:
                if len(literals) > 1:
                    try:
                        with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                            value = ast.literal_eval(" ".join(literals))
                    except (SyntaxError, ValueError):
                        value = None
                    if isinstance(value, (str, bytes)) and _credential_label(str(value), deadline):
                        concatenated = True
                literals = []

        expressions = [(begin, finish)]
        scalar_spans: set[tuple[int, int]] = set()
        bracket_depth = 0
        for token in tokens:
            _check_deadline(deadline)
            if token.type != tokenize.OP:
                continue
            if token.string in "([{":
                bracket_depth += 1
            elif token.string in ")]}":
                bracket_depth -= 1
            elif token.string == ":" and bracket_depth == 0:
                colon = line_offsets[token.start[0] - 1] + token.start[1]
                scalar_spans.update(((begin, colon), (colon + 1, finish)))
        explicit_key = re.match(r"[^\S\r\n]*\?[^\S\r\n]*", text[begin:finish])
        if explicit_key is not None:
            scalar_spans.add((begin + explicit_key.end(), finish))
            scalar_spans.update(
                (begin + explicit_key.end(), closing)
                for opening, closing in list(scalar_spans)
                if opening == begin and closing > begin + explicit_key.end()
            )
        expressions.extend(
            span
            for span in scalar_spans
            if re.fullmatch(r"[+-]?\w+(?:[-/]\w+)*", text[span[0] : span[1]].strip()) is None
        )
        assignment_targets: set[str] = set()
        try:
            with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                statement_group = ast.parse(_validation_view(text[begin:finish], deadline))
        except (SyntaxError, ValueError):
            pass
        else:
            target_work = finish - begin
            for statement in statement_group.body:
                _check_deadline(deadline)
                targets = (
                    statement.targets
                    if isinstance(statement, ast.Assign)
                    else [statement.target]
                    if isinstance(statement, (ast.AnnAssign, ast.AugAssign))
                    else []
                )
                for target in targets:
                    for node in ast.walk(target):
                        _check_deadline(deadline)
                        target_work += 1
                        if target_work > 16 * (finish - begin) + 100_000:
                            raise ContractError("context fragment work exceeds sanitization limit")
                        if isinstance(node, ast.Subscript):
                            assignment_targets.add(ast.dump(node))
        scan_work = 0
        for marker in re.compile(r"[\[({]").finditer(text, begin, finish):
            opening = marker.start()
            cursor = opening
            brackets: list[str] = []
            quote = ""
            formatted = False
            comment = False
            while cursor < finish:
                _check_deadline(deadline)
                scan_work += 1
                if scan_work > 16 * (finish - begin) + 100_000:
                    raise ContractError("context fragment work exceeds sanitization limit")
                char = text[cursor]
                if comment:
                    comment = char not in "\r\n\x85\u2028\u2029"
                elif quote:
                    if char == "\\":
                        cursor += 2
                        continue
                    if text.startswith(quote, cursor):
                        cursor += len(quote)
                        quote = ""
                        continue
                    if formatted and char == "{":
                        if text.startswith("{{", cursor):
                            cursor += 2
                            continue
                        unresolved = True
                elif char in "\"'":
                    quote = char * 3 if text.startswith(char * 3, cursor) else char
                    quote_prefix = re.search(
                        r"(?<!\w)[rRuUbBfF]{1,2}$", text[max(begin, cursor - 3) : cursor]
                    )
                    formatted = quote_prefix is not None and "f" in quote_prefix.group().lower()
                    cursor += len(quote)
                    continue
                elif char == "#":
                    comment = True
                elif char in "([{":
                    brackets.append(char)
                elif char in ")]}":
                    if not brackets or brackets.pop() != {")": "(", "]": "[", "}": "{"}[char]:
                        break
                    if not brackets:
                        # Defer a subscript only when the complete prefix is
                        # itself a valid assignment target. A trailing name
                        # in prose ("Here is headers[...]") is insufficient.
                        assignment_target = False
                        if char == "]" and text[opening] == "[" and assignment_targets:
                            scan_work += cursor + 1 - begin
                            if scan_work > 16 * (finish - begin) + 100_000:
                                raise ContractError(
                                    "context fragment work exceeds sanitization limit"
                                )
                            try:
                                with warnings.catch_warnings(
                                    action="ignore", category=SyntaxWarning
                                ):
                                    candidate = ast.parse(
                                        _validation_view(text[begin : cursor + 1], deadline)
                                        + " = None"
                                    ).body
                                assignment_target = (
                                    len(candidate) == 1
                                    and isinstance(candidate[0], ast.Assign)
                                    and len(candidate[0].targets) == 1
                                    and isinstance(candidate[0].targets[0], ast.Subscript)
                                    and ast.dump(candidate[0].targets[0]) in assignment_targets
                                )
                            except (SyntaxError, ValueError):
                                pass
                        if not assignment_target:
                            expressions.append((opening, cursor + 1))
                        if text[opening] == "(":
                            caller = opening
                            while caller > begin and text[caller - 1] in " \t":
                                caller -= 1
                            while caller > begin and (
                                text[caller - 1].isalnum() or text[caller - 1] in "_."
                            ):
                                caller -= 1
                            if caller < opening:
                                expressions.append((caller, cursor + 1))
                        break
                cursor += 1
        parse_work = 0
        inspection_work = 0
        for opening, closing in sorted(set(expressions), key=lambda span: (span[0], -span[1])):
            _check_deadline(deadline)
            parse_work += closing - opening
            if parse_work > 16 * (finish - begin) + 100_000:
                raise ContractError("context fragment work exceeds sanitization limit")
            expression_source = _validation_view(text[opening:closing].strip(), deadline)
            try:
                with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                    expression = ast.parse(expression_source)
            except (SyntaxError, ValueError):
                if text[opening : opening + 1] != "(":
                    continue
                try:
                    with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                        expression_source = "_context_record" + _validation_view(
                            text[opening:closing], deadline
                        )
                        expression = ast.parse(expression_source)
                except (SyntaxError, ValueError):
                    continue
            json_fragment = False
            if expression_source[:1] in {"{", "["}:
                try:
                    json.loads(expression_source, object_pairs_hook=tuple)
                except ValueError:
                    pass
                else:
                    # Classification and the downstream JSON decoder must
                    # agree on the original bytes. Normalized control chars
                    # can make an invalid fragment look safe here while the
                    # decoder later splits its credential members into prose.
                    try:
                        json.loads(text[opening:closing].strip(), object_pairs_hook=tuple)
                    except ValueError:
                        raise ContractError("unsupported embedded JSON fragment") from None
                    json_fragment = True
            # A complete local literal has its own lexical boundary. Inspect
            # its immediate members here, even when an apostrophe in preceding
            # prose has confused the whole-line tokenizer or YAML parser.
            # The enclosing structured path handles standalone documents;
            # embedded records must fail closed before any supplied context
            # can leave this boundary.
            for container in ast.walk(expression):
                _check_deadline(deadline)
                inspection_work += 1
                if inspection_work > 16 * (finish - begin) + 100_000:
                    raise ContractError("context fragment work exceeds sanitization limit")
                members: Sequence[ast.AST] = []
                if isinstance(container, ast.Dict):
                    members = [*filter(None, container.keys), *container.values]
                elif isinstance(container, (ast.List, ast.Tuple, ast.Set)):
                    members = container.elts
                if (
                    not structured_source
                    and not json_fragment
                    and members
                    and any(
                        (label := _literal_string(member, deadline)) is not None
                        and _credential_label(label, deadline)
                        for member in members
                    )
                ):
                    raise ContractError("unsupported embedded credential record")
            scalar = (
                expression.body[0].annotation
                if len(expression.body) == 1
                and isinstance(expression.body[0], ast.AnnAssign)
                and expression.body[0].value is None
                else expression.body[0].value
                if (
                    record_member
                    and opening == begin
                    and closing == finish
                    or (opening, closing) in scalar_spans
                )
                and len(expression.body) == 1
                and isinstance(expression.body[0], ast.Expr)
                else None
            )
            plain_scalar = (
                scalar is not None
                and re.fullmatch(
                    r"[+-]?\w+(?:[-/]\w+)*",
                    ast.get_source_segment(expression_source, scalar) or "",
                )
                is not None
            )
            literal_lines: list[bytes] | None = None
            pending: list[tuple[ast.AST, bool]] = [(expression, scalar is not None)]
            while pending:
                _check_deadline(deadline)
                node, literal_record = pending.pop()
                literal_record = literal_record or isinstance(
                    node,
                    (
                        ast.Dict,
                        ast.List,
                        ast.Tuple,
                        ast.Set,
                        ast.Subscript,
                        ast.DictComp,
                        ast.ListComp,
                        ast.SetComp,
                        ast.GeneratorExp,
                    ),
                )
                if node is scalar and plain_scalar:
                    continue
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, (str, bytes))
                    and _credential_label(
                        node.value.decode("latin1")
                        if isinstance(node.value, bytes)
                        else node.value,
                        deadline,
                    )
                ):
                    if literal_lines is None:
                        literal_lines = (
                            expression_source.replace("\r\n", "\n")
                            .replace("\r", "\n")
                            .encode()
                            .split(b"\n")
                        )
                    assert node.end_lineno is not None and node.end_col_offset is not None
                    if node.lineno == node.end_lineno:
                        fragment = literal_lines[node.lineno - 1][
                            node.col_offset : node.end_col_offset
                        ]
                    else:
                        fragment = b"\n".join(
                            [
                                literal_lines[node.lineno - 1][node.col_offset :],
                                *literal_lines[node.lineno : node.end_lineno - 1],
                                literal_lines[node.end_lineno - 1][: node.end_col_offset],
                            ]
                        )
                    if (
                        sum(
                            token.type == tokenize.STRING
                            for token in tokenize.generate_tokens(
                                StringIO(fragment.decode()).readline
                            )
                        )
                        > 1
                    ):
                        concatenated = True
                if isinstance(node, ast.Call) and node.keywords:
                    for keyword in node.keywords:
                        literal = _literal_string(keyword.value, deadline)
                        if keyword.arg is None:
                            unresolved = True
                        elif _credential_label(keyword.arg, deadline):
                            concatenated = True
                        if literal is not None and _credential_label(literal, deadline):
                            concatenated = True
                    pending.extend((item, True) for item in node.args)
                    pending.extend((item.value, True) for item in node.keywords)
                    continue
                if (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.ctx, ast.Store)
                    and _literal_string(node.slice, deadline) is not None
                ):
                    pending.append((node.slice, literal_record))
                    continue
                if (
                    isinstance(node, ast.UnaryOp)
                    and isinstance(node.op, (ast.UAdd, ast.USub))
                    and isinstance(node.operand, ast.Constant)
                    and isinstance(node.operand.value, (int, float, complex))
                ):
                    continue
                if isinstance(node, ast.expr) and not isinstance(
                    node, (ast.Constant, ast.Name, ast.Dict, ast.List, ast.Tuple, ast.Set)
                ):
                    literal = _literal_string(node, deadline)
                    if literal is not None:
                        concatenated = concatenated or _credential_label(literal, deadline)
                        continue
                    if literal_record:
                        unresolved = True
                pending.extend((child, literal_record) for child in ast.iter_child_nodes(node))

        target_start = begin
        quoted_credential = False
        for token in tokens:
            _check_deadline(deadline)
            if token.type == tokenize.STRING:
                quoted_credential = quoted_credential or _credential_label(token.string, deadline)
            if (
                token.type != tokenize.OP
                or not token.string.endswith("=")
                or token.string in {"==", "!=", "<=", ">="}
            ):
                continue
            operator_start = line_offsets[token.start[0] - 1] + token.start[1]
            operator_end = line_offsets[token.end[0] - 1] + token.end[1]
            target_begin = target_start
            prefix = re.sub(r"\\(?:\r\n|\n|\r)", "", text[target_start:operator_start]).strip()
            target_start = operator_end
            try:
                with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                    statement = ast.parse(_validation_view(prefix, deadline) + " = None").body[-1]
            except (SyntaxError, ValueError):
                if quoted_credential:
                    raise ContractError("unsupported credential assignment") from None
                for opening in sorted(
                    {target_begin}
                    | {
                        opening
                        for opening, closing in expressions
                        if target_begin <= opening < closing <= operator_start
                    }
                ):
                    _check_deadline(deadline)
                    parse_work += operator_start - opening
                    if parse_work > 16 * (finish - begin) + 100_000:
                        raise ContractError("context fragment work exceeds sanitization limit")
                    try:
                        with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                            target_expression = ast.parse(
                                text[opening:operator_start].strip(), mode="eval"
                            ).body
                    except (SyntaxError, ValueError):
                        continue
                    literal = _literal_string(target_expression, deadline)
                    if literal is not None:
                        if _credential_label(literal, deadline):
                            raise ContractError("unsupported credential assignment")
                    elif isinstance(
                        target_expression,
                        (
                            ast.Call,
                            ast.BinOp,
                            ast.BoolOp,
                            ast.IfExp,
                            ast.NamedExpr,
                            ast.JoinedStr,
                            ast.Attribute,
                            ast.Subscript,
                        ),
                    ):
                        raise ContractError("unsupported computed assignment target")
                continue
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
                if isinstance(statement, ast.AnnAssign)
                else []
            )
            sensitive = False
            for target in targets:
                for node in ast.walk(target):
                    _check_deadline(deadline)
                    if isinstance(node, (ast.Attribute, ast.Subscript)) and not isinstance(
                        node.value, (ast.Name, ast.Attribute, ast.Subscript)
                    ):
                        raise ContractError("unsupported computed assignment target")
                    value = (
                        node.id
                        if isinstance(node, ast.Name)
                        else node.attr
                        if isinstance(node, ast.Attribute)
                        else str(node.value)
                        if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes))
                        else _literal_string(node, deadline) or ""
                        if isinstance(node, (ast.BinOp, ast.JoinedStr))
                        else ""
                    )
                    sensitive = sensitive or _credential_label(value, deadline)
            if not sensitive:
                continue
            logical = re.sub(r"\\(?:\r\n|\n|\r)", "", text[begin:finish])
            if (
                incomplete
                or "\n" in logical
                or "\r" in logical
                or any(
                    item.type == tokenize.ERRORTOKEN and item.string in {"'", '"'}
                    for item in tokens
                )
            ):
                raise ContractError("unsupported multiline credential assignment")
            if begin < end:
                break
            folded = continuation.match(text, finish)
            chunks.append(text[end:begin])
            chunks.append("[redacted]")
            end = folded.end() if folded is not None else finish
            break
        else:
            if unresolved:
                raise ContractError("unsupported computed literal record")
            if concatenated:
                raise ContractError("unsupported concatenated literal credential")
            if (
                incomplete
                and "=" in text[begin:finish]
                and _credential_label(text[begin:finish], deadline)
            ):
                raise ContractError("unsupported credential assignment")
    return "".join(chunks) + text[end:]


def _redact_plain(text: str, deadline: float | None) -> str:
    _check_deadline(deadline)
    for match in CREDENTIAL.finditer(text):
        _check_deadline(deadline)
        first_line = match.group().splitlines()[0]
        if "=" in first_line:
            value = first_line.split("=", 1)[1].strip()
            try:
                for token in tokenize.generate_tokens(StringIO(value).readline):
                    _check_deadline(deadline)
                    if token.type == tokenize.ERRORTOKEN and token.string in {"'", '"'}:
                        raise ContractError("unsupported multiline credential assignment")
            except (tokenize.TokenError, IndentationError):
                raise ContractError("unsupported multiline credential assignment") from None
    cleaned = CREDENTIAL.sub("[redacted]", text)
    references = [
        (match.group(), True)
        for match in re.finditer(r"""["'][^"'\r\n\x85\u2028\u2029]+["']""", cleaned)
    ]
    references += [
        (
            re.sub(rf"{LINE_BREAK}{INDENT}+", " ", match.group(2)),
            match.group(1) == ":",
        )
        for match in re.finditer(
            rf"{LINE_START}[^\r\n\x85\u2028\u2029:=]+([:=]){INDENT}*"
            rf"({LINE_TEXT}+(?:{CONTINUATION})*)",
            cleaned,
        )
    ]
    references += [
        (value, True)
        for value in re.findall(r"[:=][^\S\r\n]*[|>][^\r\n]*" + rf"(?:{CONTINUATION})+", cleaned)
    ]
    for value, record_member in references:
        if (
            _credential_label(value, deadline)
            or _redact_assignments(value, deadline, record_member=record_member) != value
        ):
            raise ContractError("unsupported credential representation")
    _check_deadline(deadline)
    return _redact_private_keys(cleaned, deadline)


def _sensitive_array_tail(
    text: str, closing: int, deadline: float | None, charge: list[int], cap: int
) -> str:
    """Classify a decoded sensitive array's target tail before rewriting it.

    The scan is local and forward-only.  It treats a physical break as a
    boundary unless an explicit continuation or open bracket owns it.
    Unclosed postfix syntax is unsafe; it must not detach the decoded label.
    """

    def step(count: int = 1) -> None:
        charge[0] += count
        if charge[0] > cap:
            raise ContractError("context fragment work exceeds sanitization limit")
        _check_deadline(deadline)

    def continuation(i: int) -> int:
        if text.startswith("\\\r\n", i):
            return i + 3
        if i + 1 < len(text) and text[i] == "\\" and text[i + 1] in "\r\n":
            return i + 2
        return i

    def spacing(i: int) -> int:
        while i < len(text):
            nxt = continuation(i)
            if nxt != i:
                step(nxt - i)
                i = nxt
            elif text[i] in " \t\f":
                step()
                i += 1
            else:
                break
        return i

    def bracket(i: int) -> int | None:
        stack = [{"[": "]", "(": ")", "{": "}"}[text[i]]]
        i += 1
        step()
        quote = None
        while i < len(text):
            ch = text[i]
            step()
            if quote:
                if ch == "\\" and i + 1 < len(text):
                    i += 2
                    step()
                    continue
                if ch == quote:
                    quote = None
            elif ch in "\"'":
                quote = ch
            elif ch in "[({":
                stack.append({"[": "]", "(": ")", "{": "}"}[ch])
            elif ch in "])}":
                if ch != stack.pop():
                    return None
                if not stack:
                    return i + 1
            elif ch in "\r\n" and (i == 0 or text[i - 1] != "\\"):
                # An open Python bracket owns implicit physical continuations.
                pass
            i += 1
        return None

    i = spacing(closing)
    postfixed = False
    while i < len(text):
        if text[i] == ".":
            postfixed = True
            i += 1
            step()
            begin = i
            while i < len(text):
                ch = text[i]
                if ("a" + ch).isidentifier():
                    i += 1
                    step()
                else:
                    break
            if begin == i or not text[begin:i].isidentifier():
                return "unsafe"
            i = spacing(i)
        elif text[i] == "[":
            postfixed = True
            nxt = bracket(i)
            if nxt is None:
                return "unsafe"
            i = spacing(nxt)
        else:
            break
    if i >= len(text) or text[i] in "\r\n\x85\u2028\u2029":
        return "fragment" if not postfixed else "safe_tail"
    if text[i] in "=":
        return "unsafe" if postfixed else "assignment"
    if text[i] in "<>!" or TARGET_COMPARISON_WORD.match(text, i):
        return "unsafe"
    if text[i] in "+-*/%@&|^<>" and TARGET_AUGMENTED.match(text, i):
        return "unsafe" if postfixed else "assignment"
    if text[i] in ":,":
        # Annotations and tuple/chained targets may continue over explicit
        # breaks or balanced brackets; inspect through their logical operator.
        i += 1
        step()
        while i < len(text):
            nxt = continuation(i)
            if nxt != i:
                step(nxt - i)
                i = nxt
                continue
            ch = text[i]
            if ch in "\r\n\x85\u2028\u2029":
                return "fragment"
            if ch in "[({":
                nxt = bracket(i)
                if nxt is None:
                    return "unsafe"
                i = nxt
                continue
            if ch == "=" or (ch in "+-*/%@&|^<>" and TARGET_AUGMENTED.match(text, i)):
                return "unsafe"
            if ch in "<>!":
                return "unsafe"
            if ch in "in" and TARGET_COMPARISON_WORD.match(text, i):
                return "unsafe"
            step()
            i += 1
        return "fragment"
    # Unrecognized prose or syntax can still carry an operator later in the
    # same logical record.  Do not assume the first unknown token ends the
    # target; keep the credential fragment whole through that boundary.
    while i < len(text):
        nxt = continuation(i)
        if nxt != i:
            step(nxt - i)
            i = nxt
            continue
        ch = text[i]
        if ch in "\r\n\x85\u2028\u2029":
            break
        if ch in "=<>!" or (ch in "+-*/%@&|^" and TARGET_AUGMENTED.match(text, i)):
            return "unsafe"
        if ch in "in" and TARGET_COMPARISON_WORD.match(text, i):
            return "unsafe"
        step()
        i += 1
    return "safe_tail" if postfixed else "fragment"


def _guard_sensitive_name_targets(text: str, deadline: float | None) -> None:
    """Keep a locally spelled credential NAME/attribute attached to its target.

    This local check is independent of whole-prose tokenization: contractions
    and quoted prose can hide the assignment operator from tokenize.  Simple
    assignments retain their existing complete CREDENTIAL handling.
    """
    cap = 16 * len(text) + 100_000
    work = 0

    def charge(count: int = 1) -> None:
        nonlocal work
        work += count
        if work > cap:
            raise ContractError("context fragment work exceeds sanitization limit")
        _check_deadline(deadline)

    scan = 0
    while scan < len(text):
        charge()
        if not text[scan].isidentifier() or (scan > 0 and ("a" + text[scan - 1]).isidentifier()):
            scan += 1
            continue
        begin = scan
        scan += 1
        while scan < len(text) and ("a" + text[scan]).isidentifier():
            charge()
            scan += 1
        spelling = text[begin:scan]
        if not spelling.isidentifier() or not (
            _credential_label(spelling, deadline)
            or _credential_label(unicodedata.normalize("NFKC", spelling), deadline)
        ):
            continue
        cursor = scan
        while cursor < len(text) and text[cursor] in " \t\f":
            cursor += 1
            charge()
        if cursor >= len(text) or text[cursor] not in "[.,\\":
            continue
        budget = [work]
        ownership = _sensitive_array_tail(text, scan, deadline, budget, cap)
        work = budget[0]
        if text[cursor] != "," and (
            ownership == "unsafe" or (text[cursor] == "\\" and ownership == "assignment")
        ):
            raise ContractError("unsupported credential assignment")
        if text[cursor] != ",":
            continue
        # For tuples, prove the *local* target syntax with AST.  Ordinary
        # prose such as "the secret, however, is x=1" must not be rejected.
        i = cursor + 1
        while i < len(text):
            _check_deadline(deadline)
            if text.startswith("\\\r\n", i):
                charge(3)
                i += 3
                continue
            if i + 1 < len(text) and text[i] == "\\" and text[i + 1] in "\r\n":
                charge(2)
                i += 2
                continue
            if text[i] in "\r\n\x85\u2028\u2029":
                break
            charge()
            if text[i] == "=":
                fragment = re.sub(r"\\(?:\r\n|[\r\n])", "", text[begin:i])
                charge(len(fragment))
                try:
                    with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                        parsed = ast.parse(fragment + " = None")
                except (SyntaxError, ValueError):
                    pass
                else:
                    if len(parsed.body) == 1 and isinstance(parsed.body[0], ast.Assign):
                        target = parsed.body[0].targets[0]
                        if _credential_label(spelling, deadline) or any(
                            isinstance(node, (ast.Name, ast.Attribute))
                            and _credential_label(
                                unicodedata.normalize(
                                    "NFKC", node.id if isinstance(node, ast.Name) else node.attr
                                ),
                                deadline,
                            )
                            for node in ast.walk(target)
                        ):
                            raise ContractError("unsupported credential assignment")
            i += 1


def _guard_extended_credential_assignments(text: str, deadline: float | None) -> None:
    """Reject intact credential labels with invisible and ordinary suffixes.

    These are free-text records even when the suffix makes the target invalid
    Python. Scan only the supplied text; never build a Unicode-wide table.
    """
    cap = 16 * len(text) + 100_000
    work = 0
    label = re.compile(rf"(?i)(?<![\w.-])[\w.-]*(?:{CREDENTIAL_LABEL})[\w.-]*")
    operator = re.compile(r"(?:\*\*|//|<<|>>|[+\-*/%@&|^:])?=(?!=)")
    for match in label.finditer(text):
        _check_deadline(deadline)
        work += match.end() - match.start()
        if work > cap:
            raise ContractError("context fragment work exceeds sanitization limit")
        if not _credential_label(match.group(), deadline):
            continue
        cursor = match.end()
        hidden = False
        adjacent = False
        while cursor < len(text):
            char = text[cursor]
            if char in "\r\n\x85\u2028\u2029":
                break
            category = unicodedata.category(char)
            if char in " \t\f" or category == "Zs":
                hidden = hidden or char not in " \t\f"
                adjacent = False
            elif category in {"Cf", "Mn", "Me", "Cc"}:
                hidden = True
                adjacent = True
            elif hidden and adjacent and (char.isalnum() or char in "_.-"):
                # A hidden separator may split one raw label into several
                # ordinary spelling runs, including hyphenated suffixes.
                pass
            else:
                break
            cursor += 1
            work += 1
            if work > cap:
                raise ContractError("context fragment work exceeds sanitization limit")
            _check_deadline(deadline)
        if hidden and operator.match(text, cursor):
            raise ContractError("unsupported credential assignment")


def _guard_local_assignment_owners(
    text: str, deadline: float | None, *, pending_plain_redaction: bool = False
) -> None:
    """Prove a local Python assignment target before releasing unstructured prose.

    A candidate starts at a runtime-valid identifier or a grouping opener that
    encloses it. Only Python target nodes own a spelling; subscript indices and
    annotations do not. Incomplete/unsupported local ownership fails closed.
    """
    cap = 16 * len(text) + 100_000
    work = 0

    def charge(amount: int = 1) -> None:
        nonlocal work
        work += amount
        if work > cap:
            raise ContractError("context fragment work exceeds sanitization limit")
        _check_deadline(deadline)

    def sensitive_name(spelling: str) -> bool:
        return _credential_label(spelling, deadline) or _credential_label(
            unicodedata.normalize("NFKC", spelling), deadline
        )

    def owners(node: ast.AST, lines: list[bytes]) -> list[str]:
        charge()
        if isinstance(node, (ast.Name, ast.Attribute)):
            # AST identifiers are NFKC-normalized. Recover the identifier at
            # this owner's own end position, not a subscript index, annotation,
            # or arbitrary text within the complete attribute expression.
            line_number = node.end_lineno
            end = node.end_col_offset
            if line_number is None or end is None or not 1 <= line_number <= len(lines):
                raise ContractError("unsupported credential assignment")
            line = lines[line_number - 1]
            if not 0 < end <= len(line):
                raise ContractError("unsupported credential assignment")
            begin = end
            while begin:
                charge()
                previous = begin - 1
                while previous and line[previous] & 0xC0 == 0x80:
                    charge()
                    previous -= 1
                char = line[previous:begin].decode("utf-8")
                if not ("a" + char).isidentifier():
                    break
                begin = previous
            spelling = line[begin:end].decode("utf-8")
            charge(end - begin)
            if not spelling.isidentifier():
                raise ContractError("unsupported credential assignment")
            if isinstance(node, ast.Name):
                return [spelling]
            return [*owners(node.value, lines), spelling]
        if isinstance(node, ast.Subscript):
            return owners(node.value, lines)
        if isinstance(node, (ast.Tuple, ast.List)):
            return [name for element in node.elts for name in owners(element, lines)]
        if isinstance(node, ast.Starred):
            return owners(node.value, lines)
        return []

    def named_expression_owner(start: int, grouped: bool) -> bool:
        """Inspect a locally complete walrus expression, including its raw target."""
        cursor = start
        groups: list[str] = []
        quote = ""
        escaped = False
        comment = False
        while cursor < len(text):
            charge()
            char = text[cursor]
            if comment:
                if char in "\r\n\x85\u2028\u2029":
                    comment = False
                else:
                    cursor += 1
                    continue
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = ""
                cursor += 1
                continue
            if char in "\"'":
                quote = char
                cursor += 1
                continue
            if char == "#":
                comment = True
                cursor += 1
                continue
            if char in "([{":
                groups.append(char)
            elif char in ")]}":
                if not groups:
                    break
                if {"(": ")", "[": "]", "{": "}"}[groups.pop()] != char:
                    return False
                if grouped and not groups:
                    cursor += 1
                    break
            # The initial colon is the walrus operator, not a clause
            # delimiter. A later colon ends an if/while condition.
            elif (
                not grouped
                and not groups
                and char in ",:\r\n\x85\u2028\u2029"
                and (char != ":" or not text.startswith(":=", cursor))
            ):
                break
            cursor += 1
        fragment = _validation_view(text[start:cursor], deadline)
        charge(len(fragment))
        if not grouped:
            fragment = "(" + fragment + ")"
        try:
            with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                expression = ast.parse(fragment, mode="eval")
        except (SyntaxError, ValueError):
            return False
        for node in ast.walk(expression):
            charge()
            if isinstance(node, ast.NamedExpr):
                spelling = ast.get_source_segment(fragment, node.target)
                if spelling is not None and sensitive_name(spelling):
                    return True
        return False

    def assignment_target(start: int) -> list[str] | None:
        # Inspect one physical/logical record. Grouping and explicit backslash
        # continuations carry the record through CR, LF, and CRLF.
        cursor = start
        groups: list[str] = []
        quote = ""
        escaped = False
        comment = False
        while cursor < len(text):
            charge()
            char = text[cursor]
            if comment:
                if char in "\r\n\x85\u2028\u2029":
                    comment = False
                else:
                    cursor += 1
                    continue
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = ""
                cursor += 1
                continue
            # An apostrophe between identifier characters is prose, not
            # a Python quote opener (It's, don't).
            if char in "\"'" and (
                char != "'"
                or not (
                    cursor > 0
                    and cursor + 1 < len(text)
                    and ("a" + text[cursor - 1]).isidentifier()
                    and ("a" + text[cursor + 1]).isidentifier()
                )
            ):
                quote = char
                cursor += 1
                continue
            if char == "#":
                comment = True
                cursor += 1
                continue
            if char == "\\" and cursor + 1 < len(text) and text[cursor + 1] in "\r\n":
                cursor += 3 if text.startswith("\\\r\n", cursor) else 2
                charge(2)
                continue
            if char in "([{":
                groups.append(char)
            elif char in ")]}":
                if not groups or {"(": ")", "[": "]", "{": "}"}[groups[-1]] != char:
                    return None
                groups.pop()
            elif char in "\r\n\x85\u2028\u2029" and not groups:
                return None
            elif char == "=" and not groups:
                if (cursor + 1 < len(text) and text[cursor + 1] == "=") or (
                    cursor > start
                    and text[cursor - 1] in "!<>="
                    and text[max(start, cursor - 2) : cursor] not in ("<<", ">>")
                ):
                    cursor += 1
                    continue
                fragment = text[start : cursor + 1]
                charge(len(fragment))
                view = _validation_view(fragment + " None", deadline)
                lines = [line.encode("utf-8") for line in view.splitlines(keepends=True)]
                charge(sum(len(line) for line in lines))
                try:
                    with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                        statement = ast.parse(view).body
                except (SyntaxError, ValueError):
                    return None
                if len(statement) != 1:
                    return None
                item = statement[0]
                targets = (
                    item.targets
                    if isinstance(item, ast.Assign)
                    else ([item.target] if isinstance(item, (ast.AnnAssign, ast.AugAssign)) else [])
                )
                return [name for target in targets for name in owners(target, lines)]
            cursor += 1
        return None

    # These complete plaintext records are still validated and removed by the
    # existing CONTEXT_PART path. Do not reject a target already inside one.
    # Structured early returns have no later plaintext pass and never opt in.
    covered_records = iter(CREDENTIAL.finditer(text)) if pending_plain_redaction else iter(())
    covered_record = next(covered_records, None)

    # Track grouping openers in a single pass. Quote state is deliberately
    # local to candidate parsing: quoted prose before an assignment can be
    # syntactically invalid while the target itself is still valid Python.
    _guard_extended_credential_assignments(text, deadline)
    openers: list[tuple[str, int]] = []
    scan = 0
    comment = False
    while scan < len(text):
        charge()
        char = text[scan]
        if comment:
            if char in "\r\n\x85\u2028\u2029":
                comment = False
        elif char == "#" and openers:
            comment = True
        elif char in "([":
            openers.append((char, scan))
        elif char in ")]" and openers:
            openers.pop()
        if not char.isidentifier() or (scan and ("a" + text[scan - 1]).isidentifier()):
            scan += 1
            continue
        begin = scan
        scan += 1
        while scan < len(text) and ("a" + text[scan]).isidentifier():
            charge()
            scan += 1
        spelling = text[begin:scan]
        while covered_record is not None and covered_record.end() <= begin:
            charge()
            covered_record = next(covered_records, None)
        if (
            covered_record is not None
            and covered_record.start() <= begin
            and scan <= covered_record.end()
        ):
            continue
        if not spelling.isidentifier() or not sensitive_name(spelling):
            continue
        lookahead = scan
        while lookahead < len(text):
            if text[lookahead] in " \t\f" or (
                openers and text[lookahead] in "\r\n\x85\u2028\u2029"
            ):
                charge()
                lookahead += 1
            elif openers and text[lookahead] == "#":
                while lookahead < len(text) and text[lookahead] not in "\r\n\x85\u2028\u2029":
                    charge()
                    lookahead += 1
            else:
                break
        # A grouped target can continue through comments and physical lines.
        if not openers and (
            lookahead >= len(text) or text[lookahead] not in "=:+-*/%@&|^\\,.)]([<>"
        ):
            continue
        if text.startswith(":=", lookahead) and (
            named_expression_owner(begin, grouped=False)
            or any(
                named_expression_owner(position, grouped=True) for _, position in reversed(openers)
            )
        ):
            raise ContractError("unsupported credential assignment")
        starts = [begin]
        for kind, position in reversed(openers):
            charge()
            # A postfix '[' is a subscript of its preceding expression, not
            # a new grouping target rooted at its index.
            before = position - 1
            if (
                kind == "["
                and before >= 0
                and (("a" + text[before]).isidentifier() or text[before] in ")]")
            ):
                continue
            starts.append(position)
        for start in starts:
            charge()
            labels = assignment_target(start)
            if labels is not None and any(sensitive_name(label) for label in labels):
                raise ContractError("unsupported credential assignment")


def _redact_local_json(text: str, deadline: float | None) -> str:
    """Sanitize complete JSON containers from their own opening delimiter."""
    decoder = json.JSONDecoder(object_pairs_hook=tuple)
    assignment_operator = re.compile(r"(?:(?:\*\*|//|<<|>>|[+\-*/%@&|^])?=)")
    chunks: list[str] = []
    end = 0
    work = 0
    complete_assignments = tuple(
        (match.start(), match.end()) for match in CREDENTIAL.finditer(text) if "[" in match.group()
    )
    for opening in re.finditer(r"[\[{]", text):
        _check_deadline(deadline)
        if opening.start() < end:
            continue
        try:
            value, closing = decoder.raw_decode(text, opening.start())
        except json.JSONDecodeError:
            # A failed decode may have examined the entire remaining suffix.
            work += len(text) - opening.start()
            if work > 16 * len(text) + 100_000:
                raise ContractError("context fragment work exceeds sanitization limit")
            continue
        work += closing - opening.start()
        if work > 16 * len(text) + 100_000:
            raise ContractError("context fragment work exceeds sanitization limit")
        if text[opening.start()] == "[":
            fragment = text[opening.start() : closing]
            # JSON escapes are part of a label's spelling, not its meaning.
            # Inspect decoded members before deciding whether this array can
            # be separated from the assignment or comparison that follows it.
            pending = [value]
            sensitive = False
            while pending:
                _check_deadline(deadline)
                member = pending.pop()
                work += 1
                if work > 16 * len(text) + 100_000:
                    raise ContractError("context fragment work exceeds sanitization limit")
                if isinstance(member, str):
                    sensitive = _credential_label(member, deadline) or sensitive
                elif isinstance(member, (list, tuple)):
                    pending.extend(member)
                elif isinstance(member, dict):
                    pending.extend(member.items())
            if sensitive:
                budget = [work]
                ownership = _sensitive_array_tail(
                    text, closing, deadline, budget, 16 * len(text) + 100_000
                )
                work = budget[0]
                if ownership == "unsafe":
                    raise ContractError("unsupported credential assignment")
            # A quoted prose prefix can make the assignment pass miss this
            # target. Inspect the complete target before rewriting its first
            # array, which would otherwise detach the credential from its RHS.
            if sensitive:
                cursor = closing
                while cursor < len(text):
                    _check_deadline(deadline)
                    work += 1
                    if work > 16 * len(text) + 100_000:
                        raise ContractError("context fragment work exceeds sanitization limit")
                    if text[cursor].isspace():
                        cursor += 1
                    elif (
                        text[cursor] == "\\"
                        and cursor + 1 < len(text)
                        and text[cursor + 1] in "\r\n"
                    ):
                        cursor += 3 if text.startswith("\\\r\n", cursor) else 2
                    elif text[cursor] == "[":
                        try:
                            _, next_cursor = decoder.raw_decode(text, cursor)
                        except json.JSONDecodeError:
                            line_end = text.find("\n", cursor)
                            unresolved = text[cursor : line_end if line_end >= 0 else len(text)]
                            work += len(unresolved)
                            if work > 16 * len(text) + 100_000:
                                raise ContractError(
                                    "context fragment work exceeds sanitization limit"
                                )
                            if re.search(r"(?<![<>=!])=|==", unresolved):
                                raise ContractError("unsupported credential assignment")
                            break
                        work += next_cursor - cursor
                        cursor = next_cursor
                    elif text[cursor] == ".":
                        member = re.compile(r"\.[A-Za-z_]\w*").match(text, cursor)
                        if member is None:
                            break
                        cursor += len(member.group())
                    else:
                        break
                if cursor < len(text) and (
                    text[cursor] in ":,=" or assignment_operator.match(text, cursor)
                ):
                    # Include annotations and tuple targets. A comparison is
                    # also unsafe when paired prose quotes expose the array.
                    line_end = text.find("\n", cursor)
                    tail = text[cursor : line_end if line_end >= 0 else len(text)]
                    work += len(tail)
                    if work > 16 * len(text) + 100_000:
                        raise ContractError("context fragment work exceeds sanitization limit")
                    work += len(complete_assignments)
                    if work > 16 * len(text) + 100_000:
                        raise ContractError("context fragment work exceeds sanitization limit")
                    # A complete later match removes the whole statement.
                    # Sensitivity was already decided from decoded members.
                    covered = any(
                        start <= opening.start() < stop
                        and stop >= (line_end if line_end >= 0 else len(text))
                        for start, stop in complete_assignments
                    )
                    if not covered and re.search(
                        r"(?<![<>=!])(?:\*\*|//|<<|>>|[+\-*/%@&|^])?=|==", tail
                    ):
                        raise ContractError("unsupported credential assignment")
            cursor = closing
            continued = False
            while cursor < len(text):
                if text[cursor].isspace():
                    cursor += 1
                elif text.startswith("\\\r\n", cursor):
                    cursor += 3
                    continued = True
                elif text.startswith("\\\n", cursor):
                    cursor += 2
                    continued = True
                else:
                    break
                _check_deadline(deadline)
            # Charge suffix scans as well as JSON decoding. Repeated arrays
            # cannot rescan long whitespace for free.
            work += cursor - closing
            if work > 16 * len(text) + 100_000:
                raise ContractError("context fragment work exceeds sanitization limit")
            if assignment_operator.match(text, cursor) is not None:
                # The assignment pass has already had first refusal. If it
                # left a sensitive target intact, local rewriting would split
                # that target from its value across a continued assignment.
                if continued and sensitive:
                    raise ContractError("unsupported credential assignment")
                continue
        fragment = text[opening.start() : closing]
        cleaned = _structured(fragment, deadline)
        if cleaned is None:
            raise ContractError("unsupported structured context")
        chunks.extend((text[end : opening.start()], cleaned))
        end = closing
    return "".join(chunks) + text[end:]


def _guard_multiline_assignment_ownership(text: str, deadline: float | None) -> None:
    """Classify assignment targets within lexical Python statements.

    A NEWLINE token ends a logical statement; NL inside brackets or after an
    explicit continuation does not.  Ordinary preceding and following lines
    cannot multiply the parsing work or make a valid assignment unparsable.
    """
    if not (any(char in text for char in "[()") and "=" in text and re.search(LINE_BREAK, text)):
        return
    _check_deadline(deadline)
    # String offsets remain in the original text.  Token line numbers are
    # obtained from the normalized view and never converted from byte columns.
    line_starts = [0]
    line_ends = []
    for marker in re.finditer(LINE_BREAK, text):
        _check_deadline(deadline)
        line_ends.append(marker.start())
        line_starts.append(marker.end())
    line_ends.append(len(text))
    view = _validation_view(text, deadline)
    boundaries = []
    logical_start = 0
    try:
        for token in tokenize.generate_tokens(StringIO(view).readline):
            _check_deadline(deadline)
            if token.type == tokenize.NEWLINE:
                end_line = min(token.end[0] - 1, len(line_ends) - 1)
                if logical_start <= end_line:
                    boundaries.append((logical_start, end_line))
                logical_start = end_line + 1
            elif token.type == tokenize.ENDMARKER:
                if logical_start < len(line_ends):
                    boundaries.append((logical_start, len(line_ends) - 1))
    except (tokenize.TokenError, IndentationError):
        # A malformed lexical prefix cannot safely establish the later
        # statement boundary.  Retain the existing conservative rejection.
        if re.search(CREDENTIAL_LABEL, text, re.IGNORECASE) is not None:
            raise ContractError("unsupported multiline credential assignment") from None
        return
    local_rewrite_stable: bool | None = None
    work = 0
    cap = 16 * len(text) + 100_000
    for begin_line, end_line in boundaries:
        _check_deadline(deadline)
        begin, finish = line_starts[begin_line], line_ends[end_line]
        if begin >= finish:
            continue
        fragment = text[begin:finish]
        if (
            not any(char in fragment for char in "[()")
            or "=" not in fragment
            or not re.search(LINE_BREAK, fragment)
        ):
            continue
        work += len(fragment)
        if work > cap:
            raise ContractError("context fragment work exceeds sanitization limit")
        # Isolated indented statements are valid after removing their shared
        # margin.  This permits a body statement under an unrelated header.
        lines = fragment.splitlines(keepends=True)
        indents = [len(part) - len(part.lstrip(" \t")) for part in lines if part.strip()]
        if indents:
            margin = min(indents)
            if margin:
                fragment = "".join(part[margin:] if part.strip() else part for part in lines)
        try:
            with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                parsed = ast.parse(_validation_view(fragment, deadline))
        except (SyntaxError, ValueError):
            continue
        covered = any(
            match.end() >= len(fragment) and "[" in fragment[match.start() : match.end()]
            for match in CREDENTIAL.finditer(fragment)
        )
        for statement in ast.walk(parsed):
            _check_deadline(deadline)
            work += 1
            if work > cap:
                raise ContractError("context fragment work exceeds sanitization limit")
            if not isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                continue
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            if not targets or statement.lineno == statement.end_lineno:
                continue
            for target in targets:
                for node in ast.walk(target):
                    _check_deadline(deadline)
                    work += 1
                    if work > cap:
                        raise ContractError("context fragment work exceeds sanitization limit")
                    label = (
                        node.id
                        if isinstance(node, ast.Name)
                        else node.attr
                        if isinstance(node, ast.Attribute)
                        else _literal_string(node, deadline)
                        if isinstance(node, (ast.Constant, ast.BinOp, ast.JoinedStr))
                        else None
                    )
                    if label is not None and _credential_label(label, deadline):
                        if covered:
                            if local_rewrite_stable is None:
                                local_rewrite_stable = _redact_local_json(text, deadline) == text
                            if local_rewrite_stable:
                                continue
                        raise ContractError("unsupported multiline credential assignment")


def redact(text: str, deadline: float | None = None) -> str:
    try:
        _check_deadline(deadline)
        _check_escaped_record_labels(text, deadline)
        if "?" in text:
            _complete_public_explicit_key(text, deadline)
        if PRIVATE_KEY_BEGIN.search(text) is not None:
            _redact_private_keys(text, deadline)
        if not any(marker in text for marker in "{}[]:=\"'&#*!|>?-%"):
            return _redact_plain(text, deadline)
        structured = _structured(text, deadline)
        if structured is not None:
            _guard_local_assignment_owners(structured, deadline)
            return structured
        _guard_sensitive_name_targets(text, deadline)
        text = _redact_assignments(text, deadline)
        _guard_multiline_assignment_ownership(text, deadline)
        _guard_local_assignment_owners(text, deadline, pending_plain_redaction=True)
        text = _redact_local_json(text, deadline)
        decoder = json.JSONDecoder(object_pairs_hook=tuple)
        chunks = []
        end = 0
        cursor = 0
        while start := CONTEXT_PART.search(text, cursor):
            _check_deadline(deadline)
            cursor = start.end()
            if start.group("credential") is not None:
                chunks.append(_redact_plain(text[end : start.start()], deadline))
                _redact_plain(start.group(), deadline)
                chunks.append("[redacted]")
                end = cursor
                continue
            try:
                value, consumed = decoder.raw_decode(text, start.start())
            except json.JSONDecodeError:
                continue
            fragment = text[start.start() : consumed]
            cleaned = _structured(fragment, deadline)
            if cleaned is None:
                raise ContractError("unsupported structured context")
            if (
                isinstance(value, str)
                and _credential_label(value, deadline)
                and cleaned == fragment
            ):
                raise ContractError("unsupported credential representation")
            chunks.append(_redact_plain(text[end : start.start()], deadline))
            chunks.append(cleaned)
            end = consumed
            cursor = end
        return "".join(chunks) + _redact_plain(text[end:], deadline)
    except UnicodeError as error:
        raise ContractError("unsupported Unicode context representation") from error
    except (RecursionError, MemoryError) as error:
        raise ContractError("context nesting exceeds sanitization limit") from error


def workspace_id(path: Path) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, os.path.normcase(str(path.resolve()))))


def excluded_reference(reference: str, exclusions: Sequence[str]) -> bool:
    normalized = posixpath.normpath(reference.replace("\\", "/"))
    parts = normalized.casefold().split("/")
    if any(part in EXCLUDED_COMPONENTS or part.startswith(".env.") for part in parts):
        return True
    for pattern in exclusions:
        pattern = posixpath.normpath(pattern.replace("\\", "/")).rstrip("/")
        if fnmatch.fnmatchcase(normalized, pattern) or normalized.startswith(pattern + "/"):
            return True
    return False


def collect_context(
    task_representation: str,
    attachments: Sequence[Mapping[str, Any]],
    excluded_paths: Sequence[str],
    deadline: float | None = None,
) -> dict[str, Any]:
    if not isinstance(task_representation, str):
        raise ContractError("invalid task context")
    retained = []
    unavailable = False
    for attachment in attachments:
        reference = attachment.get("reference")
        if (
            not isinstance(reference, str)
            or excluded_reference(reference, excluded_paths)
            or attachment.get("authorized") is not True
        ):
            unavailable = True
            continue
        item = dict(attachment)
        if item.get("text_representation") is not None:
            item["text_representation"] = redact(item["text_representation"], deadline)
        retained.append(item)
    return {
        "task_representation": redact(task_representation, deadline),
        "attachments": retained,
        "unavailable": unavailable,
    }
