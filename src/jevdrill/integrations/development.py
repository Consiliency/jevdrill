"""Durable, explicitly pumped BAML worker for registered development cases."""

import copy
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from pathlib import Path
from time import monotonic, time
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from baml_bridge.errors import BamlError

from baml_sdk import (
    JevUsageObservation,
    development_artifact_request_shape,
    development_discovery_request_shape,
    development_judgment_decode,
    development_observed_completion,
    development_request_shape,
    development_task_request_shape,
)
from baml_sdk.ai.content import StopReason

from ..contracts import ContractError, canonical_digest, jev_usage_measurements, parse_contract
from ..evaluation import grade_development_artifact
from .archive import maintenance_lock
from .experiments import RestrictedContainerRunner
from .jev import JUDGMENT_FUNCTION_REVISION, development_judgment_template_binding


@dataclass(frozen=True)
class DevelopmentModel:
    """Trusted, versioned provider limits and undiscounted USD rates per million tokens."""

    model_revision: str
    input_limit: int
    output_limit: int
    input_rate: str
    output_rate: str
    rate_revision: str
    verified_at_ms: int
    expires_at_ms: int
    request_bytes_limit: int = 8192
    request_timeout_ms: int = 30000

    def bound(self, now: int, deadline: int) -> int:
        # These pinned provider revisions reserve the complete documented context;
        # a request byte limit does not bound provider framing/billable tokens.
        if (
            self.model_revision in {"gpt-4.1-mini-2025-04-14", "gpt-4.1-nano-2025-04-14"}
            and self.input_limit < 1_047_576
        ):
            raise ContractError("development_full_context_reservation_required")
        try:
            rates = (Decimal(self.input_rate), Decimal(self.output_rate))
        except InvalidOperation:
            raise ContractError("development_profile_unverified") from None
        if (
            not self.model_revision
            or not self.rate_revision
            or not self.verified_at_ms <= now < deadline <= self.expires_at_ms
            or not 0 < self.input_limit <= 2**53 - 1
            or not 0 < self.output_limit <= 2**53 - 1
            or not 0 < self.request_bytes_limit <= 8192
            or not 0 < self.request_timeout_ms <= 30000
            or any(not r.is_finite() or r < 0 for r in rates)
        ):
            raise ContractError("development_profile_unverified")
        bound = int(
            (self.input_limit * rates[0] + self.output_limit * rates[1]).to_integral_value(
                rounding=ROUND_CEILING
            )
        )
        if not 0 < bound <= 2**53 - 1:
            raise ContractError("development_cost_bound_invalid")
        return bound


_JEV_HTTP = """
import http.client,json,ssl,sys
data=json.load(sys.stdin)
connection=(http.client.HTTPSConnection(data['host'],data['port'],timeout=data['timeout'],context=ssl.create_default_context()) if data['secure'] else http.client.HTTPConnection(data['host'],data['port'],timeout=data['timeout']))
try:
    connection.request('POST',data['path'],data['body'].encode(),{'Authorization':'Bearer '+data['key'],'Content-Type':'application/json'})
    response=connection.getresponse()
    body=response.read(65537)
    if response.status!=200 or len(body)>65536: sys.exit(1)
    sys.stdout.buffer.write(body)
finally:
    connection.close()
"""


class DevelopmentJudge:
    """Explicit study-only pinned JEV; no default retry, bounded receive, durable calls.

    The child has an absolute parent-enforced deadline and reads at most64KiB.
    The documented provider context (conservatively65536) is always reserved;
    free output removes the spending requirement for an unavailable output cap.
    This trusted configured port cannot be created from a public request.
    """

    model_revision = "jev-1.13.0"

    def __init__(
        self,
        path: Path,
        *,
        scope: Mapping[str, str],
        authorization_revision: str,
        max_calls: int,
        total_spend_microusd: int,
        deadline_ms: int,
        credential: Callable[[], str],
        authorize: Callable[[Mapping[str, str]], bool],
        base_url: str = "https://api.typesafe.ai/v1",
        clock: Callable[[], int] | None = None,
    ) -> None:
        parse_contract(
            "DiscoveryScope" if scope.get("operation") == "discover" else "CommandScope", scope
        )
        if (
            type(max_calls) is not int
            or not 0 < max_calls <= 768
            or type(total_spend_microusd) is not int
            or total_spend_microusd < 1
            or type(deadline_ms) is not int
            or not authorization_revision
        ):
            raise ContractError("development_judgment_limits_invalid")
        url = urlsplit(base_url)
        if (
            url.username
            or url.password
            or url.query
            or url.fragment
            or not (
                url.scheme == "https"
                and url.hostname == "api.typesafe.ai"
                and url.path == "/v1"
                or url.scheme == "http"
                and url.hostname in {"127.0.0.1", "localhost"}
            )
        ):
            raise ContractError("development_judgment_endpoint_invalid")
        self.path, self.scope = path, dict(scope)
        self.credential, self.authorize = credential, authorize
        self.clock = clock or (lambda: int(time() * 1000))
        self.url, self.deadline_ms = url, deadline_ms
        self.max_calls, self.total_spend_microusd = max_calls, total_spend_microusd
        self.revision = canonical_digest(
            {
                "scope": self.scope,
                "authorization_revision": authorization_revision,
                "model": "jev-1.13.0",
                "context": 65536,
                "rate": "0.042/M",
                "output_rate": "0",
                "max_calls": max_calls,
                "total_spend_microusd": total_spend_microusd,
                "deadline_ms": deadline_ms,
                "endpoint": base_url,
                "receive_bytes": 65536,
                "request_bytes": 8192,
                "retries": 0,
                **development_judgment_template_binding(),
            }
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as db, db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS judgment_profile (identity INTEGER PRIMARY KEY, revision TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS judgment_calls (identity TEXT PRIMARY KEY, reservation INTEGER NOT NULL, payload TEXT NOT NULL)"
            )
            prior = db.execute("SELECT revision FROM judgment_profile WHERE identity=1").fetchone()
            if prior is not None and prior[0] != self.revision:
                raise ContractError("development_judgment_profile_changed")
            db.execute("INSERT OR IGNORE INTO judgment_profile VALUES(1,?)", (self.revision,))

    def _allowed(self, operation: str) -> None:
        if self.clock() >= self.deadline_ms or not self.authorize(
            self.scope | {"operation": operation}
        ):
            raise ContractError("development_judgment_not_authorized")

    def prepare_option(
        self, objective: str, context: str, question: Mapping[str, Any], option: Mapping[str, Any]
    ) -> tuple[str, str, dict[str, Any]]:
        self._allowed("discover")
        if option["feasible"] is not True or option["option_id"] not in {
            row["option_id"] for row in question["options"]
        }:
            raise ContractError("unoffered discovery option")
        task = json.dumps({"objective": objective, "authorized_context": context}, sort_keys=True)
        offered = json.dumps(
            {
                "question_digest": question["question_digest"],
                "level": question["level"],
                "option_id": option["option_id"],
                "label": option["label"],
                "description": option["description"],
                "description_unknown": option["description"] is None,
            },
            sort_keys=True,
        )
        if len(development_discovery_request_shape(task, offered, "jev-1.13.0").encode()) > 8192:
            raise ContractError("development_judgment_request_too_large")
        return (
            task,
            offered,
            {
                "input_tokens": 65536,
                "output_tokens": 0,
                "reserved_spend": "0.002753",
                "currency": "USD",
            },
        )

    def _call(
        self, purpose: str, task: str, offered: str, deadline: float
    ) -> tuple[bool, list[dict[str, Any]]]:
        self._allowed(purpose)
        remaining = min(deadline - monotonic(), (self.deadline_ms - self.clock()) / 1000, 5)
        if remaining <= 0:
            raise ContractError("development_judgment_deadline")
        body = (
            development_discovery_request_shape
            if purpose == "discover"
            else development_task_request_shape
        )(task, offered, "jev-1.13.0")
        if len(body.encode()) > 8192:
            raise ContractError("development_judgment_request_too_large")
        identity = canonical_digest({"purpose": purpose, "task": task, "offered": offered})
        payload: dict[str, Any] = {
            "identity": identity,
            "configuration_digest": self.revision,
            "request_digest": canonical_digest(json.loads(body)),
            "model": "jev-1.13.0",
            "state": "uncertain",
            "response": None,
            "reserved_microusd": 2753,
        }
        with closing(sqlite3.connect(self.path, timeout=1)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            count, reserved = db.execute(
                "SELECT COUNT(*),COALESCE(SUM(reservation),0) FROM judgment_calls"
            ).fetchone()
            prior = db.execute(
                "SELECT payload FROM judgment_calls WHERE identity=?", (identity,)
            ).fetchone()
            if prior is not None:
                recorded = json.loads(prior[0])
                if (
                    recorded["state"] == "completed"
                    and recorded["configuration_digest"] == self.revision
                    and recorded["request_digest"] == payload["request_digest"]
                ):
                    return bool(recorded["response"]["answer"]), list(recorded["measurements"])
                raise ContractError("development_judgment_reservation_denied")
            if count >= self.max_calls or reserved + 2753 > self.total_spend_microusd:
                raise ContractError("development_judgment_reservation_denied")
            db.execute(
                "INSERT INTO judgment_calls VALUES(?,?,?)",
                (identity, 2753, json.dumps(payload, sort_keys=True)),
            )
        self._allowed(purpose)
        request = {
            "host": self.url.hostname,
            "port": self.url.port,
            "secure": self.url.scheme == "https",
            "path": self.url.path.rstrip("/") + "/systemone",
            "timeout": remaining,
            "body": body,
            "key": self.credential(),
        }
        self._allowed(purpose)
        remaining = min(deadline - monotonic(), (self.deadline_ms - self.clock()) / 1000, 5)
        if remaining <= 0:
            raise ContractError("development_judgment_deadline")
        request["timeout"] = remaining
        started = monotonic()
        process = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c", _JEV_HTTP],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={"SYSTEMROOT": str(os.environ.get("SYSTEMROOT", ""))}
            if sys.platform == "win32"
            else {},
        )
        try:
            output, _ = process.communicate(json.dumps(request).encode(), timeout=remaining)
            if process.returncode or len(output) > 65536 or monotonic() >= deadline:
                raise ContractError("development_judgment_incomplete")
            response = json.loads(output)
            if (
                not isinstance(response, dict)
                or response.get("model") != "jev-1.13.0"
                or set(response.get("answers", {})) != {"result"}
            ):
                raise ContractError("development_judgment_model_or_answers_mismatch")
            probability = response["answers"]["result"].get("noul")
            if (
                type(probability) not in (float, int)
                or not math.isfinite(probability)
                or not 0 <= probability <= 1
            ):
                raise ContractError("development_judgment_probability_invalid")
            answer = development_judgment_decode(output.decode(), "jev-1.13.0")
            usage = response.get("usage") or {}
            counts = {name: usage.get(name) for name in ("input_tokens", "output_tokens")}
            if any(
                value is not None
                and (
                    type(value) is not int or value < 0 or name == "input_tokens" and value > 65536
                )
                for name, value in counts.items()
            ):
                raise ContractError("development_judgment_usage_invalid")
            measurements = jev_usage_measurements(
                JevUsageObservation(
                    invocation_id=identity,
                    **counts,
                    input_invalid=False,
                    output_invalid=False,
                    call_input_tokens=None,
                    call_output_tokens=None,
                    duration_ms=int((monotonic() - started) * 1000),
                    first_output_ms=None,
                )
            )
            measurements.append(
                {
                    "metric_id": "raw_token_cost",
                    "metric_version": "1",
                    "measurement_value": {
                        "kind": "known",
                        "value": float(Decimal(counts["input_tokens"]) * Decimal("0.000000042")),
                        "unit": "USD",
                    }
                    if counts["input_tokens"] is not None
                    else {"kind": "unknown", "reason": "not_reported"},
                    "source": "provider",
                    "method": "official_jev_1.13_rates_20261009",
                    "scope": "call",
                    "counting_semantics": "disjoint",
                    "parent_metric_id": None,
                }
            )
            self._allowed(purpose)
            payload.update(
                state="completed",
                response={"model": response["model"], "answer": answer, "usage": counts},
                measurements=measurements,
            )
            with closing(sqlite3.connect(self.path)) as db, db:
                db.execute(
                    "UPDATE judgment_calls SET payload=? WHERE identity=?",
                    (json.dumps(payload, sort_keys=True), identity),
                )
            return bool(answer), measurements
        except (OSError, ValueError, BamlError, subprocess.TimeoutExpired):
            raise ContractError("development_judgment_incomplete") from None
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)

    def observe_option(
        self, task: str, offered: str, question_digest: str, option_id: str, deadline: float
    ) -> dict[str, Any]:
        answer, measurements = self._call("discover", task, offered, deadline)
        return dict(
            parse_contract(
                "DiscoveryJudgmentRecord",
                {
                    "schema_version": "1",
                    "function_revision": "ObserveDiscoveryOption-v1",
                    "model_revision": "jev-1.13.0",
                    "question_digest": question_digest,
                    "judgments": {option_id: answer},
                    "measurements": measurements,
                },
            ).payload()
        )

    def judge(
        self, task: str, candidates: tuple[Mapping[str, Any], ...], deadline: float
    ) -> dict[str, Any]:
        results, measurements = {}, []
        for candidate in candidates:
            answer, observed = self._call(
                "route", task, json.dumps(dict(candidate), sort_keys=True), deadline
            )
            results[candidate["candidate_id"]] = answer
            measurements.extend(observed)
        return dict(
            parse_contract(
                "JudgmentRecord",
                {
                    "schema_version": "1",
                    "function_revision": JUDGMENT_FUNCTION_REVISION,
                    "model_revision": "jev-1.13.0",
                    "candidate_digest": canonical_digest(list(candidates)),
                    "judgments": results,
                    "measurements": measurements,
                },
            ).payload()
        )


class IndependentDevelopmentGrader:
    """Local answer checks from trusted recipes, without provider calls or identities."""

    def __init__(
        self,
        cases: Mapping[str, Mapping[str, Any]],
        *,
        container: RestrictedContainerRunner,
        lock_path: Path,
        duration_ms: int,
        authorize: Callable[[str], bool],
    ) -> None:
        if not 0 < duration_ms <= 120_000:
            raise ContractError("policy_grading_duration_invalid")
        self.cases = copy.deepcopy(dict(cases))
        for case in self.cases.values():
            if (
                set(case) == {"task_family", "expected"}
                and case["task_family"] in {"review", "documentation"}
                and isinstance(case["expected"], dict)
            ):
                grade_development_artifact(case["task_family"], None, case["expected"])
                continue
            if (
                set(case) != {"inputs", "expected_answers"}
                or not isinstance(case["inputs"], list)
                or not case["inputs"]
                or not isinstance(case["expected_answers"], list)
                or len(case["inputs"]) != len(case["expected_answers"])
            ):
                raise ContractError("policy_grading_case_invalid")
        self.container, self.lock_path = container, lock_path
        self.duration_ms, self.authorize = duration_ms, authorize

    @property
    def revision(self) -> str:
        return canonical_digest(
            {
                "rubric": "independent-js-answers-v1",
                "cases": self.cases,
                "image": self.container.image_id,
                "duration_ms": self.duration_ms,
            }
        )

    def grade(self, grading_key: str, outputs: Sequence[str | None]) -> list[dict[str, Any]]:
        if sys.platform != "linux":
            raise ContractError("policy_grading_linux_worker_required")
        case = copy.deepcopy(self.cases.get(grading_key))
        if case is None or len(outputs) != 2 or not self.authorize(grading_key):
            raise ContractError("policy_grading_not_authorized")
        grades: list[dict[str, Any]] = []
        self.last_artifacts: list[dict[str, Any]] = []
        custody: list[int] = []
        revision = self.revision
        deadline = monotonic() + self.duration_ms / 1000
        with maintenance_lock(self.lock_path, acquired_fd=custody.append) as acquired:
            if not acquired:
                raise ContractError("policy_grading_worker_busy")
            for output in outputs:
                if monotonic() >= deadline or not self.authorize(grading_key):
                    raise ContractError("policy_grading_not_authorized")
                if "task_family" in case:
                    grades.append(
                        grade_development_artifact(case["task_family"], output, case["expected"])
                    )
                    try:
                        artifact = json.loads(output) if output is not None else None
                    except (ValueError, TypeError):
                        artifact = None
                    self.last_artifacts.append(
                        {
                            "output_digest": canonical_digest(output),
                            "artifact": artifact,
                            "grade": grades[-1],
                        }
                    )
                    continue
                result = (
                    self.container.evaluate(
                        output,
                        copy.deepcopy(case["inputs"]),
                        deadline,
                        run_id=str(uuid4()),
                        custody_fd=custody[0],
                    )
                    if output is not None
                    else {"status": "incomplete"}
                )
                reported = result.get("answers")
                answers = reported if isinstance(reported, list) else None
                known = result["status"] == "completed" and answers is not None
                matches = (
                    sum(
                        canonical_digest(answer) == canonical_digest(expected)
                        for answer, expected in zip(answers, case["expected_answers"], strict=True)
                    )
                    if known
                    and answers is not None
                    and len(answers) == len(case["expected_answers"])
                    else 0
                )
                quality = matches / len(case["inputs"]) if known else None
                grades.append(
                    {
                        "quality": quality,
                        "critical": {"answers_match": quality == 1} if known else {},
                    }
                )
                self.last_artifacts.append(
                    {
                        "output_digest": canonical_digest(output),
                        "artifact": {"results": answers} if known else None,
                        "runtime": result,
                        "grade": grades[-1],
                    }
                )
        if self.revision != revision:
            raise ContractError("policy_grading_recipe_changed")
        if monotonic() >= deadline or not self.authorize(grading_key):
            raise ContractError("policy_grading_not_authorized")
        return grades


class DevelopmentRunner:
    """start enqueues; run executes on a trusted Linux worker; poll never dispatches.

    The worker lock spans provider calls and container cleanup. A lost worker is
    recovered as incomplete, retaining its reservation and never repeating calls.
    The embedding host owns worker invocation, authority and credential lookup.
    """

    def __init__(
        self,
        path: Path,
        *,
        models: Mapping[str, DevelopmentModel],
        cases: Mapping[str, Mapping[str, Any]],
        container: RestrictedContainerRunner,
        credential: Callable[[], str],
        authorize: Callable[[Mapping[str, Any]], bool],
        base_url: str = "https://api.openai.com/v1",
        clock: Callable[[], int] | None = None,
        guidance: Mapping[tuple[str, str], Mapping[str, Any]] | None = None,
        execution_mode: str = "deferred",
    ) -> None:
        if execution_mode not in {"deferred", "immediate"}:
            raise ContractError("development_execution_mode_invalid")
        self.execution_mode = execution_mode
        self.path = path
        self.models = dict(models)
        self.cases = copy.deepcopy(dict(cases))
        self.guidance = copy.deepcopy(dict(guidance or {}))
        self.container = container
        self.credential, self.authorize = credential, authorize
        self.base_url = base_url
        self.clock = clock or (lambda: int(time() * 1000))
        self.lock_path = path.with_suffix(".worker.lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute("PRAGMA journal_mode = DELETE")
            db.execute(
                "CREATE TABLE IF NOT EXISTS development_runs "
                "(token TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.path, timeout=1)) as db, db:
            db.execute("PRAGMA secure_delete = ON")
            yield db

    @staticmethod
    def _load(db: sqlite3.Connection, token: str) -> dict[str, Any] | None:
        row = db.execute("SELECT payload FROM development_runs WHERE token=?", (token,)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def _save(db: sqlite3.Connection, job: dict[str, Any]) -> None:
        if job.get("canceled"):
            for key in ("experiment", "frozen_inputs", "config"):
                job.pop(key, None)
            job["observations"] = []
            job["results"] = []
        db.execute(
            "INSERT OR REPLACE INTO development_runs VALUES (?, ?)",
            (job["record"]["dispatch_token"], json.dumps(job, allow_nan=False)),
        )

    @staticmethod
    def _bind(job: dict[str, Any], record: Mapping[str, Any]) -> None:
        if any(
            job["record"][key] != record[key]
            for key in (
                "dispatch_token",
                "experiment_digest",
                "deadline_ms",
                "reserved_microusd",
                "authorization_digest",
                "comparison_experiment_id",
                "task_id",
                "harness_id",
            )
        ):
            raise ContractError("development_dispatch_binding_mismatch")

    def _inputs(
        self, experiment: Mapping[str, Any], deadline: int
    ) -> tuple[dict[str, Any], int, str]:
        case = self.cases.get(experiment["context_ref"])
        plans, limits = experiment["candidate_plans"], experiment["limits"]
        artifact_case = (
            case is not None
            and set(case)
            == {"prompt", "task_family", "expected", "evaluator_ref", "rubric_revision"}
            and case["task_family"] in {"review", "documentation"}
            and isinstance(case["expected"], dict)
        )
        if (
            case is None
            or canonical_digest(case) != experiment["context_hash"]
            or not isinstance(case["prompt"], str)
            or (
                not artifact_case
                and (
                    set(case)
                    != {"prompt", "inputs", "expected_answers", "evaluator_ref", "rubric_revision"}
                    or not isinstance(case["inputs"], list)
                    or not case["inputs"]
                    or not isinstance(case["expected_answers"], list)
                    or len(case["inputs"]) != len(case["expected_answers"])
                )
            )
            or any(case[k] != experiment[k] for k in ("evaluator_ref", "rubric_revision"))
        ):
            raise ContractError("development_case_unavailable")
        if (
            experiment["execution_path"]
            != ("internal" if self.execution_mode == "deferred" else "harness_assisted")
            or experiment["isolation_ref"] != self.container.image_id
            or not 1 <= len(plans) <= 5
            or limits["max_duration_ms"] > 120_000
            or limits["cpu_limit"] != 2
            or limits["memory_limit_bytes"] != 2 * 1024**3
        ):
            raise ContractError("development_execution_unsupported")
        profiles, total = [], 0
        for plan in plans:
            profile = self.models.get(plan["resolved_model_revision"])
            if (
                profile is None
                or profile.model_revision != plan["resolved_model_revision"]
                or plan["model_id"] != profile.model_revision
                or plan["provider"] != "openai"
                or plan["access_route"] != "baml_development"
                or plan["harness_id"] != "jevdrill"
                or plan["execution_target_id"] != "linux_worker"
                or plan["native_effort"] != {"kind": "provider_default"}
            ):
                raise ContractError("development_plan_unsupported")
            self._prompt(case, plan, experiment["task_id"])
            total += profile.bound(self.clock(), deadline)
            profiles.append(asdict(profile))
        return (
            dict(case),
            total,
            canonical_digest(
                {
                    "case": case,
                    "profiles": profiles,
                    "image": self.container.image_id,
                    "url": self.base_url,
                    "execution_mode": self.execution_mode,
                    "prompts": [self._prompt(case, plan, experiment["task_id"]) for plan in plans],
                }
            ),
        )

    def _prompt(self, case: Mapping[str, Any], plan: Mapping[str, Any], task_id: str) -> str:
        instructions = []
        for reference in plan["required_guidance"] + plan["optional_guidance"]:
            resource = self.guidance.get((reference["resource_id"], reference["revision"]))
            if (
                resource is None
                or reference["task_id"] != task_id
                or reference["admission"] not in {"explicitly_enabled", "policy_admitted"}
                or hashlib.sha256(resource["instructions"].encode()).hexdigest()
                != reference["content_hash"]
                or not resource["rights"]
            ):
                raise ContractError("development_guidance_unverified")
            instructions.append(resource["instructions"])
        return str(case["prompt"]) + (
            "\nAuthorized guidance:\n" + "\n".join(instructions) if instructions else ""
        )

    def _runtime(self) -> None:
        if sys.platform != "linux":
            raise ContractError("development_linux_worker_required")
        result = subprocess.run(
            ["docker", "info", "--format", "{{json .}}"],
            capture_output=True,
            check=False,
            timeout=1,
        )
        info = json.loads(result.stdout) if result.returncode == 0 else {}
        if (
            info.get("OSType") != "linux"
            or info.get("NCPU", 0) < 2
            or info.get("MemTotal", 0) < 2 * 1024**3
        ):
            raise ContractError("development_resources_unavailable")
        probe = self.container.evaluate(
            "function solve(x) { return x; }", [[1]], monotonic() + 2, run_id=str(uuid4())
        )
        if probe.get("status") != "completed" or probe.get("answers") != [1]:
            raise ContractError("development_container_unavailable")

    def prepare(self, experiment: Mapping[str, Any], deadline_ms: int) -> dict[str, Any]:
        _, bound, _ = self._inputs(experiment, deadline_ms)
        try:
            self._runtime()
        except (OSError, ValueError, subprocess.TimeoutExpired):
            raise ContractError("development_runtime_unavailable") from None
        capabilities = [
            "text",
            "bounded_execution",
            "durable_dispatch",
            "cancel_before_start",
            "verified_cleanup",
            "restricted_container",
            "network_disabled",
            "shadow_side_effects_disabled",
        ]
        return dict(
            parse_contract(
                "ExperimentReadiness",
                {
                    "schema_version": "1",
                    "harness_id": "jevdrill",
                    "execution_target_id": "linux_worker",
                    "context_hash": experiment["context_hash"],
                    "context_available": True,
                    "local_execution": self.base_url.startswith("http://127.0.0.1:")
                    or self.base_url.startswith("http://localhost:"),
                    "isolation_ref": self.container.image_id,
                    "declared_capabilities": capabilities,
                    "runtime_capabilities": capabilities,
                    "candidate_plan_digests": [
                        canonical_digest(p) for p in experiment["candidate_plans"]
                    ],
                    "spend_bound_verified": True,
                    "upper_cost_microusd": bound,
                    "available_cpu": 2,
                    "available_memory_bytes": 2 * 1024**3,
                    "max_concurrency": 1,
                    "expires_at": datetime.fromtimestamp(deadline_ms / 1000, UTC)
                    .isoformat()
                    .replace("+00:00", "Z"),
                },
            ).payload()
        )

    def start(self, experiment: Mapping[str, Any], record: Mapping[str, Any]) -> dict[str, Any]:
        if canonical_digest(experiment) != record["experiment_digest"]:
            raise ContractError("development_experiment_mismatch")
        # A canceled token must be recognized even after profiles/context expire.
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            prior = self._load(db, record["dispatch_token"])
            if prior:
                self._bind(prior, record)
                return self._receipt(prior)
            case, bound, config = self._inputs(experiment, record["deadline_ms"])
            if bound > record["reserved_microusd"] or not self.authorize(record):
                raise ContractError("development_dispatch_not_authorized")
            job = {
                "record": dict(record),
                "experiment": dict(experiment),
                "config": config,
                "frozen_inputs": {
                    "case": case,
                    "models": [
                        asdict(self.models[p["resolved_model_revision"]])
                        for p in experiment["candidate_plans"]
                    ],
                },
                "state": "queued",
                "canceled": False,
                "results": [],
                "observations": [],
                "cleanup": False,
            }
            self._save(db, job)
        return self.run(record) if self.execution_mode == "immediate" else self._receipt(job)

    @staticmethod
    def _receipt(job: Mapping[str, Any]) -> dict[str, Any]:
        status = {"queued": "running", "executing": "running"}.get(job["state"], job["state"])
        return dict(
            parse_contract(
                "ExperimentHostReceipt",
                {
                    "schema_version": "1",
                    "dispatch_token": job["record"]["dispatch_token"],
                    "experiment_digest": job["record"]["experiment_digest"],
                    "host_status": status,
                    "cleanup_verified": job["cleanup"],
                    "candidates": job["results"] if status != "running" else [],
                    "preferred_plan_id": None,
                    "preference_reason": None,
                },
            ).payload()
        )

    def retained_observations(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Read a terminal snapshot for trusted reclassification; never dispatch."""
        with self._db() as db:
            job = self._load(db, record["dispatch_token"])
        if job is None:
            raise ContractError("development_observations_unavailable")
        self._bind(job, record)
        if (
            job["canceled"]
            or not job["cleanup"]
            or job["state"] not in {"completed", "failed"}
            or record["execution_status"] not in {"completed", "incomplete"}
            or canonical_digest(self._receipt(job)) != canonical_digest(record["receipt"])
        ):
            raise ContractError("development_observations_not_terminal")
        return copy.deepcopy(
            {
                "experiment_digest": record["experiment_digest"],
                "context_hash": job["experiment"]["context_hash"],
                "observations": job["observations"],
            }
        )

    def cancel(self, record: Mapping[str, Any]) -> dict[str, Any]:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._load(db, record["dispatch_token"])
            if job:
                self._bind(job, record)
            else:
                job = {
                    "record": dict(record),
                    "state": "canceled",
                    "results": [],
                    "observations": [],
                    "cleanup": True,
                }
            job["canceled"] = True
            if job["state"] == "queued":
                job.update(state="canceled", cleanup=True)
            if job["cleanup"] and job["state"] in {"completed", "failed", "canceled"}:
                job["state"] = "canceled"
            self._save(db, job)
        with self._db() as db:
            db.execute("VACUUM")
        return self.poll(record)

    def poll(self, record: Mapping[str, Any]) -> dict[str, Any]:
        with maintenance_lock(self.lock_path) as acquired, self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._load(db, record["dispatch_token"])
            if job is None:
                return self._receipt(
                    {"record": record, "state": "absent", "results": [], "cleanup": False}
                )
            self._bind(job, record)
            if (
                acquired
                and job["state"] == "executing"
                and (job["cleanup"] or self.clock() >= record["deadline_ms"])
            ):
                # Acquiring OS custody proves the old worker stopped; the call may
                # still have cost money remotely, so its reservation is never refunded.
                self.container.cleanup(record["dispatch_token"])
                job.update(state="canceled" if job["canceled"] else "failed", cleanup=True)
                self._save(db, job)
            return self._receipt(job)

    def run(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Bounded worker entrypoint; call outside the short-lived request transport."""
        custody: list[int] = []
        with maintenance_lock(self.lock_path, acquired_fd=custody.append) as acquired:
            if not acquired:
                raise ContractError("development_worker_busy")
            with self._db() as db:
                db.execute("BEGIN IMMEDIATE")
                job = self._load(db, record["dispatch_token"])
                if job is None:
                    raise ContractError("development_dispatch_not_found")
                self._bind(job, record)
                if job["state"] != "queued":
                    return self._receipt(job)
                for (payload,) in db.execute("SELECT payload FROM development_runs"):
                    prior = json.loads(payload)
                    if prior["state"] == "executing":
                        raise ContractError("development_recovery_required")
                job["state"] = "executing"
                self._save(db, job)
            deadline = monotonic() + max(0, (record["deadline_ms"] - self.clock()) / 1000)
            try:
                case, bound, config = self._inputs(job["experiment"], record["deadline_ms"])
                if config != job["config"] or bound > record["reserved_microusd"]:
                    raise ContractError("development_configuration_changed")
                for plan in job["experiment"]["candidate_plans"]:
                    self._allowed(record, deadline)
                    profile = self.models[plan["resolved_model_revision"]]
                    prompt = self._prompt(case, plan, job["experiment"]["task_id"])
                    observation = (
                        self._complete(prompt, profile, deadline)
                        if not case.get("task_family")
                        else self._complete(
                            prompt, profile, deadline, task_family=case["task_family"]
                        )
                    )
                    # Preserve attributable observations even if evaluation/cleanup fails.
                    job["observations"].append(
                        {"execution_plan_id": plan["execution_plan_id"], **observation}
                    )
                    self._checkpoint(job)
                    self._allowed(record, deadline)
                    checked: dict[str, Any]
                    if case.get("task_family"):
                        grade = grade_development_artifact(
                            case["task_family"], observation["output"], case["expected"]
                        )
                        checked = {
                            "status": "completed" if grade["quality"] is not None else "incomplete"
                        }
                        acceptance = grade["critical"]
                    else:
                        checked = self.container.evaluate(
                            observation["output"] or "",
                            case["inputs"],
                            deadline,
                            run_id=record["dispatch_token"],
                            custody_fd=custody[0],
                        )
                        acceptance = {
                            "answers_match": canonical_digest(checked.get("answers"))
                            == canonical_digest(case["expected_answers"]),
                            "inputs_unchanged": checked.get("inputs_unchanged") is True,
                        }
                    completed = observation["completed"] and checked["status"] == "completed"
                    job["results"].append(
                        {
                            "execution_plan_id": plan["execution_plan_id"],
                            "status": "completed" if completed else "failed",
                            "measurements": observation["measurements"],
                            "acceptance_checks": acceptance if completed else {},
                            "evaluator_ref": case["evaluator_ref"],
                            "rubric_revision": case["rubric_revision"],
                        }
                    )
                    self._checkpoint(job)
                self._allowed(record, deadline)
                job["state"] = (
                    "completed"
                    if all(r["status"] == "completed" for r in job["results"])
                    else "failed"
                )
            except (ContractError, BamlError, OSError, ValueError, subprocess.TimeoutExpired):
                # Never serialize SDK/provider exception text, which can contain credentials.
                job["state"] = "failed"
            finally:
                try:
                    self.container.cleanup(record["dispatch_token"])
                    job["cleanup"] = True
                except (ContractError, OSError, subprocess.TimeoutExpired):
                    # Recovery will retry cleanup under exclusive worker custody.
                    job["state"] = "executing"
                self._checkpoint(job)
            return self._receipt(job)

    def _checkpoint(self, job: dict[str, Any]) -> None:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            current = self._load(db, job["record"]["dispatch_token"])
            assert current is not None
            job["canceled"] = current["canceled"]
            if job["canceled"] and job["cleanup"]:
                job["state"] = "canceled"
            self._save(db, job)

    def _allowed(self, record: Mapping[str, Any], deadline: float) -> None:
        with self._db() as db:
            job = self._load(db, record["dispatch_token"])
        if (
            job is None
            or job["canceled"]
            or monotonic() >= deadline
            or not record["admitted_at_ms"] <= self.clock() < record["deadline_ms"]
            or not self.authorize(record)
        ):
            raise ContractError("development_dispatch_not_authorized")

    def _complete(
        self,
        prompt: str,
        profile: DevelopmentModel,
        deadline: float,
        *,
        task_family: str = "implementation",
    ) -> dict[str, Any]:
        if task_family not in {"implementation", "review", "documentation"}:
            raise ContractError("development_artifact_family_invalid")
        shape = (
            development_request_shape
            if task_family == "implementation"
            else development_artifact_request_shape
        )
        wire = json.loads(shape(prompt, profile.model_revision, profile.output_limit))
        if (
            set(wire)
            != {"model", "messages", "max_completion_tokens", "n", "store", "service_tier"}
            or wire["model"] != profile.model_revision
            or wire["max_completion_tokens"] != profile.output_limit
            or wire["n"] != 1
            or wire["store"] is not False
            or wire["service_tier"] != "default"
        ):
            raise ContractError("development_request_unverified")
        if len(json.dumps(wire, ensure_ascii=False).encode("utf-8")) > profile.request_bytes_limit:
            raise ContractError("development_input_bound_exceeded")
        key = self.credential()
        remaining = min(profile.request_timeout_ms, int((deadline - monotonic()) * 1000))
        if not key or remaining <= 0:
            raise ContractError("development_credential_or_deadline_unavailable")
        started = monotonic()
        turn = development_observed_completion(
            prompt,
            profile.model_revision,
            key,
            self.base_url,
            remaining,
            profile.output_limit,
            task_family,
        )
        elapsed = int((monotonic() - started) * 1000)
        usage = turn.usage
        observed_models = [
            json.loads(call.http_response.body).get("model")
            for call in turn.calls
            if call.selected
            and call.http_response is not None
            and call.http_response.body is not None
        ]
        observed_model = observed_models[0] if len(observed_models) == 1 else None
        if observed_model is not None and observed_model != profile.model_revision:
            raise ContractError("development_response_model_mismatch")
        if usage and (
            not 0 <= usage.input_tokens <= profile.input_limit
            or not 0 <= usage.output_tokens <= profile.output_limit
        ):
            raise ContractError("development_usage_exceeds_bound")
        raw_cost = (
            float(
                (
                    usage.input_tokens * Decimal(profile.input_rate)
                    + usage.output_tokens * Decimal(profile.output_rate)
                )
                / 1_000_000
            )
            if usage
            else None
        )
        measurements = []
        for metric, value, unit, source, method in (
            ("completion_time_ms", elapsed, "ms", "direct", "monotonic_call_duration"),
            (
                "input_tokens",
                usage.input_tokens if usage else None,
                "tokens",
                "provider",
                "provider_usage",
            ),
            (
                "output_tokens",
                usage.output_tokens if usage else None,
                "tokens",
                "provider",
                "provider_usage",
            ),
            (
                "cached_input_tokens",
                usage.cached_input_tokens if usage else None,
                "tokens",
                "provider",
                "provider_usage",
            ),
            ("raw_token_cost", raw_cost, "USD", "provider", "full_rates:" + profile.rate_revision),
        ):
            measurements.append(
                {
                    "metric_id": metric,
                    "metric_version": "1",
                    "measurement_value": {"kind": "known", "value": value, "unit": unit}
                    if value is not None
                    else {"kind": "unknown", "reason": "not_reported"},
                    "source": source,
                    "method": method,
                    "scope": "call",
                    "counting_semantics": "subset"
                    if metric == "cached_input_tokens"
                    else "disjoint",
                    "parent_metric_id": "input_tokens" if metric == "cached_input_tokens" else None,
                }
            )
        return {
            "requested_model": profile.model_revision,
            "observed_model": observed_model,
            "request_digest": canonical_digest(wire),
            "profile_digest": canonical_digest(asdict(profile)),
            "output": turn.terminal_text(),
            "completed": turn.stop_reason == StopReason.Complete
            and not turn.tool_uses()
            and monotonic() < deadline,
            "stop_reason": turn.stop_reason.value,
            "measurements": measurements,
        }
