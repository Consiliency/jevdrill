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
PRIVATE_KEY_BEGIN = re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----", re.IGNORECASE)
PRIVATE_KEY_END = re.compile(r"-----END [^-]*PRIVATE KEY-----", re.IGNORECASE)
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
        if (
            not _credential_label(node.value, deadline)
            and _redact_assignments(node.value, deadline, record_member=True) != node.value
        ):
            raise ContractError("unsupported embedded credential assignment")
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
    for sequence in re.finditer(
        rf"{LINE_START}{INDENT}*-(?:{INDENT}+{LINE_TEXT}*|(?={LINE_BREAK}|$))"
        rf"(?:{CONTINUATION})*",
        text,
    ):
        _check_deadline(deadline)
        credential_sequence = (
            credential_sequence
            or _credential_label(sequence.group(), deadline)
            or _redact_assignments(sequence.group(), deadline) != sequence.group()
        )
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
        _redact_assignments(text, deadline)
        changed = _redact_node(node, set(), deadline)
        result = yaml.serialize(node) if changed or comments else text
        _check_deadline(deadline)
        return result
    if credential_sequence:
        raise ContractError("unsupported structured credential sequence")
    if comments:
        _redact_assignments(text, deadline)
        return redact(node.value, deadline) if isinstance(node, ScalarNode) else ""
    return None


def _redact_assignments(text: str, deadline: float | None, *, record_member: bool = False) -> str:
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
        explicit_key = re.match(r"[^\S\r\n]*\?[^\S\r\n]+", text[begin:finish])
        if explicit_key is not None:
            scalar_spans.add((begin + explicit_key.end(), finish))
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
            try:
                with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                    expression = ast.parse(text[opening:closing].strip())
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
                    ast.get_source_segment(text[opening:closing].strip(), scalar) or "",
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
                            text[opening:closing]
                            .strip()
                            .replace("\r\n", "\n")
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
            prefix = re.sub(r"\\(?:\r\n|\n|\r)", "", text[target_start:operator_start]).strip()
            target_start = operator_end
            try:
                with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                    statement = ast.parse(prefix + " = None").body[-1]
            except (SyntaxError, ValueError):
                if quoted_credential:
                    raise ContractError("unsupported credential assignment") from None
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
        (match.group(2), match.group(1) == ":")
        for match in re.finditer(
            rf"{LINE_START}[^\r\n\x85\u2028\u2029:=]+([:=]){INDENT}*({LINE_TEXT}+)", cleaned
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
