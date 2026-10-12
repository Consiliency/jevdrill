import copy
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import pytest

from jevdrill.contracts import ContractError, canonical_digest
from jevdrill.experiments import Experiments
from jevdrill.integrations.development import DevelopmentModel, DevelopmentRunner
from jevdrill.integrations.experiments import RestrictedContainerRunner
from jevdrill.storage import SQLiteStorage
from tests.experiments.test_execution import enabled_settings, seed_task
from tests.experiments.test_execution import setup as setup  # noqa: PLC0414 -- pytest fixture


@pytest.fixture
def provider():
    observed = {
        "requests": [],
        "status": 200,
        "delay": 0,
        "body": {
            "id": "synthetic",
            "model": "synthetic-local",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "answer"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
        },
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            observed["requests"].append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            time.sleep(observed["delay"])
            self.send_response(observed["status"])
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                response = copy.deepcopy(observed["body"])
                if response.get("model") == "synthetic-local":
                    response["model"] = observed["requests"][-1]["model"]
                self.wfile.write(json.dumps(response).encode())
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", observed
    server.shutdown()
    server.server_close()
    thread.join()


class Container(RestrictedContainerRunner):
    def __init__(self):
        super().__init__("sha256:" + "1" * 64)
        self.cleanups = []
        self.cleanup_fails = False

    def evaluate(self, source, inputs, deadline, *, run_id=None, custody_fd=None):
        return {"status": "completed", "answers": [3], "inputs_unchanged": True}

    def cleanup(self, run_id):
        self.cleanups.append(run_id)
        if self.cleanup_fails:
            raise ContractError("fixture cleanup failed")


@pytest.fixture
def development(tmp_path, setup, provider):
    _, request, authority, _, now, proposal = setup
    url, observed = provider
    experiment = proposal["proposal"]["experiment"]
    case = {
        "prompt": "Define solve(a, b) returning their sum.",
        "inputs": [[1, 2]],
        "expected_answers": [3],
        "evaluator_ref": "development-js-v1",
        "rubric_revision": "1",
    }
    experiment.update(
        context_ref="sum-v1",
        context_hash=canonical_digest(case),
        evaluator_ref=case["evaluator_ref"],
        rubric_revision=case["rubric_revision"],
    )
    models = {}
    for index, plan in enumerate(experiment["candidate_plans"]):
        model = f"development-fixture-{index}"
        plan.update(
            model_id=model,
            resolved_model_revision=model,
            provider="openai",
            access_route="baml_development",
            harness_id="jevdrill",
            execution_target_id="linux_worker",
            native_effort={"kind": "provider_default"},
            required_guidance=[],
            optional_guidance=[],
            guidance_action="none",
            required_capabilities=[],
        )
        models[model] = DevelopmentModel(
            model, 1000, 32, "1", "2", "fixture-prices-v1", 0, 2_000_000
        )
    container = (
        RestrictedContainerRunner(os.environ["JEVDRILL_DEVELOPMENT_IMAGE"])
        if "JEVDRILL_DEVELOPMENT_IMAGE" in os.environ
        else Container()
    )
    experiment["isolation_ref"] = container.image_id
    authority.update(
        local_only=False,
        allowed_providers=["openai"],
        allowed_harnesses=["jevdrill"],
        allowed_isolation_refs=[container.image_id],
    )
    observed["body"]["choices"][0]["message"]["content"] = "function solve(a, b) { return a + b; }"
    service = Experiments(
        SQLiteStorage(tmp_path / "controller.db"),
        lambda _: authority,
        clock=lambda: now[0],
        settings=enabled_settings,
    )
    seed_task(service.storage, request["scope"], experiment["task_id"])
    service.handle(proposal)
    runner = DevelopmentRunner(
        tmp_path / "worker.db",
        models=models,
        cases={"sum-v1": case},
        container=container,
        credential=lambda: "synthetic-secret",
        authorize=lambda record: service.authorize_dispatch(request["scope"], record),
        base_url=url,
        clock=lambda: now[0],
    )
    if isinstance(container, Container):
        runner._runtime = lambda: None
    service.runner = runner
    return service, runner, request, proposal, authority, now, observed


def dispatch(development):
    service, _, request, _, _, _, observed = development
    admitted = service.execute(request)
    assert admitted["status"] == "recorded", admitted
    assert admitted["record"]["reserved_microusd"] == 2128
    started = service.execute(request | {"action": "advance"})
    assert started["record"]["execution_status"] == "running", started
    assert observed["requests"] == []
    return started["record"]


def five_arm_dispatch(development):
    service, _, request, proposal, authority, _, _ = development
    experiment = proposal["proposal"]["experiment"]
    experiment["comparison_experiment_id"] = str(uuid4())
    template = experiment["candidate_plans"][0]
    experiment["candidate_plans"] = [copy.deepcopy(template) for _ in range(5)]
    for plan in experiment["candidate_plans"]:
        plan["execution_plan_id"] = str(uuid4())
    experiment["limits"]["max_candidates"] = authority["limits"]["max_candidates"] = 5
    proposal["idempotency_key"] = str(uuid4())
    service.handle(proposal)
    request["comparison_experiment_id"] = experiment["comparison_experiment_id"]
    admitted = service.execute(request)
    assert admitted["record"]["reserved_microusd"] == 5320
    assert admitted["record"]["deadline_ms"] - admitted["record"]["admitted_at_ms"] == 120000
    return service.execute(request | {"action": "advance"})["record"]


def test_five_arm_comparison_reserves_once_and_survives_restart_without_redispatch(development):
    service, runner, request, _, _, _, observed = development
    record = five_arm_dispatch(development)
    assert runner.run(record)["host_status"] == "completed"
    terminal = service.execute(request | {"action": "advance"})["record"]
    assert terminal["reserved_microusd"] == 5320
    assert len(terminal["receipt"]["candidates"]) == len(observed["requests"]) == 5
    assert runner.run(record)["host_status"] == "completed"
    assert len(observed["requests"]) == 5


def test_five_arm_cancellation_during_third_request_prevents_fourth_and_recovery_retry(development):
    service, runner, request, _, _, _, observed = development
    record = five_arm_dispatch(development)
    observed["delay"] = 0.15
    with ThreadPoolExecutor() as executor:
        running = executor.submit(runner.run, record)
        deadline = time.monotonic() + 5
        while len(observed["requests"]) < 3 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(observed["requests"]) == 3
        service.execute(request | {"action": "cancel"})
        running.result(timeout=5)
    recovered = service.execute(request | {"action": "advance"})["record"]
    assert recovered["execution_status"] == "canceled"
    assert recovered["reserved_microusd"] == 5320
    assert recovered["receipt"]["cleanup_verified"] is True
    assert runner.run(record)["host_status"] == "canceled"
    assert len(observed["requests"]) == 3


def test_development_pair_uses_actual_baml_and_persistent_receipts(development):
    service, runner, request, _, _, _, observed = development
    record = dispatch(development)
    result = runner.run(record)
    assert result["host_status"] == "completed", result
    assert result["cleanup_verified"] is True
    assert all(
        c["acceptance_checks"] == {"answers_match": True, "inputs_unchanged": True}
        for c in result["candidates"]
    )
    assert len(observed["requests"]) == 2
    for wire in observed["requests"]:
        assert wire["n"] == 1 and wire["store"] is False and wire["max_completion_tokens"] == 32
        assert set(wire) == {
            "model",
            "messages",
            "n",
            "store",
            "service_tier",
            "max_completion_tokens",
        }
    assert runner.run(record) == result
    assert runner.poll(record) == result
    assert len(observed["requests"]) == 2
    assert (
        service.execute(request | {"action": "advance"})["record"]["execution_status"]
        == "completed"
    )
    with sqlite3.connect(runner.path) as db:
        serialized = db.execute("SELECT payload FROM development_runs").fetchone()[0]
    assert "synthetic-secret" not in serialized
    assert len(json.loads(serialized)["observations"]) == 2
    assert all(
        row["observed_model"] == row["requested_model"]
        for row in json.loads(serialized)["observations"]
    )
    metrics = {m["metric_id"]: m for m in result["candidates"][0]["measurements"]}
    assert metrics["raw_token_cost"]["measurement_value"]["value"] == 0.00012
    assert metrics["input_tokens"]["source"] == "provider"
    assert metrics["completion_time_ms"]["source"] == "direct"


@pytest.mark.parametrize("status,body", [(429, {}), (500, {}), (200, {"invalid": True})])
def test_development_provider_failures_never_retry(development, status, body):
    _, runner, _, _, _, _, observed = development
    record = dispatch(development)
    observed.update(status=status, body=body)
    assert runner.run(record)["host_status"] == "failed"
    runner.run(record)
    assert len(observed["requests"]) == 1


def test_development_cancel_before_start_survives_restart(development):
    service, runner, request, proposal, _, _, observed = development
    record = service.execute(request)["record"]
    assert runner.cancel(record)["host_status"] == "canceled"
    restarted = copy.copy(runner)
    assert restarted.start(proposal["proposal"]["experiment"], record)["host_status"] == "canceled"
    restarted.run(record)
    assert observed["requests"] == []


@pytest.mark.parametrize("change", ["expired", "authority", "profile", "case", "deleted"])
def test_development_worker_rechecks_frozen_inputs_and_authority(development, change):
    service, runner, request, proposal, authority, now, observed = development
    record = dispatch(development)
    if change == "expired":
        now[0] = record["deadline_ms"]
    elif change == "authority":
        authority["enabled"] = False
    elif change == "profile":
        name = next(iter(runner.models))
        runner.models[name] = replace(runner.models[name], rate_revision="changed")
    elif change == "case":
        runner.cases["sum-v1"]["prompt"] = "changed"
    else:
        service.storage.delete_task(request["scope"], proposal["proposal"]["experiment"]["task_id"])
    assert runner.run(record)["host_status"] == "failed"
    assert observed["requests"] == []


def test_development_recovery_never_repeats_uncertain_call(development, monkeypatch):
    _, runner, _, _, _, _, observed = development
    record = dispatch(development)
    original = runner._complete

    def interrupted(*args):
        original(*args)
        raise SystemExit("simulated lost worker result")

    monkeypatch.setattr(runner, "_complete", interrupted)
    with pytest.raises(SystemExit):
        runner.run(record)
    restarted = copy.copy(runner)
    assert restarted.poll(record)["host_status"] == "failed"
    assert restarted.run(record)["host_status"] == "failed"
    assert len(observed["requests"]) == 1


def test_development_cancel_inflight_waits_and_prevents_second_call(development):
    _, runner, _, _, _, _, observed = development
    record = dispatch(development)
    observed["delay"] = 0.3
    with ThreadPoolExecutor() as pool:
        future = pool.submit(runner.run, record)
        end = time.monotonic() + 3
        while not observed["requests"] and time.monotonic() < end:
            time.sleep(0.005)
        assert observed["requests"]
        receipt = runner.cancel(record)
        assert receipt["host_status"] == "running" and not receipt["cleanup_verified"]
        assert future.result()["host_status"] == "canceled"
    assert len(observed["requests"]) == 1


def test_development_two_workers_cannot_dispatch_twice(development):
    _, runner, _, _, _, _, observed = development
    record = dispatch(development)
    observed["delay"] = 0.1
    barrier = threading.Barrier(2)

    def work():
        barrier.wait()
        try:
            return runner.run(record)
        except ContractError as error:
            return str(error)

    with ThreadPoolExecutor() as pool:
        results = list(pool.map(lambda _: work(), range(2)))
    assert "development_worker_busy" in results
    assert len(observed["requests"]) == 2


def test_development_cleanup_failure_holds_slot(development):
    _, runner, _, _, _, now, observed = development
    record = dispatch(development)
    runner.container.cleanup_fails = True
    assert not runner.run(record)["cleanup_verified"]
    assert not runner.poll(record)["cleanup_verified"]
    now[0] = record["deadline_ms"]
    with pytest.raises(ContractError, match="cleanup"):
        runner.poll(record)
    runner.container.cleanup_fails = False
    receipt = runner.poll(record)
    assert receipt["cleanup_verified"] and receipt["host_status"] == "failed"
    assert len(observed["requests"]) == 2


@pytest.mark.parametrize(
    "field,value",
    [("input_rate", "NaN"), ("input_rate", "-1"), ("expires_at_ms", 1), ("input_limit", 0)],
)
def test_development_unverified_profiles_fail_before_dispatch(development, field, value):
    service, runner, request, _, _, _, observed = development
    name = next(iter(runner.models))
    runner.models[name] = replace(runner.models[name], **{field: value})
    assert service.execute(request)["status"] == "denied"
    assert observed["requests"] == []


def test_development_missing_usage_stays_unknown(development):
    _, runner, _, _, _, _, observed = development
    record = dispatch(development)
    del observed["body"]["usage"]
    receipt = runner.run(record)
    assert receipt["host_status"] == "completed"
    metric = next(
        m for m in receipt["candidates"][0]["measurements"] if m["metric_id"] == "raw_token_cost"
    )
    assert metric["measurement_value"] == {"kind": "unknown", "reason": "not_reported"}


def test_development_killed_worker_recovers_without_another_call(development, tmp_path):
    _, runner, _, _, _, now, observed = development
    record = dispatch(development)
    observed["delay"] = 1
    config = tmp_path / "worker-fixture.json"
    config.write_text(
        json.dumps(
            {
                "path": str(runner.path),
                "record": record,
                "now": now[0],
                "models": {k: asdict(v) for k, v in runner.models.items()},
                "cases": runner.cases,
                "image": runner.container.image_id,
                "url": runner.base_url,
            }
        )
    )
    worker = subprocess.Popen(
        [
            sys.executable,
            "-c",
            """
import json, sys
from pathlib import Path
from jevdrill.integrations.development import DevelopmentRunner, DevelopmentModel
from jevdrill.integrations.experiments import RestrictedContainerRunner
c = json.loads(Path(sys.argv[1]).read_text())
r = DevelopmentRunner(Path(c['path']), models={k: DevelopmentModel(**v) for k,v in c['models'].items()},
    cases=c['cases'], container=RestrictedContainerRunner(c['image']), credential=lambda: 'synthetic-secret',
    authorize=lambda _: True, clock=lambda: c['now'], base_url=c['url'])
r.run(c['record'])
""",
            str(config),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        end = time.monotonic() + 5
        while not observed["requests"] and time.monotonic() < end and worker.poll() is None:
            time.sleep(0.01)
        assert observed["requests"]
    finally:
        worker.kill()
        worker.wait(timeout=5)
    # A hard death does not run finally. Recovery conservatively waits for the
    # persisted deadline before confirming cleanup of a possibly interrupted launch.
    assert not runner.poll(record)["cleanup_verified"]
    now[0] = record["deadline_ms"]
    assert runner.poll(record)["host_status"] == "failed"
    assert runner.run(record)["host_status"] == "failed"
    assert len(observed["requests"]) == 1


def test_development_provider_deadline_does_not_retry(development):
    _, runner, _, _, _, _, observed = development
    observed["delay"] = 0.8
    profile = next(iter(runner.models.values()))
    from baml_bridge.errors import BamlError

    started = time.monotonic()
    with pytest.raises(BamlError):
        runner._complete("fixture", profile, time.monotonic() + 0.05)
    assert time.monotonic() - started < 0.7
    assert len(observed["requests"]) == 1


@pytest.mark.parametrize("family", ["review", "documentation"])
def test_actual_baml_artifact_worker_preserves_independent_checks(development, family):
    service, runner, request, proposal, _, _, observed = development
    expected = (
        {"findings": {"bounds": {"severity": "critical", "action": "reject invalid index"}}}
        if family == "review"
        else {
            "facts": {"argument": "index"},
            "requirements": ["bounds"],
            "references": ["public-spec-v1"],
            "examples": [{"index": 0, "answer": 3}],
        }
    )
    changed = copy.deepcopy(proposal)
    changed["idempotency_key"] = str(uuid4())
    experiment = changed["proposal"]["experiment"]
    experiment.update(comparison_experiment_id=str(uuid4()), context_ref=family)
    case = {
        "prompt": "Return the requested structured " + family + " artifact.",
        "task_family": family,
        "expected": expected,
        "evaluator_ref": experiment["evaluator_ref"],
        "rubric_revision": experiment["rubric_revision"],
    }
    experiment["context_hash"] = canonical_digest(case)
    runner.cases[family] = case
    service.handle(changed)
    request = request | {"comparison_experiment_id": experiment["comparison_experiment_id"]}
    observed["body"]["choices"][0]["message"]["content"] = json.dumps(expected)
    admitted = service.execute(request)
    assert admitted["status"] == "recorded", admitted
    record = service.execute(request | {"action": "advance"})["record"]
    receipt = runner.run(record)
    assert receipt["host_status"] == "completed"
    assert all(all(row["acceptance_checks"].values()) for row in receipt["candidates"])
    assert len(observed["requests"]) == 2
    assert "structured answer" in json.dumps(observed["requests"][0]["messages"][0]["content"])


def test_actual_immediate_host_acceptance_is_bounded_and_not_redispatched(development):
    service, runner, request, proposal, authority, _, observed = development
    runner.execution_mode = "immediate"
    changed = copy.deepcopy(proposal)
    changed["idempotency_key"] = str(uuid4())
    experiment = changed["proposal"]["experiment"]
    experiment.update(comparison_experiment_id=str(uuid4()), execution_path="harness_assisted")
    authority["allowed_execution_paths"] = ["harness_assisted"]
    service.handle(changed)
    request = request | {"comparison_experiment_id": experiment["comparison_experiment_id"]}
    assert service.execute(request)["status"] == "recorded"
    finished = service.execute(request | {"action": "advance"})
    assert finished["record"]["execution_status"] == "completed", finished
    assert finished["record"]["receipt"]["cleanup_verified"]
    assert len(observed["requests"]) == 2
    assert service.execute(request | {"action": "advance"}) == finished
    assert len(observed["requests"]) == 2


def test_documented_provider_context_cannot_be_replaced_by_request_bytes():
    model = DevelopmentModel(
        "gpt-4.1-mini-2025-04-14", 1_047_576, 512, "0.40", "1.60", "official-20261009", 0, 2_000_000
    )
    assert model.bound(1_000_000, 1_030_000) == 419850
    with pytest.raises(ContractError, match="full_context_reservation"):
        replace(model, input_limit=8192).bound(1_000_000, 1_030_000)


def test_resolved_pause_during_actual_call_prevents_later_call_and_retains_reservation(development):
    service, runner, request, _, _, _, observed = development
    record = dispatch(development)
    observed["delay"] = 0.3
    with ThreadPoolExecutor() as pool:
        future = pool.submit(runner.run, record)
        deadline = time.monotonic() + 2
        while not observed["requests"] and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(observed["requests"]) == 1
        service.settings = lambda scope: enabled_settings(scope) | {"experiment_enabled": False}
        receipt = future.result(timeout=3)
    assert receipt["host_status"] == "failed" and receipt["cleanup_verified"]
    assert len(observed["requests"]) == 1
    assert (
        service.storage.experiment_execution(request["scope"], request["comparison_experiment_id"])[
            "record"
        ]["reserved_microusd"]
        == record["reserved_microusd"]
    )
