"""Pure measurement aggregation and split checks; no routing or promotion effects."""

import json
import math
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from datetime import datetime
from decimal import Decimal
from typing import Any

from .contracts import ContractError, ValidatedDocument, canonical_digest, parse_contract


def cost_per_accepted(
    costs: Sequence[Decimal | None], accepted: Sequence[bool | None]
) -> Decimal | None:
    if len(costs) != len(accepted):
        raise ValueError("cost/outcome lengths differ")
    if any(value is None for value in costs) or any(value is None for value in accepted):
        return None
    count = sum(value is True for value in accepted)
    if count == 0:
        return None
    total = sum((value for value in costs if value is not None), Decimal(0))
    return total / count


def elapsed_union_ms(intervals: Sequence[tuple[int, int]]) -> int:
    """Elapsed occupied wall time, counting overlapping candidate intervals once."""
    result = 0
    end: int | None = None
    for start, stop in sorted(intervals):
        if stop < start:
            raise ValueError("negative interval")
        result += max(0, stop - (start if end is None else max(start, end)))
        end = stop if end is None else max(end, stop)
    return result


def token_total(
    input_tokens: int | None,
    output_tokens: int | None,
    cached_input_tokens: int | None = None,
    reasoning_output_tokens: int | None = None,
) -> int | None:
    """Aggregate counters whose declared semantics make cache/reasoning subsets."""
    for count in (input_tokens, output_tokens, cached_input_tokens, reasoning_output_tokens):
        if count is not None and count < 0:
            raise ValueError("negative token count")
    if input_tokens is None or output_tokens is None:
        return None
    if cached_input_tokens is not None and cached_input_tokens > input_tokens:
        raise ValueError("cache subset exceeds input")
    if reasoning_output_tokens is not None and reasoning_output_tokens > output_tokens:
        raise ValueError("reasoning subset exceeds output")
    return input_tokens + output_tokens


def require_comparable(left: ValidatedDocument, right: ValidatedDocument) -> None:
    if left.contract_name != "Measurement" or right.contract_name != "Measurement":
        raise ContractError("measurement contracts required")
    a, b = left.payload(), right.payload()
    keys = ("metric_id", "metric_version", "method", "scope", "source", "counting_semantics")
    if any(a[key] != b[key] for key in keys):
        raise ContractError("incompatible metric definitions or provenance")
    av, bv = a["measurement_value"], b["measurement_value"]
    if av["kind"] != "known" or bv["kind"] != "known":
        raise ContractError("missing measurement")
    if av["unit"] != bv["unit"]:
        raise ContractError("incompatible units")


def validate_splits(
    assignments: Mapping[str, Sequence[str]],
    groups: Mapping[str, str],
    exposed_tasks: AbstractSet[str],
) -> None:
    allowed = {
        "development",
        "validation",
        "policy_holdout",
        "policy_regression",
        "release_holdout",
    }
    if set(assignments) - allowed:
        raise ValueError("unknown split")
    seen: dict[str, str] = {}
    group_split: dict[str, str] = {}
    for split, tasks in assignments.items():
        for task in tasks:
            if task not in groups or task in seen:
                raise ValueError("missing grouping or duplicated task")
            group = groups[task]
            if group in group_split and group_split[group] != split:
                raise ValueError("related-task leakage")
            if split in {"release_holdout", "policy_holdout"} and task in exposed_tasks:
                raise ValueError("holdout already exposed")
            seen[task] = split
            group_split[group] = split


def evaluate_host_artifact(
    family: str, expected: Mapping[str, object], artifact: Mapping[str, object]
) -> dict[str, bool]:
    """Independent checks for versioned synthetic HOST artifacts, not model quality scores.

    Expected results come from the frozen rubric, never from candidate-written tests.
    Review findings and documentation assertions use structured synthetic identifiers;
    these checks do not claim to judge arbitrary prose.
    """

    def matches(value: object, reference: object) -> bool:
        return json.dumps(value, sort_keys=True, allow_nan=False) == json.dumps(
            reference, sort_keys=True, allow_nan=False
        )

    if family == "implementation":
        return {"regression_results": matches(artifact.get("results"), expected["results"])}
    if family == "review":
        findings = artifact.get("findings")
        required = expected["findings"]
        if not isinstance(findings, dict) or not isinstance(required, dict):
            return {"defect_recall": False, "false_positives": False, "severity_action": False}
        return {
            "defect_recall": set(required) <= set(findings),
            "false_positives": set(findings) <= set(required),
            "severity_action": all(
                matches(findings.get(key), value) for key, value in required.items()
            ),
        }
    if family == "documentation":
        return {
            key: matches(artifact.get(key), expected[key])
            for key in ("facts", "requirements", "references", "examples")
        }
    raise ValueError("unknown HOST task family")


def score_review_components(
    output: str | None, expected: Mapping[str, Any], allowed_labels: Sequence[str]
) -> dict[str, Any]:
    """V3 retains valid components even when other fields are absent or malformed."""
    result: dict[str, Any] = {
        "evaluator_revision": "review-components-v3",
        "format_valid": False,
        "issues_valid": False,
        "example_present": False,
        "defects_found": None,
        "defects_missed": None,
        "false_alarms": None,
        "defect_recall": None,
        "example_correct": None,
        "critical_pass": False,
    }

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate review field")
            value[key] = item
        return value

    try:
        actual = json.loads(output, object_pairs_hook=unique_object) if output is not None else None
    except (ValueError, TypeError):
        return result
    if not isinstance(actual, dict):
        return result
    result["example_present"] = "example" in actual
    if result["example_present"]:
        try:
            result["example_correct"] = canonical_digest(actual["example"]) == canonical_digest(
                expected["example"]
            )
        except (ValueError, TypeError):
            pass
    labels = actual.get("issues")
    if (
        isinstance(labels, list)
        and all(type(label) is str and label in allowed_labels for label in labels)
        and len(set(labels)) == len(labels)
    ):
        found, required = set(labels), set(expected["issues"])
        result.update(
            issues_valid=True,
            defects_found=sorted(found & required),
            defects_missed=sorted(required - found),
            false_alarms=sorted(found - required),
            defect_recall=len(found & required) / len(required) if required else None,
        )
    result["format_valid"] = (
        set(actual) == {"issues", "example"}
        and result["issues_valid"]
        and result["example_correct"] is not None
    )
    result["critical_pass"] = bool(
        result["format_valid"]
        and not result["defects_missed"]
        and not result["false_alarms"]
        and result["example_correct"]
    )
    return result


def grade_development_artifact(
    family: str, output: str | None, expected: Mapping[str, object]
) -> dict[str, Any]:
    """Check frozen structured review/docs outputs independently of candidate claims."""
    if family not in {"review", "documentation"}:
        raise ContractError("development_artifact_family_invalid")
    keys = (
        {"findings"} if family == "review" else {"facts", "requirements", "references", "examples"}
    )
    if set(expected) != keys:
        raise ContractError("development_artifact_recipe_invalid")
    if output is None:
        return {"quality": None, "critical": {}}

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate artifact field")
            result[key] = value
        return result

    try:
        artifact = json.loads(
            output,
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite artifact")),
        )
        valid = isinstance(artifact, dict) and set(artifact) == keys
        checks = evaluate_host_artifact(family, expected, artifact if valid else {})
        checks["format_valid"] = valid
    except (ValueError, TypeError):
        checks = evaluate_host_artifact(family, expected, {})
        checks["format_valid"] = False
    return {"quality": sum(checks.values()) / len(checks), "critical": checks}


def evaluate_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Assess reported paired evidence; a quality result never authorizes promotion.

    Quality scores must be rubric-defined values in [0, 1]. Distinct related groups
    are the sampling units. Simultaneous one-sided Hoeffding bounds conservatively
    account for uncertainty in quality and paired loss; calibration must precede
    exposure. The caller remains responsible for verifying the reported provenance.
    """
    evaluation = parse_contract("PolicyEvaluation", payload).payload()
    calibration = evaluation["calibration"]
    cases = evaluation["cases"]
    result: dict[str, Any] = {
        "schema_version": "1",
        "classification": "insufficient_evidence",
        "calibration_revision": None
        if calibration is None
        else calibration["calibration_revision"],
        "evidence_digest": canonical_digest(evaluation),
        "pair_count": len(cases),
        "critical_regressions": [],
        "reasons": [],
        "candidate_quality_lower_bound": None,
        "quality_loss_upper_bound": None,
        "promotion_authorized": False,
    }

    def finish(classification: str, *reasons: str) -> dict[str, Any]:
        result.update(classification=classification, reasons=list(reasons))
        return dict(parse_contract("PolicyAssessment", result).payload())

    if calibration is None:
        return finish("insufficient_evidence", "calibration_missing")
    binding = ("task_family", "evaluator_ref", "rubric_revision", "dataset_revision")
    if any(evaluation[key] != calibration[key] for key in binding):
        return finish("non_comparable", "calibration_binding_mismatch")
    if not all(
        calibration[key].strip()
        for key in (
            "calibration_revision",
            "calibration_source",
            "evaluator_ref",
            "rubric_revision",
            "dataset_revision",
        )
    ):
        return finish("insufficient_evidence", "calibration_provenance_missing")
    critical = set(calibration["critical_requirements"])
    if any(not item.strip() for item in critical):
        return finish("insufficient_evidence", "critical_definition_missing")
    if len({case["case_id"] for case in cases}) != len(cases) or len(
        {case["related_group"] for case in cases}
    ) != len(cases):
        return finish("non_comparable", "duplicate_or_related_samples")
    if any(not case["case_id"].strip() or not case["related_group"].strip() for case in cases):
        return finish("non_comparable", "sample_identity_missing")
    if any(
        set(case[key]) != critical
        for case in cases
        for key in ("baseline_critical", "candidate_critical")
    ):
        return finish("insufficient_evidence", "critical_checks_missing_or_changed")
    result["critical_regressions"] = sorted(
        case["case_id"] + ":" + requirement
        for case in cases
        for requirement in critical
        if case["baseline_critical"][requirement] and not case["candidate_critical"][requirement]
    )
    if result["critical_regressions"]:
        return finish("critical_regression", "new_critical_failure")
    if any(not all(case["candidate_critical"].values()) for case in cases):
        return finish("quality_regression", "mandatory_requirement_failed")
    if any(case["split"] == "release_holdout" for case in cases):
        return finish("non_comparable", "release_holdout_not_permitted")
    if any(case["split"] not in {"policy_holdout", "policy_regression"} for case in cases):
        return finish("insufficient_evidence", "policy_evaluation_splits_missing")
    if {case["split"] for case in cases} != {"policy_holdout", "policy_regression"}:
        return finish("insufficient_evidence", "both_policy_splits_required")
    frozen = datetime.fromisoformat(calibration["frozen_at"])
    if any(datetime.fromisoformat(case["exposed_at"]) <= frozen for case in cases):
        return finish("non_comparable", "calibration_not_frozen_before_exposure")
    if not evaluation["identities_blinded"]:
        return finish("insufficient_evidence", "evaluation_not_blinded")
    if evaluation["evidence_origin"] != "controlled":
        return finish("insufficient_evidence", "controlled_evidence_required")
    if any(
        case[key] is None for case in cases for key in ("baseline_quality", "candidate_quality")
    ):
        return finish("insufficient_evidence", "quality_observation_missing")
    # Require each split to meet the calibration independently. Pooling a large
    # holdout with a tiny regression set must not hide a weak regression result.
    bounds = []
    alpha = 1 - calibration["confidence"]
    for split in ("policy_holdout", "policy_regression"):
        rows = [case for case in cases if case["split"] == split]
        count = len(rows)
        if count < calibration["minimum_pairs"]:
            return finish("insufficient_evidence", "minimum_pairs_not_met_in_each_split")
        # Four bounds (quality and loss in two splits) share the error budget.
        quality_radius = math.sqrt(math.log(4 / alpha) / (2 * count))
        loss_radius = 2 * quality_radius
        quality = sum(case["candidate_quality"] for case in rows) / count
        loss = sum(case["baseline_quality"] - case["candidate_quality"] for case in rows) / count
        bounds.append((max(0.0, quality - quality_radius), min(1.0, loss + loss_radius)))
        if quality < calibration["quality_floor"] or loss > calibration["maximum_quality_loss"]:
            return finish("quality_regression", "observed_quality_floor_or_loss_breached")
    result["candidate_quality_lower_bound"] = min(bound[0] for bound in bounds)
    result["quality_loss_upper_bound"] = max(bound[1] for bound in bounds)
    if (
        result["candidate_quality_lower_bound"] < calibration["quality_floor"]
        or result["quality_loss_upper_bound"] > calibration["maximum_quality_loss"]
    ):
        return finish("insufficient_evidence", "uncertainty_exceeds_quality_limits")
    return finish("quality_gate_passed", "reported_quality_evidence_within_calibration")
