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
CONTINUATION = r"(?:\r\n|\n|\r)[^\S\r\n]+[^\r\n]*"
CREDENTIAL = re.compile(
    rf"""(?i)(?<![\w.-])(?:[\w.]+\s*+\[\s*+)?(?:["'][^\S\r\n]*+)?[\w.-]*(?:{CREDENTIAL_LABEL})"""
    r"""[\w.-]*[^\S\r\n]*+["']?\s*+\]?\s*+(?::|(?:\*\*|//|<<|>>|[+\-*/%@&|^])?=)[^\r\n]*"""
    rf"(?:{CONTINUATION})*"
    + r"""|(?<![^\r\n"'])[ \t]*(?:bearer|basic)\s+[^\s"',;}\]]+"""
    + r"|-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----"
)
CONTEXT_PART = re.compile(
    "(?P<credential>" + CREDENTIAL.pattern.removeprefix("(?i)") + r")|[\[{\"]",
    re.IGNORECASE,
)


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None and monotonic() >= deadline:
        raise TimeoutError("context sanitization deadline exceeded")


def _credential_label(value: str, deadline: float | None = None) -> bool:
    while value.strip().startswith(('"', "'")):
        _check_deadline(deadline)
        try:
            try:
                decoded = json.loads(value)
            except ValueError:
                with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                    decoded = ast.literal_eval(value)
        except (ValueError, RecursionError):
            break
        except SyntaxError:
            break
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
        cleaned = redact(node.value, deadline)
        changed = cleaned != node.value
        node.value = cleaned
    return changed


def _structured(text: str, deadline: float | None) -> str | None:
    spans = []
    depth = 0
    try:
        for token in yaml.scan(text):
            _check_deadline(deadline)
            if isinstance(token, (AliasToken, AnchorToken, TagToken)):
                raise ContractError("unsupported YAML graph or tag")
            if isinstance(token, ScalarToken):
                if token.value == "<<":
                    raise ContractError("unsupported YAML merge")
                if "\\" in token.value:
                    try:
                        with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                            literal = ast.literal_eval(
                                text[token.start_mark.index : token.end_mark.index]
                            )
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
        node = yaml.compose(text)
    except yaml.YAMLError:
        if re.search(r"(?m)^[^\S\r\n]*\?[^\S\r\n]*[\[{]", text):
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
        changed = _redact_node(node, set(), deadline)
        result = yaml.serialize(node) if changed or comments else text
        _check_deadline(deadline)
        return result
    if comments:
        return redact(node.value, deadline) if isinstance(node, ScalarNode) else ""
    return None


def _redact_assignments(text: str, deadline: float | None) -> str:
    chunks = []
    end = 0
    for match in re.finditer(
        r"(?m)^(?:[^\r\n]*\\(?:\r\n|\n|\r))*[^\r\n]*=[^\r\n]*" + rf"(?:{CONTINUATION})*",
        text,
    ):
        _check_deadline(deadline)
        first_line = re.sub(r"\\(?:\r\n|\n|\r)", "", match.group()).splitlines()[0].strip()
        tokens = []
        incomplete = False
        try:
            for token in tokenize.generate_tokens(StringIO(first_line).readline):
                _check_deadline(deadline)
                tokens.append(token)
        except (tokenize.TokenError, IndentationError):
            incomplete = True
        labeled = False
        for index, token in enumerate(tokens):
            _check_deadline(deadline)
            if token.type == tokenize.NAME:
                labeled = labeled or _credential_label(token.string, deadline)
            elif token.type == tokenize.STRING:
                with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                    literal = ast.literal_eval(token.string)
                labeled = labeled or _credential_label(str(literal), deadline)
            if (
                not labeled
                or token.type != tokenize.OP
                or not token.string.endswith("=")
                or token.string in {"==", "!=", "<=", ">="}
            ):
                continue
            try:
                with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
                    statement = ast.parse(first_line[: token.start[1]].strip() + " = None").body[-1]
            except (SyntaxError, ValueError):
                if any(
                    item.type == tokenize.STRING and _credential_label(item.string, deadline)
                    for item in tokens[:index]
                ):
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
                        else ""
                    )
                    sensitive = sensitive or _credential_label(value, deadline)
            if not sensitive:
                continue
            if incomplete or any(
                item.type == tokenize.ERRORTOKEN and item.string in {"'", '"'} for item in tokens
            ):
                raise ContractError("unsupported multiline credential assignment")
            chunks.append(text[end : match.start()])
            chunks.append("[redacted]")
            end = match.end()
            break
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
    references = [match.group() for match in re.finditer(r"""["'][^"'\r\n]+["']""", cleaned)]
    references += re.findall(r"(?m)^[^\r\n:=]+[:=][^\S\r\n]*(.+)", cleaned)
    references += re.findall(r"[:=][^\S\r\n]*[|>][^\r\n]*" + rf"(?:{CONTINUATION})+", cleaned)
    if any(_credential_label(value, deadline) for value in references):
        raise ContractError("unsupported credential representation")
    _check_deadline(deadline)
    return cleaned


def redact(text: str, deadline: float | None = None) -> str:
    try:
        _check_deadline(deadline)
        text = _redact_assignments(text, deadline)
        structured = _structured(text, deadline)
        if structured is not None:
            return structured
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
    except RecursionError as error:
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
