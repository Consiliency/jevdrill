"""Supplied context only; never follow attachment references or search user files."""

import fnmatch
import json
import os
import posixpath
import re
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from .contracts import ContractError

EXCLUDED_COMPONENTS = frozenset({".env", ".ssh", ".gnupg", "credentials", "id_rsa", "id_ed25519"})
CREDENTIAL_LABEL = r"authorization|api[\s_-]*key|access[\s_-]*token|password|secret"
CONTINUATION = r"(?:\r\n|\n|\r)[^\S\r\n]+[^\r\n]*"
CREDENTIAL = re.compile(
    rf"""(?i)(?:[\w.]+\s*\[\s*)?["']?[^\S\r\n]*[\w.-]*(?:{CREDENTIAL_LABEL})"""
    r"""[\w.-]*[^\S\r\n]*["']?\s*\]?\s*[:=][^\r\n]*"""
    rf"(?:{CONTINUATION})*"
    + r"""|(?<![^\r\n"'])[ \t]*(?:bearer|basic)\s+[^\s"',;}\]]+"""
    + r"|-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----"
)
CONTEXT_PART = re.compile(
    "(?P<credential>" + CREDENTIAL.pattern.removeprefix("(?i)") + r")|[\[{\"]",
    re.IGNORECASE,
)


def _credential_label(value: str) -> bool:
    return re.search(CREDENTIAL_LABEL, value.strip(), re.IGNORECASE) is not None


def _redact_node(node: Node, seen: set[int]) -> bool:
    if id(node) in seen:
        return False
    seen.add(id(node))
    changed = False
    if isinstance(node, MappingNode):
        sensitive = any(
            isinstance(item, ScalarNode) and _credential_label(item.value)
            for pair in node.value
            for item in pair
        )
        for index, (key, value) in enumerate(node.value):
            changed = _redact_node(key, seen) or changed
            if sensitive:
                node.value[index] = (key, ScalarNode("tag:yaml.org,2002:str", "[redacted]"))
                changed = True
            else:
                changed = _redact_node(value, seen) or changed
    elif isinstance(node, SequenceNode):
        if any(
            isinstance(item, ScalarNode) and _credential_label(item.value) for item in node.value
        ):
            node.value = [ScalarNode("tag:yaml.org,2002:str", "[redacted]") for _ in node.value]
            return True
        for item in node.value:
            changed = _redact_node(item, seen) or changed
    elif isinstance(node, ScalarNode):
        cleaned = redact(node.value)
        changed = cleaned != node.value
        node.value = cleaned
    return changed


def _structured(text: str) -> str | None:
    try:
        node = yaml.compose(text)
    except yaml.YAMLError:
        return None
    if isinstance(node, (MappingNode, SequenceNode)) or (
        isinstance(node, ScalarNode) and node.style in ("'", '"')
    ):
        return yaml.serialize(node) if _redact_node(node, set()) else text
    return None


def _redact_plain(text: str) -> str:
    cleaned = CREDENTIAL.sub("[redacted]", text)
    references = re.findall(r"""["']([^"'\r\n]+)["']""", cleaned)
    references += re.findall(r"(?im)^[ \t-]*(?:name|key)\s*[:=]\s*(.+)", cleaned)
    if any(_credential_label(value) for value in references):
        raise ContractError("unsupported credential representation")
    return cleaned


def redact(text: str) -> str:
    try:
        structured = _structured(text)
        if structured is not None:
            return structured
        decoder = json.JSONDecoder(object_pairs_hook=tuple)
        chunks = []
        end = 0
        cursor = 0
        while start := CONTEXT_PART.search(text, cursor):
            cursor = start.end()
            if start.group("credential") is not None:
                chunks.append(_redact_plain(text[end : start.start()]))
                chunks.append("[redacted]")
                end = cursor
                continue
            try:
                value, consumed = decoder.raw_decode(text, start.start())
            except json.JSONDecodeError:
                continue
            fragment = text[start.start() : consumed]
            cleaned = _structured(fragment)
            if cleaned is None:
                raise ContractError("unsupported structured context")
            if isinstance(value, str) and _credential_label(value) and cleaned == fragment:
                raise ContractError("unsupported credential representation")
            chunks.append(_redact_plain(text[end : start.start()]))
            chunks.append(cleaned)
            end = consumed
            cursor = end
        return "".join(chunks) + _redact_plain(text[end:])
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
            item["text_representation"] = redact(item["text_representation"])
        retained.append(item)
    return {
        "task_representation": redact(task_representation),
        "attachments": retained,
        "unavailable": unavailable,
    }
