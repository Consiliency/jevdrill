"""JEV-side HOST controls, entered through ``Application.route`` (HOST plan, SL-1).

No request leaves the runner: every test injects a judgment port, so
``Application`` never judges with the real ``JevAdapter`` (it builds one only to
bound candidate size, which renders a request locally and sends nothing), and
no test reads a credential or opens a socket. Each control has a sibling case in
which the guarded condition is absent and the observed outcome differs (a judge
call, an applied policy order, a mismatch row), so the assertion can fail.
"""

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from jevdrill.application import Application
from jevdrill.contracts import canonical_digest
from jevdrill.routing import candidate_fingerprint
from jevdrill.storage import SQLiteStorage

REFRESH_ADVICE = ["Refresh the host-supplied authorized inventory."]


def inputs():
    value = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]
    value["request"]["envelope"].update(request_id=str(uuid4()), idempotency_key=str(uuid4()))
    return value


def judgment_policy():
    return {
        "enabled": True,
        "cloud_allowed": True,
        "max_calls": 2,
        "max_candidates": 2,
        "max_input_tokens": 30000,
        "max_output_tokens": 10,
        "spending_ceiling": None,
        "rates": None,
        "model_revision": "jev-latest",
        "function_revision": "JudgeCandidate-v2",
        "token_counter_revision": "utf8-bytes-upper-bound-v1",
    }


class RecordingJudge:
    """Stand-in judgment port: records each call."""

    model_revision = "jev-latest"

    def __init__(self):
        self.calls = 0

    def judge(self, task, candidates, deadline):
        self.calls += 1
        return {
            "model_revision": "jev-latest",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "judgments": {row["candidate_id"]: True for row in candidates},
        }


class ForbiddenJudge:
    """Stand-in judgment port that fails the test if it is called at all."""

    model_revision = "jev-latest"

    def judge(self, *args):
        raise AssertionError("judgment port called")


@pytest.mark.parametrize("bypass", [True, False])
def test_recursion_bypass_makes_no_judgment_call(tmp_path, bypass):
    """EC-HOST-1 "Prevent recursive routing": a bypassed request is never judged."""
    value = inputs()
    value["judgment_policy"] = judgment_policy()
    value["inventory"]["candidates"][0]["quality_sufficient"] = None
    value["request"]["recursion_bypass"] = bypass
    judge = RecordingJudge()
    Application(SQLiteStorage(tmp_path / "route.db"), judgments=judge).route(value)
    assert judge.calls == (0 if bypass else 1)


@pytest.mark.parametrize("mode", ["dry_run", "main"])
def test_dry_run_is_never_ordered_by_learned_policy(tmp_path, monkeypatch, mode):
    """EC-HOST-1 dry-run clause, ORDERING HALF ONLY: a dry run never reaches learned
    policy ordering. Whether a dry run's terminal report is counted as a completed
    run is not tested here: Consiliency/jevdrill#109."""
    value = inputs()
    value["request"]["execution_mode"] = mode
    candidates = value["inventory"]["candidates"]
    cheaper = candidates[0]
    preferred = deepcopy(cheaper)
    preferred.update(
        candidate_id="preferred", model_id="preferred", resolved_model_revision="preferred-v1"
    )
    preferred["rates"].update(input_rate="0.01", output_rate="0.01")
    candidates.append(preferred)
    # Prepared candidate ids carry the digest of their optional guidance (none here).
    suffix = canonical_digest([])[:12]
    calls = []

    def ordering(scope, group, objective, request_id, task_id):
        # Stand-in for the lifecycle's ordering: an available policy preferring the
        # candidate the router would not otherwise choose. No policy store is built.
        calls.append(group)
        return {
            "status": "ready",
            "policy_revision": "host-test-policy",
            "evidence_digest": "a" * 64,
            "candidate_order": [
                {
                    "candidate_id": f"{row['candidate_id']}:{suffix}",
                    "candidate_fingerprint": candidate_fingerprint(row),
                }
                for row in (preferred, cheaper)
            ],
        }

    app = Application(
        SQLiteStorage(tmp_path / "route.db"),
        judgments=ForbiddenJudge(),
        policy_task_group=lambda request: "host-test-group",
    )
    monkeypatch.setattr(app.policy_lifecycle, "ordering", ordering)
    result = app.route(value)
    assert result["status"] == "ready"
    assert calls == ([] if mode == "dry_run" else ["host-test-group"])
    chosen = cheaper if mode == "dry_run" else preferred
    assert result["execution_plan"]["model_id"] == chosen["model_id"]


@pytest.mark.parametrize("runtime", [["text", "tools"], ["text"]], ids=["mismatch", "match"])
def test_capability_mismatch_carries_supported_refresh_advice(tmp_path, runtime):
    """EC-HOST-2: a capability mismatch carries the supported resolution advice."""
    value = inputs()
    value["request"]["capabilities"]["runtime"] = runtime
    result = Application(SQLiteStorage(tmp_path / "route.db"), judgments=ForbiddenJudge()).route(
        value
    )
    mismatches = result["details"].get("capability_mismatches", [])
    if runtime == ["text"]:
        assert mismatches == []
        return
    assert len(mismatches) == 1
    row = mismatches[0]
    assert row["code"] == "capability_mismatch"
    assert row["declared"] == ["text"] and row["runtime"] == ["text", "tools"]
    assert row["effective"] == ["text"]
    assert row["resolution_advice"] == REFRESH_ADVICE
