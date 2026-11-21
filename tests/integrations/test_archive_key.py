import base64

import pytest

from jevdrill.integrations.archive import archive_key


@pytest.mark.parametrize("module", ["keyring", "base64"])
def test_key_store_child_never_imports_from_the_working_directory(tmp_path, monkeypatch, module):
    planted = base64.urlsafe_b64encode(b"A" * 32).decode()
    (tmp_path / f"{module}.py").write_text(
        f"import sys\nsys.stdout.write({planted!r})\nsys.stdout.flush()\nsys.exit(0)\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert archive_key("review-fixture-identity-that-is-not-stored") != planted.encode()
