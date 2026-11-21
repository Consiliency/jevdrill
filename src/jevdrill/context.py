"""Supplied context only; never follow attachment references or search user files."""

import fnmatch
import functools
import os
import posixpath
import re
import sys
import unicodedata
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from time import monotonic
from typing import Any

from .contracts import ContractError

EXCLUDED_COMPONENTS = frozenset({".env", ".ssh", ".gnupg", "credentials", "id_rsa", "id_ed25519"})
CREDENTIAL_LABEL = r"authorization|api[\s_-]*key|access[\s_-]*token|password|secret"
PRIVATE_KEY_BEGIN = re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----", re.IGNORECASE)
# The rule below is disclosed in docs/sanitization-contract.md; change both together.
# A break is CRLF or one of CR, LF, U+0085, U+2028 and U+2029. Vertical tab, form feed
# and every other whitespace character stay inside their line.
_BREAKS = r"\r\n\x85\u2028\u2029"
_LABEL = re.compile(CREDENTIAL_LABEL, re.IGNORECASE)
_OPERATOR = re.compile(r":|=|<-|->")
_SCHEME = re.compile(
    rf"""(?<![^{_BREAKS}"'])[^\S{_BREAKS}]*(?:bearer|basic)\s+[^\s"',;}}\]]+""", re.IGNORECASE
)
# From the break before an empty or whitespace-only line up to, not including, the break after.
_BLANK_LINE = re.compile(rf"(?>\r\n|[{_BREAKS}])[^\S{_BREAKS}]*(?=[{_BREAKS}])")
_ESCAPE = re.compile(
    r"\\(?:(\\)|x([0-9A-Fa-f]{2})|u([0-9A-Fa-f]{4})|U([0-9A-Fa-f]{8})|([0-7]{1,3}))"
    r"|%([0-9A-Fa-f]{2})|&#[xX]([0-9A-Fa-f]{1,6});|&#([0-9]{1,7});"
)
_REMOVED_CATEGORIES = frozenset({"Cf", "Mn", "Mc", "Me"})
_MAX_DECODES = 4
_REFUSAL = "credential-like material"


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None and monotonic() >= deadline:
        raise TimeoutError("context sanitization deadline exceeded")


@functools.cache
def _removal_table() -> dict[int, None]:
    """Every code point in a removed category, as a deletion table for `str.translate`.

    Built once, on the first text that is not ASCII. It depends only on the Unicode
    database, so it holds nothing about any text.
    """
    return dict.fromkeys(
        code
        for code in range(sys.maxunicode + 1)
        if unicodedata.category(chr(code)) in _REMOVED_CATEGORIES
    )


def _normalize(text: str) -> str:
    if text.isascii():
        return text  # NFKC changes no ASCII character and none is in a removed category.
    # Deleting by table is the per-character category test, without a Python-level loop.
    return unicodedata.normalize("NFKC", text).translate(_removal_table())


def _decoded(match: re.Match[str]) -> str:
    backslash, hex2, hex4, hex8, octal, percent, html_hex, html_decimal = match.groups()
    if backslash is not None:
        return "\\"
    if octal is not None:
        code = int(octal, 8)
    elif html_decimal is not None:
        code = int(html_decimal)
    else:
        code = int(hex2 or hex4 or hex8 or percent or html_hex, 16)
    return chr(code) if code <= 0x10FFFF else match.group()


def _decode(text: str) -> str:
    # One left-to-right pass: a character produced by a replacement is not scanned again.
    return _ESCAPE.sub(_decoded, text)


def _fires(view: str) -> bool:
    if _SCHEME.search(view) or PRIVATE_KEY_BEGIN.search(view):
        return True
    searched_to = -1
    for label in _LABEL.finditer(view):
        end = label.end()
        if end <= searched_to:
            continue  # Its region lies inside the one just searched; this keeps the scan linear.
        blank_line = _BLANK_LINE.search(view, end)
        searched_to = blank_line.start() if blank_line else len(view)
        if _OPERATOR.search(view, end, searched_to):
            return True
    return False


def redact(text: str, deadline: float | None = None) -> str:
    """Return ``text`` itself or refuse it; the text is never rewritten."""
    _check_deadline(deadline)
    if _fires(text):
        raise ContractError(_REFUSAL)
    _check_deadline(deadline)
    view = _normalize(text)
    if _fires(view):
        raise ContractError(_REFUSAL)
    for _ in range(_MAX_DECODES):
        _check_deadline(deadline)
        decoded = _normalize(_decode(view))
        if decoded == view:
            return text
        view = decoded
        _check_deadline(deadline)
        if _fires(view):
            raise ContractError(_REFUSAL)
    _check_deadline(deadline)
    if _normalize(_decode(view)) != view:
        raise ContractError(_REFUSAL)
    return text


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
