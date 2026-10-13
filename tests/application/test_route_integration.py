import copy
import hashlib
import json
import uuid
from pathlib import Path

import pytest

from jevdrill.application import Application
from jevdrill.contracts import ContractError, canonical_digest, parse_contract
from jevdrill.integrations.jev import JUDGMENT_CANDIDATE_FIELDS
from jevdrill.storage import SQLiteStorage


def inputs():
    return json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]


def policy():
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


def test_local_authority_bypasses_enabled_judgment_through_application(tmp_path):
    value = inputs()
    value["judgment_policy"] = policy()
    value["inventory"]["candidates"][0]["quality_sufficient"] = None
    value["request"]["hard_constraints"]["local_only"] = True

    class Forbidden:
        def judge(self, *args):
            raise AssertionError("forbidden cloud call")

    result = Application(SQLiteStorage(tmp_path / "route.db"), judgments=Forbidden()).route(value)
    assert result["status"] == "no_compatible_plan"


@pytest.mark.parametrize("ceiling,allowed", [("0", False), ("1", True)])
def test_builtin_task_judgment_keeps_verified_spending_bounds(
    tmp_path, monkeypatch, ceiling, allowed
):
    value = inputs()
    value["judgment_policy"] = policy() | {
        "spending_ceiling": {"amount": ceiling, "currency": "USD"},
        "rates": {
            "revision": "synthetic-fixture",
            "currency": "USD",
            "input_rate": "0.000001",
            "output_rate": "0",
            "subscription_multiplier": None,
            "verified_at": "2020-01-01T00:00:00Z",
            "expires_at": "2100-01-01T00:00:00Z",
        },
    }
    value["inventory"]["candidates"][0]["quality_sufficient"] = None
    calls = []
    monkeypatch.setattr(
        "jevdrill.integrations.jev.JudgeCandidate",
        lambda *args, **kwargs: calls.append(True) or True,
    )
    result = Application(SQLiteStorage(tmp_path / "route.db")).route(value)
    assert result["status"] == ("ready" if allowed else "routing_failed")
    assert len(calls) == int(allowed)


@pytest.mark.parametrize("injected", [False, True])
@pytest.mark.parametrize("providers", [[], ["local"], ["local", "typesafeai"]])
def test_judgment_provider_allowlist_is_checked_before_dispatch(
    tmp_path, monkeypatch, injected, providers
):
    value = inputs()
    value["judgment_policy"] = policy()
    value["request"]["hard_constraints"]["allowed_providers"] = providers
    value["inventory"]["candidates"][0].update(
        provider="local", local=True, quality_sufficient=None
    )
    calls = []

    class Judge:
        def judge(self, task, candidates, deadline):
            calls.append(task)
            return {
                "schema_version": "1",
                "function_revision": "JudgeCandidate-v2",
                "model_revision": "jev-latest",
                "candidate_digest": canonical_digest(list(candidates)),
                "judgments": {row["candidate_id"]: True for row in candidates},
                "measurements": [],
            }

    monkeypatch.setattr("jevdrill.integrations.jev.JevAdapter.judge", Judge.judge)
    result = Application(
        SQLiteStorage(tmp_path / "route.db"), judgments=Judge() if injected else None
    ).route(value)
    allowed = not providers or "typesafeai" in providers
    assert len(calls) == int(allowed)
    assert result["status"] == ("ready" if allowed else "no_compatible_plan")


@pytest.mark.parametrize("attachment", [False, True])
def test_bearer_credential_cannot_reach_judgment_or_raw_retention(
    tmp_path, credential_text, credential_may_reject, attachment
):
    value = inputs()
    value["judgment_policy"] = policy()
    value["request"]["task_representation"] = credential_text
    if attachment:
        value["request"]["task_representation"] = "Ordinary task"
        value["request"]["attachment_refs"] = [
            {
                "reference": "public.txt",
                "authorized": True,
                "modality": "document",
                "representation_source": "supplied",
                "text_representation": credential_text,
            }
        ]
    value["settings_layers"] = [{"source": "request", "values": {"retain_raw_tasks": True}}]
    value["inventory"]["candidates"][0]["quality_sufficient"] = None
    calls = []

    class Judge:
        def judge(self, task, candidates, deadline):
            calls.append(task)
            return {
                "schema_version": "1",
                "function_revision": "JudgeCandidate-v2",
                "model_revision": "jev-latest",
                "candidate_digest": canonical_digest(list(candidates)),
                "judgments": {row["candidate_id"]: True for row in candidates},
                "measurements": [],
            }

    app = Application(SQLiteStorage(tmp_path / "route.db"), judgments=Judge())
    try:
        result = app.route(value)
    except ContractError:
        assert credential_may_reject
        assert not calls
        assert b"SYNTHETIC_SENTINEL" not in (tmp_path / "route.db").read_bytes()
        assert not [p for p in (tmp_path / "artifacts").rglob("*") if p.is_file()]
        return
    assert result["status"] == "ready"
    assert calls and "SYNTHETIC_SENTINEL" not in json.dumps(calls)
    artifacts = [p for p in (tmp_path / "artifacts").rglob("*") if p.is_file()]
    assert artifacts
    assert all(b"SYNTHETIC_SENTINEL" not in p.read_bytes() for p in artifacts)


def test_recorded_judgments_are_replayed_without_a_new_call(tmp_path):
    value = inputs()
    value["judgment_policy"] = policy()
    value["inventory"]["candidates"][0]["quality_sufficient"] = None
    calls = []

    class Judge:
        def judge(self, task, candidates, deadline):
            calls.append(candidates)
            return {
                "schema_version": "1",
                "function_revision": "JudgeCandidate-v2",
                "model_revision": "jev-latest",
                "candidate_digest": canonical_digest(list(candidates)),
                "judgments": {row["candidate_id"]: True for row in candidates},
                "measurements": [],
            }

    app = Application(SQLiteStorage(tmp_path / "route.db"), judgments=Judge())
    response = app.route(value)
    assert response["status"] == "ready"
    assert app.route(value) == response
    assert len(calls) == 1
    envelope = value["request"]["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "route",
    }
    assert app.replay(scope, response["details"]["routing_decision_id"]) == response
    assert len(calls) == 1


def test_exact_catalog_frontier_and_admission_enter_application(tmp_path, monkeypatch):
    value = inputs()
    text = "Synthetic required instruction."
    digest = hashlib.sha256(text.encode()).hexdigest()
    resource = {
        "resource_id": "resource",
        "revision": "v1",
        "content_hash": digest,
        "rights": "synthetic-owned",
        "admission": "explicitly_enabled",
        "source_occurrences": ["synthetic"],
        "aliases": [],
        "domain": "test",
        "specialty": "test",
        "task_family": "test",
        "facets": [],
        "benchmark_protocol": None,
        "benchmark_split": None,
        "benchmark_effort": None,
        "instructions": text,
        "conflicts": [],
    }
    value["catalog"] = {
        "schema_version": "1",
        "revision": "fixture",
        "resources": [resource, resource | {"resource_id": "other", "domain": "other"}],
    }
    value["catalog_query"] = {
        "domain": "test",
        "specialty": "test",
        "task_family": "test",
        "facets": [],
        "max_branches": 1,
    }
    value["request"]["active_guidance"] = [
        {
            "resource_id": "resource",
            "revision": "v1",
            "content_hash": digest,
            "role": "required",
            "admission": "explicitly_enabled",
            "authority": "synthetic",
            "task_id": value["request"]["task_id"],
            "token_count": None,
        }
    ]
    import jevdrill.application as module

    entered = []
    original = module.narrow

    def observe(*args):
        result = original(*args)
        entered.append(len(result))
        return result

    monkeypatch.setattr(module, "narrow", observe)
    app = Application(SQLiteStorage(tmp_path / "route.db"))
    assert app.route(value)["status"] == "ready"
    assert entered == [1]
    value["request"]["envelope"].update(request_id=str(uuid.uuid4()), idempotency_key="changed")
    value["catalog"]["resources"][0]["admission"] = "unadmitted"
    assert app.route(value)["status"] == "no_compatible_plan"


def test_retry_requires_recorded_run_and_remaining_attempt_authority(tmp_path):
    value = inputs()
    value["request"]["hard_constraints"]["max_attempts"] = 2
    app = Application(SQLiteStorage(tmp_path / "route.db"))
    decision = app.route(value)
    run_id = str(uuid.uuid4())
    retry = copy.deepcopy(value)
    retry["request"]["envelope"].update(request_id=str(uuid.uuid4()), idempotency_key="retry")
    retry["request"]["retry_context"] = {
        "prior_routing_decision_id": decision["details"]["routing_decision_id"],
        "prior_execution_run_id": run_id,
        "failure_class": "infrastructure",
        "failure_summary": "synthetic",
        "remaining_attempts": 1,
        "remaining_time_ms": 5000,
        "remaining_spend": None,
    }
    retry["inventory"]["candidates"][0]["addresses_failures"] = ["infrastructure"]
    assert app.route(retry)["status"] == "no_compatible_plan"
    envelope = dict(value["request"]["envelope"], operation="report", idempotency_key="event")
    event = {
        "schema_version": "1",
        "event_id": str(uuid.uuid4()),
        "task_id": value["request"]["task_id"],
        "routing_decision_id": decision["details"]["routing_decision_id"],
        "execution_run_id": run_id,
        "source_id": "fixture",
        "source_sequence": 1,
        "occurred_at": "2026-09-28T00:00:00Z",
        "supersedes_event_id": None,
        "payload": {
            "kind": "lifecycle",
            "event_type": "failed",
            "applied_plan_id": None,
            "reason": "synthetic",
        },
    }
    assert app.report({"envelope": envelope, "event": event})["status"] == "accepted"
    retry["request"]["envelope"].update(
        request_id=str(uuid.uuid4()), idempotency_key="verified-retry"
    )
    response = app.route(retry)
    assert response["status"] == "ready"
    assert (
        response["execution_plan"]["predecessor_plan_id"]
        == decision["execution_plan"]["execution_plan_id"]
    )


@pytest.mark.parametrize("answer", [False, True])
def test_suitability_receives_exact_offered_guidance_and_authorized_task_context(
    tmp_path, discovery_inputs, answer
):
    value = inputs()
    value["judgment_policy"] = policy() | {"max_calls": 4, "max_candidates": 4}
    candidate = value["inventory"]["candidates"][0]
    candidate.update(
        quality_sufficient=None,
        evidence_strength="unknown",
        evidence_refs=[],
        execution_token_limits={"input_tokens": 32768, "output_tokens": 1024},
    )
    template = discovery_inputs["catalog"]["resources"][0]
    resources, refs = [], []
    for name in ("required", "first", "second", "unoffered"):
        text = "Authorized instruction for " + name
        resource = template | {
            "resource_id": name,
            "revision": name + "-revision",
            "instructions": text,
            "content_hash": hashlib.sha256(text.encode()).hexdigest(),
            "conflicts": [],
        }
        resources.append(resource)
        refs.append(
            {key: resource[key] for key in ("resource_id", "revision", "content_hash", "admission")}
            | {
                "role": "role-" + name,
                "authority": "synthetic",
                "task_id": value["request"]["task_id"],
                "token_count": None,
            }
        )
    value["catalog"] = {"schema_version": "1", "revision": "fixture", "resources": resources}
    value["request"]["active_guidance"] = refs[:1]
    value["request"]["hard_constraints"]["governing_instruction_refs"] = ["authorized-policy"]
    requirements = [
        {
            "requirement_id": "preserve-inputs",
            "description": "Preserve inputs",
            "evaluator_ref": "synthetic-integrity",
            "source": "user",
        }
    ]
    value["request"]["optimization_objective"]["acceptance_requirements"] = requirements
    candidate["satisfied_requirements"] = ["preserve-inputs"]
    candidate["guidance_options"] = refs[1:3]
    calls = []

    class Judge:
        def judge(self, task, candidates, deadline):
            calls.append((json.loads(task), candidates))
            return {
                "schema_version": "1",
                "function_revision": "JudgeCandidate-v2",
                "model_revision": "jev-latest",
                "candidate_digest": canonical_digest(list(candidates)),
                "judgments": {row["candidate_id"]: answer for row in candidates},
                "measurements": [],
            }

    result = Application(SQLiteStorage(tmp_path / "route.db"), judgments=Judge()).route(value)
    assert result["status"] == ("ready" if answer else "no_compatible_plan")
    if not answer:
        assert len(result["details"]["exclusions"]) == 4
        assert all(
            row["reasons"] == ["quality_unknown_or_insufficient"]
            for row in result["details"]["exclusions"]
        )
    task, offered = calls[0]
    assert task == {
        "task": value["request"]["task_representation"],
        "acceptance": requirements,
        "context": value["request"]["attachment_refs"],
        "governing": ["authorized-policy"],
    }
    assert len(offered) == 4
    assert JUDGMENT_CANDIDATE_FIELDS.isdisjoint(
        {
            "rates",
            "cost",
            "default",
            "source",
            "token_counter_revision",
            "supported_efforts",
            "guidance_options",
            "addresses_failures",
        }
    )
    for row in offered:
        assert set(row) == JUDGMENT_CANDIDATE_FIELDS
        assert row["execution_token_limits"] == candidate["execution_token_limits"]
        selected = row["required_guidance"] + row["optional_guidance"]
        assert row["guidance_instructions"] == [
            next(
                resource["instructions"]
                for resource in resources
                if resource["resource_id"] == ref["resource_id"]
            )
            for ref in selected
        ]
        assert row["quality_sufficient"] is None and row["evidence_refs"] == []
        assert "Authorized instruction for unoffered" not in json.dumps(row)
        selected_ids = {ref["resource_id"] for ref in selected}
        for ref in refs[1:3]:
            if ref["resource_id"] not in selected_ids:
                assert ref["resource_id"] not in json.dumps(row)
                assert ref["revision"] not in json.dumps(row)
                assert ref["content_hash"] not in json.dumps(row)
                assert ref["role"] not in json.dumps(row)
    assert len({tuple(row["guidance_instructions"]) for row in offered}) == 4
    value["request"]["envelope"].update(request_id=str(uuid.uuid4()), idempotency_key="no-options")
    candidate["guidance_options"] = []
    cleared = Application(SQLiteStorage(tmp_path / "cleared.db"), judgments=Judge()).route(value)
    assert cleared["status"] == result["status"]
    assert calls[1][1] == tuple(row for row in offered if not row["optional_guidance"])


def test_legacy_policy_can_replay_immutable_v1_bundle_but_cannot_dispatch(tmp_path):
    value = inputs()
    value["judgment_policy"] = policy() | {"function_revision": "JudgeCandidate-v1"}
    value["inventory"]["candidates"][0]["quality_sufficient"] = None
    decision = Application(SQLiteStorage(tmp_path / "seed.db")).route(inputs())
    scope = {
        "project_id": value["request"]["envelope"]["project_id"],
        "workspace_id": value["request"]["envelope"]["workspace_id"],
        "producer": value["request"]["envelope"]["harness_id"],
        "operation": "route",
    }
    bundle = {
        "schema_version": "1",
        "routing_decision_id": decision["details"]["routing_decision_id"],
        "task_id": value["request"]["task_id"],
        "request_digest": canonical_digest(value),
        "cache_digest": "0" * 64,
        "decision": decision,
        "judgments": {
            "schema_version": "1",
            "function_revision": "JudgeCandidate-v1",
            "model_revision": "jev-latest",
            "candidate_digest": "0" * 64,
            "judgments": {"historical": True},
            "measurements": [],
        },
    }
    assert parse_contract("ReplayBundle", bundle).payload() == bundle
    recovered = {"scope": scope, "bundle": bundle}
    assert parse_contract("RecoveryDecision", recovered).payload() == recovered
    recovery = {
        "schema_version": "1",
        "scope": "synthetic",
        "tasks": {},
        "objectives": {},
        "learning_policy": {},
        "decisions": [recovered],
        "events": [],
        "contexts": [],
        "discoveries": [],
        "artifacts": [],
    }
    assert parse_contract("RecoveryBundle", recovery).payload() == recovery

    class Forbidden:
        def judge(self, *args):
            raise AssertionError("legacy policy dispatched")

    store = SQLiteStorage(tmp_path / "legacy.db")
    store.commit_decision(
        scope,
        value["request"]["envelope"]["idempotency_key"],
        canonical_digest(value),
        bundle,
    )
    app = Application(store, judgments=Forbidden())
    assert app.route(value) == decision
    assert app.replay(scope, bundle["routing_decision_id"]) == decision
    assert store.load_replay(scope, bundle["routing_decision_id"]) == bundle
    value["request"]["envelope"].update(request_id=str(uuid.uuid4()), idempotency_key="new-v1")
    assert app.route(value)["status"] == "routing_failed"
    assert store.load_replay(scope, bundle["routing_decision_id"]) == bundle


@pytest.mark.parametrize("mutation", ["template", "projection", "fields"])
def test_cache_reuses_same_binding_and_invalidates_changed_judgment_template(
    tmp_path, monkeypatch, mutation
):
    from jevdrill.integrations import jev

    value = inputs()
    value["judgment_policy"] = policy()
    value["inventory"]["candidates"][0]["quality_sufficient"] = None
    calls = []

    class Judge:
        def judge(self, task, candidates, deadline):
            calls.append(candidates)
            return {
                "schema_version": "1",
                "function_revision": "JudgeCandidate-v2",
                "model_revision": "jev-latest",
                "candidate_digest": canonical_digest(list(candidates)),
                "judgments": {row["candidate_id"]: True for row in candidates},
                "measurements": [],
            }

    app = Application(SQLiteStorage(tmp_path / "cache.db"), judgments=Judge())
    first = app.route(value)
    assert first["status"] == "ready"
    value["request"]["envelope"].update(
        request_id=str(uuid.uuid4()), idempotency_key="same-template"
    )
    reused = app.route(value)
    assert reused["details"]["reused_decision_id"] == first["details"]["routing_decision_id"]
    assert len(calls) == 1
    if mutation == "template":
        original = jev.candidate_request_shape
        monkeypatch.setattr(
            jev,
            "candidate_request_shape",
            lambda task, candidate: original(task + " amended", candidate),
        )
    elif mutation == "projection":
        monkeypatch.setattr(jev, "JUDGMENT_PROJECTION_VERSION", "synthetic-new-projection")
    else:
        monkeypatch.setattr(
            jev, "JUDGMENT_CANDIDATE_FIELDS", JUDGMENT_CANDIDATE_FIELDS - {"verified_at"}
        )
    value["request"]["envelope"].update(
        request_id=str(uuid.uuid4()), idempotency_key="changed-template"
    )
    changed = app.route(value)
    assert changed["status"] == "ready"
    assert changed["details"]["reused_decision_id"] is None
    assert len(calls) == 2
