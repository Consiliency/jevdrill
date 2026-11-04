import json
import subprocess
import sys
import time


def invoke(path, command, payload=None, *args):
    return subprocess.run(
        [sys.executable, "-m", "jevdrill.cli", "--storage", str(path), command, *args],
        input=None if payload is None else json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=6,
        check=False,
    )


def test_cold_discover_inspect_replay_delete_commands(tmp_path, discovery_inputs):
    path = tmp_path / "route.db"
    discovery_inputs["catalog"]["resources"] = []
    discovery_inputs["descriptions"] = []
    started = time.monotonic()
    response = invoke(path, "discover", discovery_inputs)
    assert response.returncode == 0 and not response.stderr
    assert time.monotonic() - started < 5
    result = json.loads(response.stdout)
    assert result["status"] == "no_optional_guidance"
    envelope = discovery_inputs["envelope"]
    scope = json.dumps(
        {
            "project_id": envelope["project_id"],
            "workspace_id": envelope["workspace_id"],
            "producer": envelope["harness_id"],
            "operation": "discover",
        }
    )
    replayed = invoke(
        path,
        "inspect-discovery",
        None,
        "--discovery-id",
        result["details"]["discovery_id"],
        "--scope",
        scope,
        "--replay",
    )
    assert replayed.returncode == 0 and json.loads(replayed.stdout) == result
    deleted = invoke(
        path,
        "delete-discovery",
        None,
        "--work-objective-id",
        discovery_inputs["work_objective_id"],
        "--scope",
        scope,
    )
    assert deleted.returncode == 0 and json.loads(deleted.stdout)["status"] == "deleted"
    retry = invoke(path, "discover", discovery_inputs)
    assert retry.returncode == 2 and json.loads(retry.stdout)["status"] == "invalid"


def test_cli_discovery_rejects_unsupported_version_and_raw_duplicate_answers(
    tmp_path, discovery_inputs
):
    discovery_inputs["schema_version"] = "2"
    result = invoke(tmp_path / "route.db", "discover", discovery_inputs)
    assert result.returncode == 2 and json.loads(result.stdout)["status"] == "invalid"
    raw = subprocess.run(
        [sys.executable, "-m", "jevdrill.cli", "discover"],
        input='{"x":true,"x":false}',
        capture_output=True,
        text=True,
        check=False,
    )
    assert raw.returncode == 2 and json.loads(raw.stdout)["status"] == "invalid"
