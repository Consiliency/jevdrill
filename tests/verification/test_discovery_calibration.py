import copy
import importlib.util
import json
import shutil
import time
from pathlib import Path

import pytest

from jevdrill.contracts import canonical_digest
from jevdrill.evaluation import evaluate_host_artifact

ROOT = Path(__file__).parents[2]
SPEC = importlib.util.spec_from_file_location(
    "discovery_development_checks", ROOT / "scripts/verify_discovery_calibration.py"
)
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


@pytest.fixture(scope="module")
def diagnostic():
    return checks.offline(ROOT)


@pytest.mark.parametrize("durations", [(0.0, 0.1, 0.7, 1.0), (0.001, 0.001, 0.02, 0.003)])
def test_produced_duration_accepts_complete_overhead_and_rejects_omission(durations):
    measurements = dict(
        zip(("discovery", "routing", "execution", "grading"), durations, strict=True)
    )
    measurements.update(
        total=checks.objective_duration(*durations),
        raw_cost=0.1,
        tokens={key: {"value": 1} for key in ("input", "output", "cached_input")},
    )
    assert checks.telemetry_errors(measurements) == []
    measurements["total"] -= durations[-1]
    assert checks.telemetry_errors(measurements) == ["omitted overhead"]


def test_actual_offline_navigation_and_task_configuration_reject_unsuitable_controls(diagnostic):
    assert diagnostic["status"] == "passed"
    assert all(diagnostic["controls"].values())
    assert diagnostic["produced_if_gates"] == []
    assert len(diagnostic["cases"]) == 12
    chosen = {row["decision"]["execution_plan"]["model_id"] for row in diagnostic["cases"]}
    assert chosen == {"model-cheap", "model-fast"}
    assert all(
        row["scripted_judgment_calls"] > 0 and row["actual_outcome"] is None
        for row in diagnostic["cases"]
    )


def test_software_only_cannot_become_authorized_empirical_study(diagnostic):
    assert checks.validate_study(diagnostic, checks.read_protocol()) == [
        "new study authority missing"
    ]
    assert checks.validate_study(diagnostic, checks.read_protocol(), {"enabled": True})


@pytest.fixture
def synthetic_study(diagnostic):
    # A mutation-test structure, never a native/runtime/study acceptance artifact.
    protocol = checks.read_protocol()
    authority = {
        "enabled": True,
        "max_candidate_calls": 60,
        "max_judgment_calls": 768,
        "total_spend_microusd": 26_000_000,
        "whole_study_deadline_ms": 2_400_000,
    }
    rows = []
    for actual, case in zip(diagnostic["cases"], protocol["cases"], strict=True):
        plan = actual["decision"]["execution_plan"]
        arm = {
            "independent_grader_revision": protocol["evaluator_revision"],
            "rubric_revision": protocol["rubric_revision"],
            "related_group": case["related_group"],
            "split": "development",
            "execution_origin": "bounded_adapter_provider_receipt",
            "output": case["reference_artifact"],
            "output_digest": canonical_digest(case["reference_artifact"]),
            "critical_checks": evaluate_host_artifact(
                case["task_family"], case["expected"], case["reference_artifact"]
            ),
            "reservation_receipt_digest": "fixture-only",
            "provider_receipt_digest": "fixture-only",
            "configuration_digest": canonical_digest(plan),
            "measurements": {
                "discovery": 1,
                "routing": 1,
                "execution": 1,
                "grading": 1,
                "total": 4,
                "raw_cost": 0.1,
                "tokens": None,
            },
        }
        names = {
            name for name, applicable in case["baseline_applicability"].items() if applicable
        } | {"actual_discovery_route"}
        rows.append(
            {
                "case_id": case["id"],
                "discovery": actual["discovery"],
                "decision": actual["decision"],
                "routing_decision_id": actual["decision"]["details"]["routing_decision_id"],
                "applied_configuration_digest": canonical_digest(plan),
                "arms": {name: copy.deepcopy(arm) for name in names},
                "exposure_receipt_digest": "fixture-only",
                "judgment_configuration_digest": "fixture-only",
                "judgment_origin": "bounded_model_adapter",
            }
        )
    study = {
        "schema_version": 1,
        "origin": "authorized_recorded_development",
        "protocol_digest": canonical_digest(protocol),
        "authority_digest": canonical_digest(authority),
        "promotion_authorized": False,
        "identities_blinded": True,
        "holdouts_opened": False,
        "cases": rows,
        "uncertainty_by_family": {"fixture": "unknown"},
        "reservation_ledger": {
            "authority_digest": canonical_digest(authority),
            "candidate_attempts": 60,
            "judgment_attempts": 768,
            "reserved_microusd": 26_000_000,
            "observed_duration_ms": 100,
            "uncertain_refunded": False,
        },
    }
    return study, protocol, authority


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "origin",
        "authority",
        "membership",
        "lineage",
        "configuration",
        "baseline",
        "grader",
        "output",
        "overhead",
        "unknown",
        "scripted",
        "reservation",
        "refund",
        "holdout",
        "unblinded",
        "executor_only",
    ],
)
def test_linked_study_rejects_provenance_configuration_overhead_and_executor_substitutes(
    synthetic_study, fault
):
    study, protocol, authority = synthetic_study
    row = study["cases"][0]
    arm = row["arms"]["actual_discovery_route"]
    if fault == "origin":
        study["origin"] = "software_only_scripted_observer"
    elif fault == "authority":
        study["authority_digest"] = "wrong"
    elif fault == "membership":
        study["cases"].pop()
    elif fault == "lineage":
        row["decision"]["details"]["discovery_ref"] = None
    elif fault == "configuration":
        row["applied_configuration_digest"] = "wrong"
    elif fault == "baseline":
        row["arms"].pop("no_guidance")
    elif fault == "grader":
        arm["independent_grader_revision"] = "candidate-self-report"
    elif fault == "output":
        arm["output_digest"] = "wrong"
    elif fault == "overhead":
        arm["measurements"]["total"] = 0
    elif fault == "unknown":
        arm["measurements"]["raw_cost"] = None
    elif fault == "scripted":
        row["judgment_origin"] = "scripted"
    elif fault == "reservation":
        study["reservation_ledger"]["judgment_attempts"] += 1
    elif fault == "refund":
        study["reservation_ledger"]["uncertain_refunded"] = True
    elif fault == "holdout":
        arm["split"] = "release_holdout"
    elif fault == "unblinded":
        study["identities_blinded"] = False
    elif fault == "executor_only":
        row.pop("discovery")
    # Even the unchanged synthetic structure has no immutable runtime artifacts,
    # bounded trusted grant or calibrated independent group evidence.
    assert checks.validate_study(study, protocol, authority)


@pytest.mark.parametrize(
    "field,value",
    [
        ("quality_floor", -1),
        ("confidence", float("nan")),
        ("minimum_pairs", True),
        ("practical_equivalence", 2),
    ],
)
def test_calibration_rejects_invalid_non_null_values(field, value):
    protocol = copy.deepcopy(checks.read_protocol())
    settings = {
        "quality_floor": 0.8,
        "maximum_quality_loss": 0.1,
        "practical_equivalence": 0.1,
        "minimum_pairs": 4,
        "confidence": 0.95,
        "revision": "synthetic",
        "frozen_at": "2026-10-01T00:00:00Z",
    }
    protocol["calibration"] = {
        family: copy.deepcopy(settings) for family in protocol["calibration"]
    }
    protocol["calibration"]["implementation"][field] = value
    assert "invalid preregistered calibration: implementation" in checks.calibration_errors(
        protocol
    )


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, None])
def test_required_telemetry_cannot_be_negative_nonfinite_boolean_or_unknown(value):
    measured = {
        "discovery": 1,
        "routing": 1,
        "execution": 1,
        "grading": 1,
        "total": 4,
        "raw_cost": value,
        "tokens": {key: {"value": 0} for key in ("input", "output", "cached_input")},
    }
    assert checks.telemetry_errors(measured)


def test_critical_regression_is_observed_but_missing_outcome_remains_unknown():
    protocol = checks.read_protocol()
    actual = {
        "quality": 0,
        "critical_checks": {"critical": False},
        "measurements": {"raw_cost": 0.1, "total": 1},
    }
    baseline = {
        "quality": 1,
        "critical_checks": {"critical": True},
        "measurements": {"raw_cost": 0.1, "total": 1},
    }
    rows = [
        {
            "family": "review",
            "related_group": "one",
            "arms": {"actual_discovery_route": actual, "fixed_default": baseline},
        }
    ]
    assert any(
        "additional measured critical failure" in error
        for error in checks.paired_analysis(rows, protocol)[1]
    )
    actual.update(quality=None, critical_checks={})
    errors = checks.paired_analysis(rows, protocol)[1]
    assert "paired outcome unknown" in errors
    assert not any("additional measured critical failure" in error for error in errors)


def test_disabled_preview_cannot_create_study_or_lookup_credentials(tmp_path):
    authority = checks.authority_preview(ROOT)
    path = tmp_path / "disabled.json"
    path.write_text(json.dumps(authority))

    def forbidden():
        pytest.fail("credential callback must not run without a new grant")

    with pytest.raises(ValueError, match="trusted study authority"):
        checks.run_authorized_study(
            path, ROOT, candidate_credential=forbidden, judgment_credential=forbidden
        )


def test_recorded_database_uri_encodes_delimiters_and_closes_reader(tmp_path):
    import sqlite3

    path = tmp_path / "records # % &.db"
    database = sqlite3.connect(path)
    database.execute("CREATE TABLE records (identity TEXT, payload TEXT)")
    database.execute("INSERT INTO records VALUES (?,?)", ("observed", '{"known":1}'))
    database.commit()
    database.close()
    assert checks.database_payloads(path, "records", "identity", "payload") == {
        "observed": {"known": 1}
    }
    path.rename(path.with_name("reader-closed.db"))


@pytest.mark.parametrize(
    "case_index,fault",
    [
        (0, None),
        (3, None),
        (3, "omitted"),
        (3, "substituted"),
        (3, "extra"),
        (3, "optional"),
        (3, "no_guidance"),
        (3, "fixed_default"),
        (3, "cheapest_feasible"),
    ],
)
def test_guarded_driver_records_five_distinct_arms_with_loopback_and_explicit_fixture_runtime(
    tmp_path, monkeypatch, case_index, fault
):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from jevdrill.integrations import development, experiments

    protocol = copy.deepcopy(checks.read_protocol())
    protocol["cases"] = [protocol["cases"][case_index]]
    for name in ("discovery.json", "route-application.json"):
        destination = tmp_path / "tests/contracts/fixtures" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "tests/contracts/fixtures" / name, destination)
    monkeypatch.setattr(checks, "read_protocol", lambda root=ROOT: copy.deepcopy(protocol))
    original_preview = checks.authority_preview
    expires_at = (
        checks.datetime.fromtimestamp(time.time() + 3600, checks.UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )

    def synthetic_authority(root=ROOT):
        return original_preview(root) | {
            "authorization_revision": "synthetic-loopback-only",
            "study_id": "synthetic-loopback-only",
            "expires_at": expires_at,
        }

    monkeypatch.setattr(checks, "authority_preview", synthetic_authority)
    state = {"candidate_calls": 0, "judgment_calls": 0, "prompts": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path.endswith("systemone"):
                state["judgment_calls"] += 1
                body = {
                    "model": "jev-1.13.0",
                    "answers": {"result": {"type": "noul", "noul": 0.9}},
                    "usage": {"input_tokens": 100, "output_tokens": 1},
                }
            else:
                state["candidate_calls"] += 1
                state["prompts"].append(request["messages"])
                body = {
                    "id": "synthetic",
                    "model": request["model"],
                    "object": "chat.completion",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": protocol["cases"][0]["reference_program"],
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
                }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/v1"
    original_judge, original_runner = development.DevelopmentJudge, development.DevelopmentRunner
    original_grader = development.IndependentDevelopmentGrader

    def local_judge(*args, **kwargs):
        return original_judge(*args, **kwargs, base_url=url)

    def local_runner(*args, **kwargs):
        runner = original_runner(*args, **kwargs, base_url=url)
        runner._runtime = lambda: None
        return runner

    class FixtureContainer(experiments.RestrictedContainerRunner):
        def evaluate(self, source, inputs, deadline, **kwargs):
            return {
                "status": "completed",
                "answers": protocol["cases"][0]["expected"]["results"],
                "inputs_unchanged": True,
            }

        def cleanup(self, run_id):
            pass

    class FixtureGrader(original_grader):
        def grade(self, key, outputs):
            from types import SimpleNamespace

            with monkeypatch.context() as context:
                context.setattr(development, "sys", SimpleNamespace(platform="linux"))
                return super().grade(key, outputs)

    monkeypatch.setattr(development, "DevelopmentJudge", local_judge)
    monkeypatch.setattr(development, "DevelopmentRunner", local_runner)
    monkeypatch.setattr(experiments, "RestrictedContainerRunner", FixtureContainer)
    monkeypatch.setattr(development, "IndependentDevelopmentGrader", FixtureGrader)
    if fault:
        original_route = checks.Application.route

        def alter_guidance(app, payload):
            arm = (
                payload.get("request", {})
                .get("envelope", {})
                .get("idempotency_key", "")
                .split(":")[-1]
            )
            if arm == (
                fault
                if fault in {"no_guidance", "fixed_default", "cheapest_feasible"}
                else "simple_retrieval"
            ):
                payload = copy.deepcopy(payload)
                if fault == "omitted":
                    payload["request"]["active_guidance"] = []
                elif fault == "optional":
                    resource = payload["catalog"]["resources"][1]
                    extra = checks.reference(resource) | {
                        "role": "unexpected-optional",
                        "admission": resource["admission"],
                        "authority": "public-development-explicit-admission",
                        "task_id": payload["request"]["task_id"],
                        "token_count": None,
                    }
                    for candidate in payload["inventory"]["candidates"]:
                        candidate.update(guidance_options=[extra], quality_sufficient=None)
                else:
                    resource = payload["catalog"]["resources"][1]
                    ref = checks.reference(resource) | {
                        "role": "unexpected-required",
                        "admission": resource["admission"],
                        "authority": "public-development-explicit-admission",
                        "task_id": payload["request"]["task_id"],
                        "token_count": None,
                    }
                    if fault == "extra":
                        payload["request"]["active_guidance"].append(ref)
                    else:
                        payload["request"]["active_guidance"] = [ref]
            return original_route(app, payload)

        monkeypatch.setattr(checks.Application, "route", alter_guidance)
        if fault == "optional":
            original_prepare = checks.Application._prepare

            def require_optional(app, request, *args):
                prepared = original_prepare(app, request, *args)
                if request["envelope"]["idempotency_key"].endswith(":simple_retrieval"):
                    return [row for row in prepared if row["optional_guidance"]]
                return prepared

            monkeypatch.setattr(checks.Application, "_prepare", require_optional)
    authority = checks.authority_preview(tmp_path) | {"enabled": True}
    path = tmp_path / "new-synthetic-grant.json"
    path.write_text(json.dumps(authority))
    try:
        study = checks.run_authorized_study(
            path,
            tmp_path,
            candidate_credential=lambda: "synthetic",
            judgment_credential=lambda: "synthetic",
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
    assert study["failure"] is None, study
    assert len(study["cases"]) == 1
    assert len(study["cases"][0]["arms"]) == state["candidate_calls"] == 5
    assert study["reservation_ledger"]["candidate_attempts"] == 5
    assert study["reservation_ledger"]["judgment_attempts"] == state["judgment_calls"]
    assert study["reservation_ledger"]["reserved_microusd"] >= 5 * 104963
    errors = checks.validate_study(study, protocol, authority, tmp_path)
    baseline_error = "baseline does not implement its preregistered selection condition"
    expected_errors = {
        "Q12/Q13 family-specific empirical calibration unresolved",
        "execution endpoint/configuration differs from trusted official adapter",
        "navigation endpoint/configuration differs from trusted official adapter",
    }
    if fault:
        expected_errors.add(baseline_error)
    assert set(errors) == expected_errors
    case = protocol["cases"][0]
    directory = tmp_path / "evidence/EXPERIMENT/studies" / authority["study_id"]
    retrieval = study["cases"][0]["arms"]["simple_retrieval"]
    evidence = checks.read_artifact(directory, retrieval["artifact"])
    plan = evidence["decision"]["execution_plan"]
    selected = plan["required_guidance"] + plan["optional_guidance"]
    expected_ids = [
        resource["id"] for resource in protocol["resources"] if resource["id"] in case["objective"]
    ][:2]
    if fault == "substituted":
        assert [ref["resource_id"] for ref in selected] == [protocol["resources"][1]["id"]]
    elif fault == "extra":
        assert [ref["resource_id"] for ref in selected] == expected_ids + [
            protocol["resources"][1]["id"]
        ]
    elif fault == "optional":
        assert [ref["resource_id"] for ref in plan["required_guidance"]] == expected_ids
        assert [ref["resource_id"] for ref in plan["optional_guidance"]] == [
            protocol["resources"][1]["id"]
        ]
    else:
        assert [ref["resource_id"] for ref in selected] == (
            [] if fault == "omitted" else expected_ids
        )
    if not fault:
        assert bool(retrieval["judgment_call_ids"]) == bool(expected_ids)
        assert study["cases"][0]["arms"]["no_guidance"]["judgment_call_ids"] == []
        assert study["cases"][0]["arms"]["fixed_default"]["judgment_call_ids"] == []
        assert study["cases"][0]["arms"]["cheapest_feasible"]["judgment_call_ids"] == []
    if selected and not fault:
        instructions = [
            resource["instructions"]
            for resource in protocol["resources"]
            if resource["id"] in expected_ids
        ]
        assert any(
            all(text in json.dumps(prompt) for text in instructions) for prompt in state["prompts"]
        )
    for arm in study["cases"][0]["arms"].values():
        count = len(arm["judgment_call_ids"])
        assert arm["measurements"]["tokens"] == {
            "input": {"value": 100 + 100 * count},
            "output": {"value": 10 + count},
            "cached_input": {"missing_reason": "not_reported"},
        }
    if case_index == 0 and fault is None:
        for name in ("discovery.json", "route-application.json"):
            fixture = tmp_path / "tests/contracts/fixtures" / name
            original = fixture.read_text()
            fixture.write_text(original + "\n")
            assert set(checks.validate_study(study, protocol, authority, tmp_path)) == (
                expected_errors
                | {
                    "study source changed",
                    "immutable exposure/source/grant mismatch",
                    "new trusted study authority differs from bounded preview",
                }
            )
            fixture.write_text(original)
        assert set(checks.validate_study(study, protocol, authority, tmp_path)) == expected_errors
    arm = study["cases"][0]["arms"]["actual_discovery_route"]
    arm["configuration_digest"] = "forged"
    assert checks.validate_study(study, protocol, authority, tmp_path) != [
        "Q12/Q13 family-specific empirical calibration unresolved"
    ]


def test_study_validator_rejects_changed_judgment_template_configuration(tmp_path, monkeypatch):
    from jevdrill.integrations import jev
    from jevdrill.integrations.development import DevelopmentJudge

    authority = checks.authority_preview() | {"enabled": True}
    frozen = {"deadline_ms": int(time.time() * 1000) + 10000}
    judge = DevelopmentJudge(
        tmp_path / "official-profile.db",
        scope=authority["scope"] | {"operation": "route"},
        authorization_revision=authority["authorization_revision"],
        max_calls=authority["max_judgment_calls"],
        total_spend_microusd=authority["judgment_spend_microusd"],
        deadline_ms=frozen["deadline_ms"],
        credential=lambda: pytest.fail("offline profile check requested credentials"),
        authorize=lambda _: True,
    )
    artifacts = {
        "exposure": frozen,
        "worker": {},
        "controller": {},
        "judgments": {"revision": judge.revision},
        "lineage": {},
    }
    study = {"study_id": authority["study_id"], "artifacts": {key: key for key in artifacts}}
    monkeypatch.setattr(checks, "read_artifact", lambda directory, name: artifacts[name])
    error = "navigation endpoint/configuration differs from trusted official adapter"
    original_errors = checks.validate_study(study, checks.read_protocol(), authority)
    assert "malformed or incomplete linked study" in original_errors
    assert error not in original_errors
    original = jev.candidate_request_shape
    monkeypatch.setattr(
        jev,
        "candidate_request_shape",
        lambda task, candidate: original(task + " amended", candidate),
    )
    changed_errors = checks.validate_study(study, checks.read_protocol(), authority)
    assert set(changed_errors) == set(original_errors) | {error}


@pytest.mark.parametrize("judgment_output", [10, 0, None])
def test_objective_tokens_maps_navigation_counters_without_inventing_cached_usage(judgment_output):
    def measurement(name, value):
        return {"metric_id": name, "measurement_value": {"kind": "known", "value": value}}

    candidate = [
        measurement("input_tokens", 50),
        measurement("output_tokens", 5),
        measurement("cached_input_tokens", 2),
    ]
    judgment = [measurement("routing_input_tokens", 100)]
    judgment.append(
        measurement("routing_output_tokens", judgment_output)
        if judgment_output is not None
        else {
            "metric_id": "routing_output_tokens",
            "measurement_value": {"kind": "unknown", "reason": "not_reported"},
        }
    )
    assert checks.objective_tokens(candidate, [judgment]) == {
        "input": {"value": 150},
        "output": {"value": 5 + judgment_output}
        if judgment_output is not None
        else {"missing_reason": "not_reported"},
        "cached_input": {"missing_reason": "not_reported"},
    }
