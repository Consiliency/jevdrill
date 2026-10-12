from pathlib import Path

import pytest

from jevdrill.context import collect_context, workspace_id


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
def test_authorization_credentials_are_removed_from_task_and_attachments(scheme):
    header = f"Authorization: {scheme} SYNTHETIC_SENTINEL"
    result = collect_context(
        header,
        [{"reference": "public", "authorized": True, "text_representation": header}],
        [],
    )
    assert "SYNTHETIC_SENTINEL" not in str(result)


@pytest.mark.parametrize(
    "credential",
    [
        '{"Authorization": "Bearer SYNTHETIC_SENTINEL"}',
        '{"api_key": "SYNTHETIC_SENTINEL"}',
        "'password': 'SYNTHETIC_SENTINEL with spaces'",
        "Authorization: Digest username=SYNTHETIC_SENTINEL, nonce=SYNTHETIC_SENTINEL",
    ],
)
def test_quoted_credentials_are_removed_from_task_and_attachments(credential):
    result = collect_context(
        credential,
        [{"reference": "public", "authorized": True, "text_representation": credential}],
        [],
    )
    assert "SYNTHETIC_SENTINEL" not in str(result)
