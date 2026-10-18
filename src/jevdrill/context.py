"""Supplied context only; never follow attachment references or search user files."""

import ast
import fnmatch
import json
import os
import posixpath
import re
import sys
import tokenize
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
CREDENTIAL = re.compile(
    rf"""(?i)(?<![\w.-])(?:[\w.]+\s*+\[\s*+)?(?:["'][^\S\r\n]*+)?[\w.-]*(?:{CREDENTIAL_LABEL})"""
    r"""[\w.-]*[^\S\r\n]*+["']?\s*+\]?\s*+(?::|(?:\*\*|//|<<|>>|[+\-*/%@&|^])?=)"""
    rf"{LINE_TEXT}*"
    rf"(?:{CONTINUATION})*"
    + rf"""|(?<![^\r\n\x85\u2028\u2029"']){INDENT}*(?:bearer|basic)\s+[^\s"',;}}\]]+"""
    + rf"""[^\r\n\x85\u2028\u2029"',;}}\]]*(?:{CONTINUATION})*"""
)
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
    decoded_end = 0
    escaped_quotes: set[int] = set()
    for opening in re.finditer(r"""['"]""", text):
        _check_deadline(deadline)
        if opening.start() in escaped_quotes or opening.start() < decoded_end:
            continue
        quoted = QUOTED_SCALAR.match(text, opening.start())
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
        if quoted is not None and (
            re.search(LINE_BREAK, quoted.group()) is not None or "''" in quoted.group()[1:-1]
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
                if token.style in {"'", '"'}:
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
        _redact_assignments(text, deadline)
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
            or any(kind == tokenize.FSTRING_START for kind, _ in significant)
            or any(value == "+" for _, value in significant)
            or (
                malformed
                and (
                    "(" in expression or "+" in expression or "'" in expression or '"' in expression
                )
            )
        )
        if not computed:
            continue
        if QUOTED_SCALAR.fullmatch(expression) is not None:
            _redact_assignments(expression, deadline, record_member=True)
            continue
        try:
            with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                node = ast.parse("(" + expression + "\n)", mode="eval").body
            literal = _literal_string(node, deadline)
        except (SyntaxError, ValueError):
            literal = None
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


def _redact_assignments(text: str, deadline: float | None, *, record_member: bool = False) -> str:
    _check_deadline(deadline)
    if "?" in text:
        _validate_explicit_keys(text, deadline)
    for member in re.finditer(r"`+([^`]+)", text):
        original = _validation_view(member.group(1), deadline)
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


def redact(text: str, deadline: float | None = None) -> str:
    try:
        _check_deadline(deadline)
        if PRIVATE_KEY_BEGIN.search(text) is not None:
            _redact_private_keys(text, deadline)
        if not any(marker in text for marker in "{}[]:=\"'&#*!|>?-%"):
            return _redact_plain(text, deadline)
        structured = _structured(text, deadline)
        if structured is not None:
            return structured
        text = _redact_assignments(text, deadline)
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
