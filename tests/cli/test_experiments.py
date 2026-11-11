import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "command,identity",
    [("experiment-execution", "comparison_experiment_id"), ("policy-lifecycle", "policy_revision")],
)
def test_real_cli_inspects_lifecycle_without_enabling_execution(tmp_path, command, identity):
    from uuid import uuid4

    payload = {
        "schema_version": "1",
        "scope": {
            "project_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "producer": "fixture",
            "operation": "route",
        },
        "action": "inspect",
        identity: str(uuid4()),
    }
    payload.update(
        {"background": False} if command == "experiment-execution" else {"definition": None}
    )
    result = subprocess.run(
        [sys.executable, "-m", "jevdrill.cli", "--storage", str(tmp_path / "db"), command],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert json.loads(result.stdout) == {
        "schema_version": "1",
        "status": "not_found",
        "reasons": [],
        "record": None,
    }


def test_real_cli_blocks_critical_regression_without_promoting(tmp_path):
    root = Path(__file__).resolve().parents[2]
    fixtures = json.loads((root / "tests/contracts/fixtures/experiment.json").read_text())
    payload = copy.deepcopy(
        next(row["payload"] for row in fixtures if row["id"] == "policy-evaluation-valid")
    )
    payload["cases"][0]["candidate_critical"]["authorization"] = False
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jevdrill.cli",
            "--storage",
            str(tmp_path / "data.sqlite3"),
            "policy",
        ],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assessment = json.loads(result.stdout)
    assert assessment["classification"] == "critical_regression"
    assert assessment["promotion_authorized"] is False


def test_real_cli_lists_experiments_without_enabling_execution(tmp_path):
    from uuid import uuid4

    payload = {
        "schema_version": "1",
        "scope": {
            "project_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "producer": "fixture",
            "operation": "route",
        },
        "idempotency_key": str(uuid4()),
        "action": "inspect",
        "proposal": None,
        "comparison_experiment_id": None,
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jevdrill.cli",
            "--storage",
            str(tmp_path / "data.sqlite3"),
            "experiment",
        ],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    response = json.loads(result.stdout)
    assert response["status"] == "listed"
    assert response["experiments"] == []
    assert response["execution_authorized"] is False
