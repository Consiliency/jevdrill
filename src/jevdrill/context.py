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

from .contracts import ContractError

EXCLUDED_COMPONENTS = frozenset({".env", ".ssh", ".gnupg", "credentials", "id_rsa", "id_ed25519"})
CREDENTIAL_NAMES = frozenset(
    {
        "authorization",
        "proxyauthorization",
        "apikey",
        "xapikey",
        "accesstoken",
        "password",
        "secret",
    }
)
CONTINUATION = r"(?:\r\n|\n|\r)[^\S\r\n]+[^\r\n]*"
CREDENTIAL = re.compile(
    r"""(?i)["']?authorization["']?\s*[:=]\s*"""
    r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\r\n]+)"""
    f"(?:{CONTINUATION})*"
    + r"""|(?<![^\r\n"'])[ \t]*(?:bearer|basic)\s+[^\s"',;}\]]+"""
    + r"""|["']?(?:api[_-]?key|access[_-]?token|password|secret)["']?\s*[:=]\s*"""
    r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s,;}]+)"""
    f"(?:{CONTINUATION})*"
    + r"|-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----"
)


def _redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        names = {key.casefold().replace("-", "").replace("_", ""): key for key in value}
        name = value.get(names.get("name", ""))
        sensitive = (
            isinstance(name, str)
            and name.casefold().replace("-", "").replace("_", "") in CREDENTIAL_NAMES
        )
        return {
            key: "[redacted]"
            if key.casefold().replace("-", "").replace("_", "") in CREDENTIAL_NAMES
            or (sensitive and key.casefold() == "value")
            else _redact_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    if isinstance(value, str):
        return redact(value)
    return value


def redact(text: str) -> str:
    decoder = json.JSONDecoder()
    chunks = []
    end = 0
    for start in re.finditer(r"[\[{]", text):
        if start.start() < end:
            continue
        try:
            value, consumed = decoder.raw_decode(text[start.start() :])
        except json.JSONDecodeError:
            continue
        cleaned = _redact_json(value)
        chunks.append(text[end : start.start()])
        chunks.append(
            json.dumps(cleaned)
            if cleaned != value
            else start.string[start.start() : start.start() + consumed]
        )
        end = start.start() + consumed
    text = "".join(chunks) + text[end:]
    return CREDENTIAL.sub("[redacted]", text)


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
