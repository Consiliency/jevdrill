"""Verify exposed public development diagnostics or a separately authorized study."""

import argparse
import copy
import hashlib
import json
import math
import sqlite3
import tempfile
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

from jevdrill.application import Application
from jevdrill.contracts import canonical_digest, parse_contract
from jevdrill.discovery import reference
from jevdrill.evaluation import evaluate_host_artifact
from jevdrill.integrations.jev import (
    JUDGMENT_FUNCTION_REVISION,
    development_judgment_template_binding,
)
from jevdrill.storage import SQLiteStorage

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "research/evaluation/discovery-calibration/protocol.json"
BASELINES = {
    "fixed_default",
    "cheapest_feasible",
    "no_guidance",
    "previous_policy",
    "simple_retrieval",
}


def read_protocol(root=ROOT):
    protocol = json.loads((root / PROTOCOL).read_text())
    cases = protocol["cases"]
    if (
        protocol["schema_version"] != 1
        or not protocol["exposed"]
        or protocol["holdouts_opened"]
        or protocol["promotion_eligible"]
        or protocol["performance_claims"] != "insufficient_evidence"
        or set(protocol["baselines"]) != BASELINES
        or len({case["id"] for case in cases}) != len(cases)
        or {case["task_family"] for case in cases} != {"implementation", "review", "documentation"}
    ):
        raise ValueError("invalid public development protocol")
    required = {
        "ambiguous-alias",
        "cross-domain",
        "no-useful-guidance",
        "changed-objective-before",
        "changed-objective-after",
        "shared-skill-different-task",
    }
    if not required <= {case["scenario"] for case in cases}:
        raise ValueError("missing representative discovery conditions")
    for case in cases:
        if (
            set(case["baseline_applicability"]) != BASELINES
            or not all(
                evaluate_host_artifact(
                    case["task_family"], case["expected"], case["reference_artifact"]
                ).values()
            )
            or all(
                evaluate_host_artifact(
                    case["task_family"], case["expected"], case["unacceptable_artifact"]
                ).values()
            )
        ):
            raise ValueError("independent artifact controls invalid")
        if (
            not case["baseline_applicability"]["previous_policy"]
            and not case["previous_policy_inapplicable_reason"]
        ):
            raise ValueError("unexplained baseline omission")
    return protocol


class ScriptedObserver:
    """An explicitly synthetic oracle; its answers prove only software behavior."""

    def __init__(self, selected):
        self.selected = set(selected)
        self.calls = 0

    def observe_option(self, task, offered, question_digest, option_id, deadline):
        self.calls += 1
        option = json.loads(offered)
        return {
            "schema_version": "1",
            "function_revision": "ObserveDiscoveryOption-v1",
            "model_revision": "jev-latest",
            "question_digest": question_digest,
            "judgments": {
                option_id: option["level"] != "resource" or option["label"] in self.selected
            },
            "measurements": [],
        }


def inputs(root, protocol, case):
    discovery = copy.deepcopy(
        json.loads((root / "tests/contracts/fixtures/discovery.json").read_text())[0]["payload"]
    )
    identity = str(uuid5(NAMESPACE_URL, protocol["revision"] + case["id"]))
    discovery["envelope"].update(request_id=identity, idempotency_key=case["id"])
    discovery.update(
        work_objective_id=str(uuid5(NAMESPACE_URL, case["objective_chain_id"]))
        if "objective_chain_id" in case
        else identity,
        work_objective_text=case["objective"],
        authorized_context=case["task_prompt"],
    )
    template = discovery["catalog"]["resources"][0]
    resources, descriptions = [], []
    for item in protocol["resources"]:
        resource = copy.deepcopy(template)
        resource.update(
            resource_id=item["id"],
            domain=item["domain"],
            specialty=item["id"],
            task_family=item["family"],
            aliases=["shared"],
            instructions=item["instructions"],
            content_hash=hashlib.sha256(item["instructions"].encode()).hexdigest(),
            rights=protocol["rights"],
        )
        resources.append(resource)
        descriptions.append(
            reference(resource)
            | {"description_revision": protocol["revision"], "description": item["description"]}
        )
    discovery["catalog"].update(revision=protocol["revision"], resources=resources)
    discovery["descriptions"] = descriptions
    route = copy.deepcopy(
        json.loads((root / "tests/contracts/fixtures/route-application.json").read_text())[0][
            "payload"
        ]
    )
    route["catalog"] = discovery["catalog"]
    route["request"]["versions"]["catalog_revision"] = protocol["revision"]
    route["request"].update(task_id=identity, task_representation=case["task_prompt"])
    route["request"]["envelope"].update(request_id=identity, idempotency_key=case["id"])
    candidate = route["inventory"]["candidates"][0]
    candidate.update(
        candidate_id="cheap",
        model_id="model-cheap",
        resolved_model_revision="model-cheap-v1",
        completion_time_ms=1000,
    )
    available = sorted(
        resources, key=lambda row: row["resource_id"] not in case["acceptable_guidance"][0]
    )[:2]
    candidate["guidance_options"] = [
        reference(row)
        | {
            "role": "optional-" + row["resource_id"],
            "admission": row["admission"],
            "authority": "public-synthetic-admission",
            "task_id": identity,
            "token_count": None,
        }
        for row in available
    ]
    fast = copy.deepcopy(candidate)
    fast.update(
        candidate_id="fast",
        model_id="model-fast",
        resolved_model_revision="model-fast-v1",
        completion_time_ms=10,
        default=True,
    )
    fast["rates"]["input_rate"] = "0.01"
    route["inventory"]["candidates"].append(fast)
    if case["completion_time_limit_ms"] is not None:
        route["completion_time_limit_ms"] = case["completion_time_limit_ms"]
    return discovery, route


def selection_ok(case, guidance, model):
    return (
        sorted(guidance) in [sorted(choice) for choice in case["acceptable_guidance"]]
        and model in case["acceptable_model_ids"]
    )


def offline(root=ROOT):
    protocol = read_protocol(root)
    rows = []
    with tempfile.TemporaryDirectory(prefix="jevdrill-public-development-") as directory:
        for case in protocol["cases"]:
            discovery, route = inputs(root, protocol, case)
            observer = ScriptedObserver(case["acceptable_guidance"][0])
            app = Application(
                SQLiteStorage(Path(directory) / "public-development.db"),
                discovery_judgments=observer,
            )
            started = time.monotonic()
            selected = app.discover(discovery)
            linked = {
                "schema_version": "2",
                "route_inputs": route,
                "discovery_ref": {
                    key: selected["details"][key]
                    for key in ("discovery_id", "work_objective_id", "trace_digest")
                },
            }
            decision = app.route(linked)
            elapsed = (time.monotonic() - started) * 1000
            plan = decision.get("execution_plan")
            actual_guidance = [row["resource_id"] for row in selected["details"]["guidance_refs"]]
            model = None if plan is None else plan["model_id"]
            actual_ok = decision["status"] == "ready" and selection_ok(case, actual_guidance, model)
            independent = evaluate_host_artifact(
                case["task_family"], case["expected"], case["reference_artifact"]
            )
            baselines = {}
            for name, applicable in case["baseline_applicability"].items():
                if not applicable:
                    baselines[name] = {
                        "applicable": False,
                        "reason": case["previous_policy_inapplicable_reason"],
                    }
                    continue
                baseline = copy.deepcopy(route)
                baseline["request"]["versions"]["context_revision"] = (
                    protocol["revision"] + ":" + name
                )
                # Fixed/default and cheapest remain subject to the same actual feasibility gates.
                if name == "fixed_default":
                    baseline["inventory"]["candidates"] = [baseline["inventory"]["candidates"][1]]
                for row in baseline["inventory"]["candidates"]:
                    row["guidance_options"] = []
                baseline["request"]["task_id"] = str(uuid5(NAMESPACE_URL, case["id"] + name))
                baseline["request"]["envelope"]["idempotency_key"] = case["id"] + ":" + name
                baseline["request"]["envelope"]["request_id"] = baseline["request"]["task_id"]
                result = app.route(baseline)
                retrieval = (
                    [
                        resource["id"]
                        for resource in protocol["resources"]
                        if resource["id"] in case["objective"]
                    ]
                    if name == "simple_retrieval"
                    else []
                )
                baseline_model = (
                    model
                    if name == "no_guidance"
                    else result.get("execution_plan", {}).get("model_id")
                )
                baselines[name] = {
                    "applicable": True,
                    "status": result["status"],
                    "model_id": baseline_model,
                    "guidance": retrieval,
                    "selection_acceptable": selection_ok(case, retrieval, baseline_model),
                    "downstream_quality": None,
                    "missing_reason": "no authorized model execution",
                }
            rows.append(
                {
                    "case_id": case["id"],
                    "related_group": case["related_group"],
                    "family": case["task_family"],
                    "discovery": selected,
                    "decision": decision,
                    "selection_acceptable": actual_ok,
                    "software_selection_overhead_ms": elapsed,
                    "scripted_judgment_calls": observer.calls,
                    "baselines": baselines,
                    "reference_checks": independent,
                    "actual_outcome": None,
                    "actual_cost": None,
                    "actual_total_time": None,
                    "missing_reason": "software-only scripted observer and independent reference artifacts",
                }
            )
    controls = {
        "always_admit_rejected": any(
            not selection_ok(case, [r["id"] for r in protocol["resources"]], "model-cheap")
            for case in protocol["cases"]
        ),
        "all_default_rejected": any(
            not selection_ok(case, [], "model-fast") for case in protocol["cases"]
        ),
        "damaged_artifacts_rejected": all(
            not all(
                evaluate_host_artifact(
                    case["task_family"], case["expected"], case["unacceptable_artifact"]
                ).values()
            )
            for case in protocol["cases"]
        ),
    }
    passed = all(
        row["selection_acceptable"] and all(row["reference_checks"].values()) for row in rows
    ) and all(controls.values())
    return {
        "schema_version": 1,
        "origin": "software_only_scripted_observer",
        "status": "passed" if passed else "failed",
        "protocol_digest": canonical_digest(protocol),
        "performance_claims": "insufficient_evidence",
        "produced_if_gates": [],
        "controls": controls,
        "cases": rows,
    }


def source_digest(root=ROOT):
    paths = sorted(
        {
            p
            for pattern in (
                "src/**/*.py",
                "baml_src/**/*.baml",
                "schemas/*.json",
                "scripts/verify_discovery_calibration.py",
                "tests/contracts/fixtures/discovery.json",
                "tests/contracts/fixtures/route-application.json",
                PROTOCOL,
            )
            for p in root.glob(pattern)
            if "__pycache__" not in p.parts
        }
    )
    return canonical_digest(
        {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    )


def finite(value, lower=0, upper=float("inf")):
    return type(value) in (int, float) and math.isfinite(value) and lower <= value <= upper


def calibration_errors(protocol):
    errors = []
    for family, settings in protocol["calibration"].items():
        if any(value is None for value in settings.values()):
            errors.append("Q12/Q13 family-specific empirical calibration unresolved")
            continue
        if (
            set(settings)
            != {
                "quality_floor",
                "maximum_quality_loss",
                "practical_equivalence",
                "minimum_pairs",
                "confidence",
                "revision",
                "frozen_at",
            }
            or any(
                not finite(settings[key], 0, 1)
                for key in ("quality_floor", "maximum_quality_loss", "practical_equivalence")
            )
            or not finite(settings["confidence"], 0.500000001, 0.999999999)
            or type(settings["minimum_pairs"]) is not int
            or settings["minimum_pairs"] < 2
            or not isinstance(settings["revision"], str)
            or not settings["revision"]
        ):
            errors.append("invalid preregistered calibration: " + family)
            continue
        try:
            datetime.fromisoformat(settings["frozen_at"])
        except (TypeError, ValueError):
            errors.append("invalid preregistered calibration: " + family)
    return sorted(set(errors))


def authority_preview(root=ROOT):
    protocol = read_protocol(root)
    project = str(uuid5(NAMESPACE_URL, "jevdrill-public-development-20261009-v1"))
    return {
        "schema_version": 1,
        "authorization_revision": "discovery-development-new-20261009-v1",
        "enabled": False,
        "study_id": "discovery-development-proposed-20261009-v1",
        "source_digest": source_digest(root),
        "protocol_digest": canonical_digest(protocol),
        "scope": {"project_id": project, "workspace_id": project, "producer": "jevdrill"},
        "operations": ["discover", "route", "experiment"],
        "expires_at": "2026-10-15T00:00:00Z",
        "candidate_revisions": ["gpt-4.1-mini-2025-04-14", "gpt-4.1-nano-2025-04-14"],
        "judgment_revision": "jev-1.13.0",
        "max_candidate_calls": 60,
        "max_judgment_calls": 768,
        "candidate_spend_microusd": 26000000,
        "judgment_spend_microusd": 2200000,
        "total_spend_microusd": 28200000,
        "whole_study_deadline_ms": 2400000,
        "candidate_output_tokens": 512,
        "request_bytes": 8192,
        "receive_bytes": 65536,
        "attempts": 1,
        "concurrency": 1,
        "cpu": 2,
        "memory_bytes": 2147483648,
        "pids": 64,
        "image_id": "sha256:70af8b01bcbd3a008522f36ea07b679f14f9ad3fb721868cf0cc3f80b7e3f958",
        "promotion_authorized": False,
        "holdouts_opened": False,
        "calibration_collection_only": True,
    }


def authority_errors(authority, root=ROOT, dispatch=False):
    expected = authority_preview(root)
    expected["enabled"] = True
    errors = (
        []
        if canonical_digest(authority) == canonical_digest(expected)
        else ["new trusted study authority differs from bounded preview"]
    )
    if dispatch and datetime.now(UTC) >= datetime.fromisoformat(expected["expires_at"]):
        errors.append("new study authority expired")
    return errors


def write_artifact(directory, name, value):
    path = directory / name
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
    return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def read_artifact(directory, reference):
    path = (directory / reference["path"]).resolve()
    if not path.is_relative_to(directory.resolve()) or path.is_symlink():
        raise ValueError("artifact outside immutable study")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != reference["sha256"]:
        raise ValueError("changed immutable artifact")
    return json.loads(data)


def metric(measurements, name):
    values = [
        row["measurement_value"]
        for row in measurements
        if row["metric_id"] == name and row["counting_semantics"] == "disjoint"
    ]
    if not values or any(row["kind"] != "known" for row in values):
        return None
    return sum(row["value"] for row in values)


def objective_duration(discovery, routing, execution, grading):
    return sum((discovery, routing, execution, grading))


def telemetry_errors(value):
    keys = {"discovery", "routing", "execution", "grading", "total", "raw_cost", "tokens"}
    if set(value) != keys or any(not finite(value[key]) for key in keys - {"tokens"}):
        return ["required objective telemetry unknown or invalid"]
    if value["total"] < objective_duration(
        *(value[key] for key in ("discovery", "routing", "execution", "grading"))
    ):
        return ["omitted overhead"]
    tokens = value["tokens"]
    if not isinstance(tokens, dict) or set(tokens) != {"input", "output", "cached_input"}:
        return ["token telemetry missing"]
    for counter in tokens.values():
        if not isinstance(counter, dict) or not (
            set(counter) == {"value"}
            and type(counter["value"]) is int
            and counter["value"] >= 0
            or set(counter) == {"missing_reason"}
            and counter["missing_reason"] in {"not_reported", "incomplete"}
        ):
            return ["invalid token telemetry"]
    if (
        all("value" in tokens[k] for k in ("input", "cached_input"))
        and tokens["cached_input"]["value"] > tokens["input"]["value"]
    ):
        return ["invalid cached token subset"]
    return []


def objective_tokens(candidate, judgments):
    counters = {}
    for name, metric_id in (
        ("input", "input_tokens"),
        ("output", "output_tokens"),
        ("cached_input", "cached_input_tokens"),
    ):
        values = []
        for observations, observed_metric in [
            (candidate, metric_id),
            *((judgment, "routing_" + metric_id) for judgment in judgments),
        ]:
            matches = [
                row["measurement_value"]
                for row in observations
                if row["metric_id"] == observed_metric
            ]
            value = (
                sum(row["value"] for row in matches)
                if matches and all(row["kind"] == "known" for row in matches)
                else None
            )
            values.append(value)
        counters[name] = (
            {"value": int(sum(values))}
            if all(value is not None for value in values)
            else {"missing_reason": "not_reported"}
        )
    return counters


def independent_checks(case, grading):
    artifact = grading["artifact"]
    if artifact is None:
        return {}
    checks = evaluate_host_artifact(case["task_family"], case["expected"], artifact)
    if case["task_family"] == "implementation":
        checks["inputs_unchanged"] = grading["runtime"].get("inputs_unchanged") is True
    return checks


def paired_analysis(rows, protocol):
    result, errors = {}, []
    for family, settings in protocol["calibration"].items():
        family_rows = [row for row in rows if row["family"] == family]
        summaries = {}
        for name in BASELINES:
            pairs = [row for row in family_rows if name in row["arms"]]
            groups = {}
            for row in pairs:
                actual, baseline = row["arms"]["actual_discovery_route"], row["arms"][name]
                if not finite(actual["quality"], 0, 1) or not finite(baseline["quality"], 0, 1):
                    errors.append("paired outcome unknown")
                    continue
                if any(
                    baseline["critical_checks"].get(key) is True
                    and actual["critical_checks"].get(key) is False
                    for key in baseline["critical_checks"]
                ):
                    errors.append("additional measured critical failure: " + family + "/" + name)
                groups.setdefault(row["related_group"], []).append(
                    (
                        actual["quality"],
                        baseline["quality"] - actual["quality"],
                        actual["measurements"]["raw_cost"] - baseline["measurements"]["raw_cost"]
                        if all(
                            finite(arm["measurements"]["raw_cost"]) for arm in (actual, baseline)
                        )
                        else None,
                        actual["measurements"]["total"] - baseline["measurements"]["total"]
                        if all(finite(arm["measurements"]["total"]) for arm in (actual, baseline))
                        else None,
                    )
                )
            means = [
                tuple(
                    sum(pair[index] for pair in group) / len(group)
                    if all(pair[index] is not None for pair in group)
                    else None
                    for index in range(4)
                )
                for group in groups.values()
            ]
            count = len(means)
            summary = {
                "paired_cases": len(pairs),
                "independent_groups": count,
                "unknown_pairs": len(pairs) - sum(len(group) for group in groups.values()),
                "quality_lower_bound": None,
                "quality_loss_upper_bound": None,
                "cost_difference": None,
                "total_time_difference": None,
                "status": "insufficient_evidence",
            }
            if (
                count
                and not any(value is None for value in settings.values())
                and not calibration_errors(protocol)
            ):
                radius = math.sqrt(math.log(2 / (1 - settings["confidence"])) / (2 * count))
                summary.update(
                    quality_lower_bound=max(0, sum(v[0] for v in means) / count - radius),
                    quality_loss_upper_bound=min(1, sum(v[1] for v in means) / count + 2 * radius),
                    cost_difference=sum(v[2] for v in means) / count
                    if all(v[2] is not None for v in means)
                    else None,
                    total_time_difference=sum(v[3] for v in means) / count
                    if all(v[3] is not None for v in means)
                    else None,
                )
                if count < settings["minimum_pairs"]:
                    errors.append("family/group sample floor unmet: " + family + "/" + name)
                elif summary["quality_lower_bound"] < settings["quality_floor"] or summary[
                    "quality_loss_upper_bound"
                ] > min(settings["maximum_quality_loss"], settings["practical_equivalence"]):
                    errors.append(
                        "preregistered paired quality tolerance not established: "
                        + family
                        + "/"
                        + name
                    )
                else:
                    summary["status"] = "within_preregistered_tolerance"
            summaries[name] = summary
        result[family] = summaries
    return result, sorted(set(errors))


def configured_worker_errors(job, record, authority, protocol):
    from jevdrill.integrations.development import DevelopmentModel

    models = job["frozen_inputs"]["models"]
    plans = job["experiment"]["candidate_plans"]
    resources = {resource["id"]: resource for resource in protocol["resources"]}
    prompts, errors, reserved = [], [], 0
    for plan, profile in zip(plans, models, strict=True):
        revision = plan["resolved_model_revision"]
        if (
            revision not in authority["candidate_revisions"]
            or profile["model_revision"] != revision
            or profile["input_limit"] != 1047576
            or profile["output_limit"] != 512
            or profile["input_rate"] != (".40" if "mini" in revision else ".10")
            or profile["output_rate"] != ("1.60" if "mini" in revision else ".40")
            or profile["request_bytes_limit"] != 8192
            or profile["request_timeout_ms"] != (8000 if "mini" in revision else 30000)
        ):
            errors.append("provider profile differs from frozen official bounded configuration")
        reserved += DevelopmentModel(**profile).bound(
            record["admitted_at_ms"], record["deadline_ms"]
        )
        instructions = []
        for guidance in plan["required_guidance"] + plan["optional_guidance"]:
            resource = resources[guidance["resource_id"]]
            if (
                hashlib.sha256(resource["instructions"].encode()).hexdigest()
                != guidance["content_hash"]
            ):
                errors.append("executed guidance content differs from frozen public corpus")
            instructions.append(resource["instructions"])
        prompts.append(
            job["frozen_inputs"]["case"]["prompt"]
            + ("\nAuthorized guidance:\n" + "\n".join(instructions) if instructions else "")
        )
    expected = canonical_digest(
        {
            "case": job["frozen_inputs"]["case"],
            "profiles": models,
            "image": authority["image_id"],
            "url": "https://api.openai.com/v1",
            "execution_mode": "deferred",
            "prompts": prompts,
        }
    )
    if job["config"] != expected:
        errors.append("execution endpoint/configuration differs from trusted official adapter")
    if reserved != record["reserved_microusd"]:
        errors.append("provider full-context reservation differs from conservative ledger")
    return errors


def validate_study(study, protocol, authority=None, root=ROOT):
    """Missing authority/telemetry is an incomplete study, never a synthetic pass."""
    errors = []
    if authority is None:
        return ["new study authority missing"]
    errors.extend(authority_errors(authority, root))
    errors.extend(calibration_errors(protocol))
    try:
        directory = root / "evidence/EXPERIMENT/studies" / study["study_id"]
        frozen = read_artifact(directory, study["artifacts"]["exposure"])
        worker = read_artifact(directory, study["artifacts"]["worker"])
        controller = read_artifact(directory, study["artifacts"]["controller"])
        judgments = read_artifact(directory, study["artifacts"]["judgments"])
        expected_judge = canonical_digest(
            {
                "scope": authority["scope"] | {"operation": "route"},
                "authorization_revision": authority["authorization_revision"],
                "model": "jev-1.13.0",
                "context": 65536,
                "rate": "0.042/M",
                "output_rate": "0",
                "max_calls": authority["max_judgment_calls"],
                "total_spend_microusd": authority["judgment_spend_microusd"],
                "deadline_ms": frozen["deadline_ms"],
                "endpoint": "https://api.typesafe.ai/v1",
                "receive_bytes": 65536,
                "request_bytes": 8192,
                "retries": 0,
                **development_judgment_template_binding(),
            }
        )
        if judgments["revision"] != expected_judge:
            errors.append("navigation endpoint/configuration differs from trusted official adapter")
        lineage = read_artifact(directory, study["artifacts"]["lineage"])
        charged_judgments, used_plans = set(), set()
        if directory.name != authority["study_id"] or not directory.resolve().is_relative_to(
            (root / "evidence/EXPERIMENT/studies").resolve()
        ):
            raise ValueError("study directory outside authoritative grant")
        if (
            frozen["authority"] != authority
            or frozen["protocol"] != protocol
            or frozen["source_digest"] != source_digest(root)
        ):
            errors.append("immutable exposure/source/grant mismatch")
        if study["source_digest"] != source_digest(root):
            errors.append("study source changed")
        if (
            study["schema_version"] != 1
            or study["origin"] != "authorized_recorded_development"
            or study["protocol_digest"] != canonical_digest(protocol)
            or study["authority_digest"] != canonical_digest(authority)
            or authority["enabled"] is not True
            or study["promotion_authorized"] is not False
            or study["identities_blinded"] is not True
            or study["holdouts_opened"] is not False
        ):
            errors.append("study provenance or authority mismatch")
        cases = {case["id"]: case for case in protocol["cases"]}
        rows = study["cases"]
        if len(rows) != len(cases) or {row["case_id"] for row in rows} != set(cases):
            errors.append("study membership mismatch")
        for row in rows:
            case = cases[row["case_id"]]
            source_discovery, source_route = inputs(root, protocol, case)
            task_required = {
                ref["resource_id"]: {
                    key: value for key, value in ref.items() if key != "token_count"
                }
                | {"task_id": source_route["request"]["task_id"]}
                for ref in source_discovery["required_guidance"]
                + source_route["request"]["active_guidance"]
            }
            if (
                row["family"] != case["task_family"]
                or row["related_group"] != case["related_group"]
            ):
                errors.append("case family/group mismatch")
            discovery = parse_contract("DiscoveryResult", row["discovery"]).payload()
            decision = parse_contract("RoutingDecision", row["decision"]).payload()
            linked = decision["details"]["discovery_ref"]
            if linked is None or any(linked[key] != discovery["details"][key] for key in linked):
                errors.append("missing authoritative discovery/task lineage")
            if (
                discovery != lineage["discoveries"][discovery["details"]["discovery_id"]]
                or decision != lineage["decisions"][decision["details"]["routing_decision_id"]]
            ):
                errors.append(
                    "actual navigation/task record differs from frozen authoritative lineage"
                )
            plan = decision["execution_plan"]
            if (
                row["applied_configuration_digest"] != canonical_digest(plan)
                or row["routing_decision_id"] != decision["details"]["routing_decision_id"]
            ):
                errors.append("executed configuration differs from actual route")
            arms = row["arms"]
            expected = {
                name for name, applicable in case["baseline_applicability"].items() if applicable
            } | {"actual_discovery_route"}
            if set(arms) != expected:
                errors.append("missing applicable paired baseline")
            for name, arm in arms.items():
                evidence = read_artifact(directory, arm["artifact"])
                record = evidence["record"]
                job = worker[record["dispatch_token"]]
                stored = controller[record["comparison_experiment_id"]]
                errors.extend(configured_worker_errors(job, record, authority, protocol))
                if (
                    stored["record"] != record
                    or job["record"]["dispatch_token"] != record["dispatch_token"]
                    or job["experiment"] != stored["experiment"]
                    or job["record"]["experiment_digest"] != canonical_digest(stored["experiment"])
                    or not job["cleanup"]
                    or job["state"] != "completed"
                ):
                    errors.append("missing authoritative executed reservation/provider binding")
                configuration = next(
                    value
                    for value in stored["experiment"]["candidate_plans"]
                    if canonical_digest(value) == arm["configuration_digest"]
                )
                observation = next(
                    value
                    for value in job["observations"]
                    if value["execution_plan_id"] == configuration["execution_plan_id"]
                )
                arm_decision = evidence["decision"]
                if (
                    arm_decision
                    != lineage["decisions"][arm_decision["details"]["routing_decision_id"]]
                    or arm_decision["execution_plan"] != configuration
                ):
                    errors.append(
                        "baseline configuration differs from its authoritative task route"
                    )
                identity = (record["dispatch_token"], configuration["execution_plan_id"])
                if identity in used_plans:
                    errors.append("arm output reused or counted twice")
                used_plans.add(identity)
                ids = arm["judgment_call_ids"]
                if ids != evidence["judgment_call_ids"] or charged_judgments.intersection(ids):
                    errors.append("judgment dispatch reused or counted twice")
                charged_judgments.update(ids)
                nav_costs = [
                    metric(judgments["calls"][identity].get("measurements", []), "raw_token_cost")
                    for identity in ids
                ]
                candidate_cost = metric(observation["measurements"], "raw_token_cost")
                expected_cost = (
                    None
                    if candidate_cost is None or any(value is None for value in nav_costs)
                    else candidate_cost + sum(nav_costs)
                )
                if arm["measurements"]["raw_cost"] != expected_cost or any(
                    arm["measurements"][key] != evidence[key + "_ms"]
                    for key in ("discovery", "routing", "execution", "grading")
                ):
                    errors.append("objective cost/time differs from actual recorded measurements")
                if arm["measurements"]["tokens"] != objective_tokens(
                    observation["measurements"],
                    [judgments["calls"][identity].get("measurements", []) for identity in ids],
                ):
                    errors.append(
                        "token counters differ from actual charged candidate/navigation calls"
                    )
                optional = [value["resource_id"] for value in configuration["optional_guidance"]]
                retrieved = [
                    reference(resource)
                    | {
                        "role": "retrieved-" + resource["resource_id"],
                        "admission": resource["admission"],
                        "authority": "public-development-explicit-admission",
                        "task_id": source_route["request"]["task_id"],
                    }
                    for resource in source_discovery["catalog"]["resources"]
                    if resource["resource_id"] in case["objective"]
                ][:2]
                required = [
                    {key: value for key, value in ref.items() if key != "token_count"}
                    for ref in configuration["required_guidance"]
                ]
                if (
                    name
                    in {"fixed_default", "cheapest_feasible", "no_guidance", "simple_retrieval"}
                    and optional
                    or name in {"fixed_default", "cheapest_feasible", "no_guidance"}
                    and required != list(task_required.values())
                    or name == "fixed_default"
                    and configuration["model_id"] != authority["candidate_revisions"][0]
                    or name == "no_guidance"
                    and any(
                        configuration[key] != plan[key] for key in ("model_id", "native_effort")
                    )
                    or name == "simple_retrieval"
                    and required != retrieved
                ):
                    errors.append(
                        "baseline does not implement its preregistered selection condition"
                    )
                if (
                    canonical_digest(configuration) != arm["configuration_digest"]
                    or observation != evidence["provider"]
                    or observation["observed_model"] != configuration["resolved_model_revision"]
                    or observation["output"] != evidence["anonymous_output"]
                    or evidence["grading"]["artifact"] != arm["output"]
                    or evidence["grading"]["output_digest"]
                    != canonical_digest(observation["output"])
                    or arm["quality"] != evidence["grading"]["grade"]["quality"]
                ):
                    errors.append("immutable configuration/provider/grading mismatch")
                if arm["reservation_receipt_digest"] != canonical_digest(record) or arm[
                    "provider_receipt_digest"
                ] != canonical_digest(observation):
                    errors.append("forged provider/reservation receipt")
                errors.extend(telemetry_errors(arm["measurements"]))
                if (
                    arm["independent_grader_revision"] != protocol["evaluator_revision"]
                    or arm["rubric_revision"] != protocol["rubric_revision"]
                    or arm["related_group"] != case["related_group"]
                    or arm["split"] != "development"
                    or arm["execution_origin"] != "bounded_adapter_provider_receipt"
                    or arm["output_digest"] != canonical_digest(arm["output"])
                    or arm["critical_checks"] != independent_checks(case, evidence["grading"])
                    or not arm["reservation_receipt_digest"]
                    or not arm["provider_receipt_digest"]
                ):
                    errors.append("missing independent execution/outcome provenance")
                measurements = arm["measurements"]
                if set(measurements) != {
                    "discovery",
                    "routing",
                    "execution",
                    "grading",
                    "total",
                    "raw_cost",
                    "tokens",
                }:
                    errors.append("missing total selection overhead or objective telemetry")
                elif any(
                    measurements[key] is None
                    for key in ("discovery", "routing", "execution", "grading", "total", "raw_cost")
                ):
                    errors.append("required objective telemetry unknown")
                elif measurements["total"] < objective_duration(
                    *(measurements[key] for key in ("discovery", "routing", "execution", "grading"))
                ):
                    errors.append("omitted overhead")
                if name == "actual_discovery_route" and arm[
                    "configuration_digest"
                ] != canonical_digest(plan):
                    errors.append("actual arm configuration unlinked")
            if (
                row["exposure_receipt_digest"] != canonical_digest(frozen)
                or row["judgment_configuration_digest"] != judgments["revision"]
            ):
                errors.append("unbound exposure/navigation configuration")
            if (
                not row["exposure_receipt_digest"]
                or not row["judgment_configuration_digest"]
                or row["judgment_origin"] == "scripted"
            ):
                errors.append("unverified actual navigation or exposure")
        expected_judgments = judgments["calls"]
        if charged_judgments != set(expected_judgments):
            errors.append("navigation calls omitted from total objective overhead/cost")
        if used_plans != {
            (token, plan["execution_plan_id"])
            for token, value in worker.items()
            for plan in value.get("experiment", {}).get("candidate_plans", [])
        }:
            errors.append("candidate calls omitted from paired outcomes")
        actual_reservations = sum(
            value["record"]["reserved_microusd"] for value in controller.values()
        )
        ledger = study["reservation_ledger"]
        if (
            ledger["candidate_attempts"]
            != sum(len(value["experiment"]["candidate_plans"]) for value in controller.values())
            or ledger["judgment_attempts"] != len(expected_judgments)
            or ledger["reserved_microusd"]
            != actual_reservations
            + sum(value["reserved_microusd"] for value in expected_judgments.values())
            or any(
                value["state"] != "completed"
                or value["configuration_digest"] != judgments["revision"]
                or value["model"] != "jev-1.13.0"
                or value["reserved_microusd"] != 2753
                for value in expected_judgments.values()
            )
        ):
            errors.append("unbound whole-study durable ledger")
        analysis, paired_errors = paired_analysis(rows, protocol)
        errors.extend(paired_errors)
        if study["uncertainty_by_family"] != analysis:
            errors.append("uncertainty differs from independently derived paired groups")
        exposed = datetime.fromisoformat(frozen["exposed_at"])
        if not calibration_errors(protocol) and any(
            datetime.fromisoformat(value["frozen_at"]) >= exposed
            for value in protocol["calibration"].values()
        ):
            errors.append("calibration not frozen before exposure")
        if (
            ledger["authority_digest"] != canonical_digest(authority)
            or not finite(ledger["observed_duration_ms"], 0, authority["whole_study_deadline_ms"])
            or ledger["candidate_attempts"] > authority["max_candidate_calls"]
            or ledger["judgment_attempts"] > authority["max_judgment_calls"]
            or ledger["reserved_microusd"] > authority["total_spend_microusd"]
            or ledger["observed_duration_ms"] > authority["whole_study_deadline_ms"]
            or ledger["uncertain_refunded"]
            or not study["uncertainty_by_family"]
        ):
            errors.append("invalid whole-study reservation or uncertainty")
    except (KeyError, TypeError, ValueError, OSError, IndexError, StopIteration):
        errors.append("malformed or incomplete linked study")
    return sorted(set(errors))


def database_payloads(path, table, key, value):
    with closing(
        sqlite3.connect(f"file:{quote(str(path), safe='/:')}?mode=ro", uri=True)
    ) as database:
        return {
            identity: json.loads(payload)
            for identity, payload in database.execute(f"SELECT {key},{value} FROM {table}")
        }


def run_authorized_study(authority_path, root=ROOT, *, candidate_credential, judgment_credential):
    """Explicit future-grant driver. Never invoked by offline/native verification."""
    from jevdrill.experiments import Experiments
    from jevdrill.integrations.development import (
        DevelopmentJudge,
        DevelopmentModel,
        DevelopmentRunner,
        IndependentDevelopmentGrader,
    )
    from jevdrill.integrations.experiments import RestrictedContainerRunner
    from jevdrill.settings import resolve_settings

    authority = json.loads(authority_path.read_text())
    errors = authority_errors(authority, root, dispatch=True)
    if errors:
        raise ValueError("; ".join(errors))
    protocol = read_protocol(root)
    directory = root / "evidence/EXPERIMENT/studies" / authority["study_id"]
    directory.mkdir(parents=True, exist_ok=False)  # A used or uncertain grant is never resumed.
    started, observed_clock = time.monotonic(), [int(time.time() * 1000)]
    deadline_ms = observed_clock[0] + authority["whole_study_deadline_ms"]
    frozen = {
        "authority": authority,
        "protocol": protocol,
        "source_digest": source_digest(root),
        "exposed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "deadline_ms": deadline_ms,
    }
    artifacts = {"exposure": write_artifact(directory, "exposure.json", frozen)}
    scope = authority["scope"] | {"operation": "route"}

    def allowed(operation):
        now = int(time.time() * 1000)
        if now < observed_clock[0]:
            return False
        observed_clock[0] = now
        return (
            now < deadline_ms
            and json.loads(authority_path.read_text()) == authority
            and not authority_errors(authority, root, dispatch=True)
            and operation in authority["operations"]
        )

    judge = DevelopmentJudge(
        directory / "judgments.db",
        scope=scope,
        authorization_revision=authority["authorization_revision"],
        max_calls=authority["max_judgment_calls"],
        total_spend_microusd=authority["judgment_spend_microusd"],
        deadline_ms=deadline_ms,
        credential=judgment_credential,
        authorize=lambda request: (
            all(request[key] == scope[key] for key in ("project_id", "workspace_id", "producer"))
            and allowed(request["operation"])
        ),
    )
    container = RestrictedContainerRunner(authority["image_id"])
    store = SQLiteStorage(directory / "controller.db")
    app = Application(store, judgments=judge, discovery_judgments=judge)
    now = int(time.time() * 1000)
    expiry = int(datetime.fromisoformat(authority["expires_at"]).timestamp() * 1000)
    models = {
        revision: DevelopmentModel(
            revision,
            1047576,
            512,
            ".40" if "mini" in revision else ".10",
            "1.60" if "mini" in revision else ".40",
            "official-openai-20261009",
            now,
            expiry,
            request_timeout_ms=8000 if "mini" in revision else 30000,
        )
        for revision in authority["candidate_revisions"]
    }
    cases, grading_cases = {}, {}
    for case in protocol["cases"]:
        common = {
            "prompt": case["task_prompt"],
            "evaluator_ref": protocol["evaluator_revision"],
            "rubric_revision": protocol["rubric_revision"],
        }
        if case["task_family"] == "implementation":
            cases[case["id"]] = common | {
                "inputs": case["inputs"],
                "expected_answers": case["expected"]["results"],
            }
            grading_cases[case["id"]] = {
                "inputs": case["inputs"],
                "expected_answers": case["expected"]["results"],
            }
        else:
            cases[case["id"]] = common | {
                "task_family": case["task_family"],
                "expected": case["expected"],
            }
            grading_cases[case["id"]] = {
                "task_family": case["task_family"],
                "expected": case["expected"],
            }
    limits = {
        "max_candidates": 5,
        "max_concurrency": 1,
        "max_duration_ms": 120000,
        "cpu_limit": 2,
        "memory_limit_bytes": 2147483648,
        "per_experiment_spend": {"amount": "2.09925", "currency": "USD"},
        "daily_spend": {"amount": "26", "currency": "USD"},
    }
    task_ids = [
        str(uuid5(NAMESPACE_URL, protocol["revision"] + case["id"])) for case in protocol["cases"]
    ]
    grant = {
        "schema_version": "1",
        "authorization_revision": authority["authorization_revision"],
        "scope": scope,
        "enabled": True,
        "task_ids": task_ids,
        "allowed_providers": ["openai"],
        "allowed_harnesses": ["jevdrill"],
        "allowed_execution_paths": ["internal"],
        "allowed_isolation_refs": [container.image_id],
        "background_allowed": False,
        "local_only": False,
        "expires_at": authority["expires_at"],
        "limits": limits,
        "total_spend_microusd": authority["candidate_spend_microusd"],
    }
    service = Experiments(
        store,
        lambda request: grant if request == scope and allowed("experiment") else None,
        settings=lambda _: resolve_settings([("product", {"experiment_enabled": True})]),
    )
    runner = DevelopmentRunner(
        directory / "worker.db",
        models=models,
        cases=cases,
        container=container,
        credential=candidate_credential,
        authorize=lambda record: (
            allowed("experiment") and service.authorize_dispatch(scope, record)
        ),
    )
    service.runner = runner
    grader = IndependentDevelopmentGrader(
        cases=grading_cases,
        container=container,
        lock_path=directory / "grading.lock",
        duration_ms=30000,
        authorize=lambda key: key in grading_cases and allowed("experiment"),
    )
    rows, lineage = [], {"decisions": {}, "discoveries": {}}
    failure = None
    try:
        for case in protocol["cases"]:
            if not allowed("discover"):
                raise ValueError("study authority/deadline no longer current")
            case_started = time.monotonic()
            discovery, route = inputs(root, protocol, case)
            for envelope in (discovery["envelope"], route["request"]["envelope"]):
                envelope.update(
                    project_id=scope["project_id"],
                    workspace_id=scope["workspace_id"],
                    harness_id="jevdrill",
                    execution_target_id="linux_worker",
                )
            for bundle in (discovery, route):
                bundle["settings_layers"] = [
                    {
                        "source": "product",
                        "values": {
                            "retain_raw_tasks": True,
                            "retain_raw_outputs": True,
                            "local_analysis_enabled": True,
                            "experiment_enabled": True,
                        },
                    }
                ]
            store.deadline = time.monotonic() + max(
                0, (deadline_ms - int(time.time() * 1000)) / 1000
            )
            discovery["hard_constraints"]["context_token_limit"] = 2097152
            discovery["limits"].update(
                max_calls=32, max_input_tokens=2097152, output_planning_reservation=0
            )
            discovery["judgment_policy"].update(
                max_calls=32,
                max_input_tokens=2097152,
                output_planning_reservation=0,
                model_revision="jev-1.13.0",
            )
            route["request"]["hard_constraints"].update(
                context_token_limit=1047576,
                execution_token_limits={"input_tokens": 1047576, "output_tokens": 512},
            )
            route["judgment_policy"] = {
                "enabled": True,
                "cloud_allowed": True,
                "max_calls": 32,
                "max_candidates": 32,
                "max_input_tokens": 2097152,
                "max_output_tokens": 64,
                "spending_ceiling": None,
                "rates": None,
                "model_revision": "jev-1.13.0",
                "function_revision": JUDGMENT_FUNCTION_REVISION,
                "token_counter_revision": "utf8-bytes-upper-bound-v1",
            }
            route["completion_time_limit_ms"] = case["study_completion_time_limit_ms"]
            route["inventory"].update(
                target="linux_worker",
                source_version="official-pinned-development-20261009",
                expires_at=authority["expires_at"],
            )
            for index, candidate in enumerate(route["inventory"]["candidates"]):
                revision = authority["candidate_revisions"][1 if index == 0 else 0]
                candidate.update(
                    model_id=revision,
                    resolved_model_revision=revision,
                    provider="openai",
                    access_route="baml_development",
                    local=False,
                    context_token_limit=1047576,
                    output_token_limit=512,
                    execution_token_limits={"input_tokens": 1047576, "output_tokens": 512},
                    source="official-pinned-development-profile-20261009",
                    source_version="official-20261009",
                    quality_sufficient=None,
                    completion_time_ms=30000 if index == 0 else 8000,
                    evidence_strength="unknown",
                    evidence_refs=[],
                    verified_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    expires_at=authority["expires_at"],
                )
                candidate.pop("source_version", None)
                candidate["rates"].update(
                    input_rate="0.00000010" if index == 0 else "0.00000040",
                    output_rate="0.00000040" if index == 0 else "0.00000160",
                    revision="official-openai-20261009",
                    expires_at=authority["expires_at"],
                )
            runner.guidance.update(
                {
                    (resource["resource_id"], resource["revision"]): resource
                    for resource in discovery["catalog"]["resources"]
                }
            )
            before_calls = set(
                database_payloads(judge.path, "judgment_calls", "identity", "payload")
            )
            before = time.monotonic()
            selected = app.discover(discovery)
            selected_ids = {
                resource["resource_id"] for resource in selected["details"]["guidance_refs"]
            }
            for candidate in route["inventory"]["candidates"]:
                candidate["guidance_options"] = [
                    reference(resource)
                    | {
                        "role": "optional-" + resource["resource_id"],
                        "admission": resource["admission"],
                        "authority": "public-development-explicit-admission",
                        "task_id": route["request"]["task_id"],
                        "token_count": None,
                    }
                    for resource in discovery["catalog"]["resources"]
                    if resource["resource_id"] in selected_ids
                ]
            discovery_ms = (time.monotonic() - before) * 1000
            lineage["discoveries"][selected["details"]["discovery_id"]] = selected
            before = time.monotonic()
            decision = app.route(
                {
                    "schema_version": "2",
                    "route_inputs": route,
                    "discovery_ref": {
                        key: selected["details"][key]
                        for key in ("discovery_id", "work_objective_id", "trace_digest")
                    },
                }
            )
            route_ms = (time.monotonic() - before) * 1000
            if decision["status"] != "ready":
                raise ValueError("actual development route incomplete")
            decisions = {"actual_discovery_route": decision}
            navigation_times = {"actual_discovery_route": (discovery_ms, route_ms)}
            arm_calls = {
                "actual_discovery_route": sorted(
                    set(database_payloads(judge.path, "judgment_calls", "identity", "payload"))
                    - before_calls
                )
            }
            for name in ("fixed_default", "cheapest_feasible", "no_guidance", "simple_retrieval"):
                if not case["baseline_applicability"][name]:
                    continue
                baseline = copy.deepcopy(route)
                envelope = baseline["request"]["envelope"]
                baseline["request"]["versions"]["context_revision"] = (
                    protocol["revision"] + ":" + name
                )
                envelope.update(
                    request_id=str(uuid5(NAMESPACE_URL, case["id"] + name)),
                    idempotency_key=case["id"] + ":" + name,
                )
                if name == "fixed_default":
                    baseline["inventory"]["candidates"] = [baseline["inventory"]["candidates"][1]]
                if name == "no_guidance":
                    baseline["inventory"]["candidates"] = [
                        candidate
                        for candidate in baseline["inventory"]["candidates"]
                        if candidate["model_id"] == decision["execution_plan"]["model_id"]
                    ]
                baseline["request"]["active_guidance"] = copy.deepcopy(
                    decision["execution_plan"]["required_guidance"]
                )
                if name == "simple_retrieval":
                    baseline["request"]["active_guidance"] = [
                        reference(resource)
                        | {
                            "role": "retrieved-" + resource["resource_id"],
                            "admission": resource["admission"],
                            "authority": "public-development-explicit-admission",
                            "task_id": route["request"]["task_id"],
                            "token_count": None,
                        }
                        for resource in discovery["catalog"]["resources"]
                        if resource["resource_id"] in case["objective"]
                    ][:2]
                for candidate in baseline["inventory"]["candidates"]:
                    candidate["guidance_options"] = []
                before_calls = set(
                    database_payloads(judge.path, "judgment_calls", "identity", "payload")
                )
                before = time.monotonic()
                decisions[name] = app.route(baseline)
                navigation_times[name] = (0, (time.monotonic() - before) * 1000)
                arm_calls[name] = sorted(
                    set(database_payloads(judge.path, "judgment_calls", "identity", "payload"))
                    - before_calls
                )
                if decisions[name]["status"] != "ready":
                    raise ValueError("applicable baseline incomplete")
            names = sorted(
                decisions, key=lambda name: canonical_digest({"case": case["id"], "arm": name})
            )
            plans = [decisions[name]["execution_plan"] for name in names]
            for result in decisions.values():
                lineage["decisions"][result["details"]["routing_decision_id"]] = result
            experiment_id = str(uuid5(NAMESPACE_URL, authority["study_id"] + case["id"]))
            store.deadline = time.monotonic() + max(
                0,
                min(
                    180 - (time.monotonic() - case_started),
                    (deadline_ms - int(time.time() * 1000)) / 1000,
                ),
            )
            experiment = {
                "schema_version": "1",
                "comparison_experiment_id": experiment_id,
                "task_id": route["request"]["task_id"],
                "context_ref": case["id"],
                "context_hash": canonical_digest(cases[case["id"]]),
                "candidate_plans": plans,
                "optimization_objectives": [route["request"]["optimization_objective"]],
                "assignment_policy": "frozen-anonymous-five-arm-development-v1",
                "assignment_probabilities": {
                    plan["execution_plan_id"]: 1 / len(plans) for plan in plans
                },
                "authorization_revision": None,
                "host_accepted": False,
                "isolation_ref": container.image_id,
                "execution_path": "internal",
                "experiment_state": "proposed",
                "evaluator_ref": protocol["evaluator_revision"],
                "rubric_revision": protocol["rubric_revision"],
                "limits": limits,
            }
            service.handle(
                {
                    "schema_version": "1",
                    "scope": scope,
                    "idempotency_key": case["id"],
                    "action": "propose",
                    "comparison_experiment_id": None,
                    "proposal": {
                        "experiment": experiment,
                        "task_group": case["related_group"],
                        "uncertainty_rank": 1,
                        "benefit_rank": 1,
                        "estimated_cost_microusd": None,
                    },
                }
            )
            request = {
                "schema_version": "1",
                "scope": scope,
                "comparison_experiment_id": experiment_id,
                "action": "admit",
                "background": False,
            }
            admitted = service.execute(request)
            if admitted["status"] != "recorded":
                raise ValueError("bounded admission denied")
            accepted = service.execute(request | {"action": "advance"})["record"]
            before = time.monotonic()
            runner.run(accepted)
            record = service.execute(request | {"action": "advance"})["record"]
            execution_ms = (time.monotonic() - before) * 1000
            observations = runner.retained_observations(record)["observations"]
            if len(observations) != len(plans) or record["execution_status"] != "completed":
                raise ValueError("bounded candidate comparison incomplete")
            grading, grading_ms = [], []
            for offset in range(0, len(observations), 2):
                outputs = [item["output"] for item in observations[offset : offset + 2]]
                count = len(outputs)
                before = time.monotonic()
                grader.duration_ms = min(
                    30000,
                    int(
                        max(
                            0,
                            min(
                                180 - (time.monotonic() - case_started),
                                (deadline_ms - int(time.time() * 1000)) / 1000,
                            ),
                        )
                        * 1000
                    ),
                )
                if grader.duration_ms <= 0:
                    raise ValueError("case/study grading deadline reached")
                grader.grade(case["id"], outputs + [None] * (2 - count))
                duration = (time.monotonic() - before) * 1000
                grading.extend(copy.deepcopy(grader.last_artifacts[:count]))
                grading_ms.extend([duration / count] * count)
            arms = {}
            call_receipts = database_payloads(judge.path, "judgment_calls", "identity", "payload")
            provider_durations = [
                metric(observation["measurements"], "completion_time_ms")
                for observation in observations
            ]
            extra_execution_ms = max(
                0, execution_ms - sum(value or 0 for value in provider_durations)
            ) / len(plans)
            for name, plan, observation, grade, elapsed in zip(
                names, plans, observations, grading, grading_ms, strict=True
            ):
                disc_ms, routing_ms = navigation_times[name]
                evidence = {
                    "record": record,
                    "provider": observation,
                    "anonymous_output": observation["output"],
                    "grading": grade,
                    "decision": decisions[name],
                    "discovery_ms": disc_ms,
                    "routing_ms": routing_ms,
                    "grading_ms": elapsed,
                    "execution_ms": metric(observation["measurements"], "completion_time_ms")
                    + extra_execution_ms,
                    "judgment_call_ids": arm_calls[name],
                }
                artifact = write_artifact(directory, case["id"] + "-" + name + ".json", evidence)
                actual_execution = evidence["execution_ms"]
                nav_metrics = [
                    call_receipts[identity]["measurements"] for identity in arm_calls[name]
                ]
                tokens = objective_tokens(observation["measurements"], nav_metrics)
                nav_cost = (
                    None
                    if any(metric(measured, "raw_token_cost") is None for measured in nav_metrics)
                    else sum(metric(measured, "raw_token_cost") for measured in nav_metrics)
                )
                provider_cost = metric(observation["measurements"], "raw_token_cost")
                total = (
                    None
                    if actual_execution is None
                    else objective_duration(disc_ms, routing_ms, actual_execution, elapsed)
                )
                arms[name] = {
                    "independent_grader_revision": protocol["evaluator_revision"],
                    "rubric_revision": protocol["rubric_revision"],
                    "related_group": case["related_group"],
                    "split": "development",
                    "execution_origin": "bounded_adapter_provider_receipt",
                    "output": grade["artifact"],
                    "output_digest": canonical_digest(grade["artifact"]),
                    "quality": grade["grade"]["quality"],
                    "critical_checks": independent_checks(case, grade),
                    "reservation_receipt_digest": canonical_digest(record),
                    "provider_receipt_digest": canonical_digest(observation),
                    "configuration_digest": canonical_digest(plan),
                    "artifact": artifact,
                    "judgment_call_ids": arm_calls[name],
                    "measurements": {
                        "discovery": disc_ms,
                        "routing": routing_ms,
                        "execution": actual_execution,
                        "grading": elapsed,
                        "total": total,
                        "raw_cost": None
                        if nav_cost is None or provider_cost is None
                        else provider_cost + nav_cost,
                        "tokens": tokens,
                    },
                }
            rows.append(
                {
                    "case_id": case["id"],
                    "family": case["task_family"],
                    "related_group": case["related_group"],
                    "discovery": selected,
                    "decision": decision,
                    "routing_decision_id": decision["details"]["routing_decision_id"],
                    "applied_configuration_digest": canonical_digest(decision["execution_plan"]),
                    "arms": arms,
                    "exposure_receipt_digest": canonical_digest(frozen),
                    "judgment_configuration_digest": judge.revision,
                    "judgment_origin": "bounded_model_adapter",
                    "elapsed_ms": (time.monotonic() - case_started) * 1000,
                    "worker_and_cleanup_ms": execution_ms,
                }
            )
            if (
                paired_analysis(rows, protocol)[1]
                or (time.monotonic() - case_started) * 1000 > 180000
            ):
                raise ValueError("critical/unknown evidence or case limit reached")
    except (ValueError, OSError, KeyError, TypeError) as error:
        failure = type(error).__name__  # Provider/credential exception text is never recorded.
    finally:
        worker = database_payloads(runner.path, "development_runs", "token", "payload")
        controller = database_payloads(store.path, "experiment_executions", "identity", "payload")
        calls = database_payloads(judge.path, "judgment_calls", "identity", "payload")
        artifacts.update(
            worker=write_artifact(directory, "worker.json", worker),
            controller=write_artifact(directory, "controller.json", controller),
            judgments=write_artifact(
                directory, "judgments.json", {"revision": judge.revision, "calls": calls}
            ),
            lineage=write_artifact(directory, "lineage.json", lineage),
        )
        study = {
            "schema_version": 1,
            "study_id": authority["study_id"],
            "origin": "authorized_recorded_development",
            "source_digest": frozen["source_digest"],
            "protocol_digest": canonical_digest(protocol),
            "authority_digest": canonical_digest(authority),
            "promotion_authorized": False,
            "identities_blinded": True,
            "holdouts_opened": False,
            "cases": rows,
            "artifacts": artifacts,
            "uncertainty_by_family": paired_analysis(rows, protocol)[0],
            "failure": failure,
            "reservation_ledger": {
                "authority_digest": canonical_digest(authority),
                "candidate_attempts": sum(
                    len(value["experiment"]["candidate_plans"]) for value in controller.values()
                ),
                "judgment_attempts": len(calls),
                "reserved_microusd": sum(
                    value["record"]["reserved_microusd"] for value in controller.values()
                )
                + sum(value["reserved_microusd"] for value in calls.values()),
                "observed_duration_ms": (time.monotonic() - started) * 1000,
                "uncertain_refunded": False,
            },
        }
        write_artifact(directory, "study.json", study)
    return study


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-only", action="store_true")
    parser.add_argument("--study", type=Path)
    parser.add_argument("--authority-preview", action="store_true")
    parser.add_argument("--run-authorized-study", type=Path)
    args = parser.parse_args()
    if args.authority_preview:
        print(json.dumps(authority_preview(), indent=2))
        return 0
    if args.run_authorized_study is not None:
        import os

        report = run_authorized_study(
            args.run_authorized_study,
            candidate_credential=lambda: os.environ["OPENAI_API_KEY"],
            judgment_credential=lambda: os.environ["TYPESAFE_API_KEY"],
        )
        print(
            json.dumps(
                {
                    "study_id": report["study_id"],
                    "failure": report["failure"],
                    "status": "recorded_development_only",
                }
            )
        )
        return int(report["failure"] is not None)
    if args.offline_only:
        report = offline()
        output = ROOT / "evidence/EXPERIMENT/discovery-offline.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({key: value for key, value in report.items() if key != "cases"}))
        return int(report["status"] != "passed")
    if args.study is None:
        parser.error("Use --offline-only or provide a separately authorized --study receipt")
    authority_path = ROOT / "evidence/EXPERIMENT/study-authorization.json"
    authority = json.loads(authority_path.read_text()) if authority_path.is_file() else None
    errors = validate_study(json.loads(args.study.read_text()), read_protocol(), authority)
    print(json.dumps({"status": "blocked" if errors else "passed", "errors": errors}))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
