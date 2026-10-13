from pathlib import Path

import pytest

from jevdrill.context import collect_context, workspace_id
from jevdrill.contracts import ContractError


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


def test_noncredential_json_preserves_context_and_format():
    text = 'Headers: [{"name":"Content-Type", "value":"application/json"}]\nUse basic arithmetic.'
    assert collect_context(text, [], [])["task_representation"] == text


def test_deep_context_fails_with_a_boundary_error():
    with pytest.raises(ContractError, match="nesting"):
        collect_context("[" * 1500 + "0" + "]" * 1500, [], [])


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
