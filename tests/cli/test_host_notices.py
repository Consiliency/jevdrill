import json
import subprocess
import sys
import uuid

import pytest


@pytest.mark.parametrize("invalid", [False, True])
def test_installed_notices_strict_stdin(tmp_path, invalid):
    payload = {
        "schema_version": "1",
        "scope": {
            "project_id": str(uuid.uuid4()),
            "workspace_id": str(uuid.uuid4()),
            "producer": "host",
            "operation": "report",
        },
    }
    if invalid:
        payload["scope"]["extra"] = "forbidden"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jevdrill.cli",
            "--storage",
            str(tmp_path / "notices.db"),
            "notices",
        ],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=6,
        check=False,
    )
    assert result.returncode == (2 if invalid else 0)
    assert json.loads(result.stdout) == (
        {"schema_version": "1", "status": "invalid", "code": "invalid_input"}
        if invalid
        else {"schema_version": "1", "notices": []}
    )
    assert result.stderr == ""
