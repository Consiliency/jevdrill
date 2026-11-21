import copy

import pytest

from jevdrill.contracts import ContractError
from jevdrill.evaluation import evaluate_policy


def evaluation(count=2):
    return {
        "schema_version": "1",
        "task_family": "implementation",
        "evaluator_ref": "independent-tests-v1",
        "rubric_revision": "required-and-quality-v1",
        "dataset_revision": "test-only-v1",
        "identities_blinded": True,
        "evidence_origin": "controlled",
        "calibration": {
            "schema_version": "1",
            "calibration_revision": "test-only-calibration",
            "task_family": "implementation",
            "evaluator_ref": "independent-tests-v1",
            "rubric_revision": "required-and-quality-v1",
            "dataset_revision": "test-only-v1",
            "calibration_source": "synthetic-unit-test-settings-not-operational-thresholds",
            "frozen_at": "2026-09-01T00:00:00Z",
            "critical_requirements": ["authorization", "correctness"],
            "quality_floor": 0.8,
            "maximum_quality_loss": 0.05,
            "minimum_pairs": 2,
            "confidence": 0.95,
        },
        "cases": [
            {
                "case_id": str(i),
                "related_group": str(i),
                "split": "policy_holdout" if i % 2 else "policy_regression",
                "exposed_at": "2026-09-02T00:00:00Z",
                "baseline_quality": 0.5,
                "candidate_quality": 1.0,
                "baseline_critical": {"authorization": True, "correctness": True},
                "candidate_critical": {"authorization": True, "correctness": True},
                "baseline_measurements": [],
                "candidate_measurements": [],
            }
            for i in range(count)
        ],
    }


def test_critical_regression_cannot_be_offset_by_average_quality_or_savings():
    payload = evaluation(120)
    payload["cases"][0]["candidate_critical"]["authorization"] = False
    before = copy.deepcopy(payload)
    result = evaluate_policy(payload)
    assert result["classification"] == "critical_regression"
    assert result["critical_regressions"] == ["0:authorization"]
    assert result["promotion_authorized"] is False
    assert payload == before


def test_existing_baseline_critical_failure_does_not_authorize_mandatory_failure():
    payload = evaluation(120)
    payload["cases"][0]["candidate_critical"]["correctness"] = False
    payload["cases"][0]["baseline_critical"]["correctness"] = False
    result = evaluate_policy(payload)
    assert result["classification"] == "quality_regression"
    assert result["critical_regressions"] == []
    assert result["reasons"] == ["mandatory_requirement_failed"]


@pytest.mark.parametrize("family", ["implementation", "review", "documentation"])
def test_quality_gate_uses_task_family_calibration_and_never_authorizes_promotion(family):
    payload = evaluation(120)
    payload["task_family"] = payload["calibration"]["task_family"] = family
    result = evaluate_policy(payload)
    assert result["classification"] == "quality_gate_passed"
    assert 0.8 < result["candidate_quality_lower_bound"] < 1.0
    assert result["quality_loss_upper_bound"] < 0.05
    assert result["promotion_authorized"] is False
    payload["calibration"]["quality_floor"] = 0.99
    assert evaluate_policy(payload)["classification"] == "insufficient_evidence"


@pytest.mark.parametrize(
    "change,classification,reason",
    [
        (lambda p: p.update(calibration=None), "insufficient_evidence", "calibration_missing"),
        (
            lambda p: p["calibration"].update(task_family="review"),
            "non_comparable",
            "calibration_binding_mismatch",
        ),
        (
            lambda p: p["calibration"].update(calibration_source=""),
            "insufficient_evidence",
            "calibration_provenance_missing",
        ),
        (
            lambda p: p["cases"][0].update(related_group="1"),
            "non_comparable",
            "duplicate_or_related_samples",
        ),
        (
            lambda p: p["cases"][0]["candidate_critical"].pop("correctness"),
            "insufficient_evidence",
            "critical_checks_missing_or_changed",
        ),
        (
            lambda p: p["cases"][0].update(split="release_holdout"),
            "non_comparable",
            "release_holdout_not_permitted",
        ),
        (
            lambda p: p["cases"][0].update(split="development"),
            "insufficient_evidence",
            "policy_evaluation_splits_missing",
        ),
        (
            lambda p: p["cases"][0].update(exposed_at="2026-09-01T00:00:00Z"),
            "non_comparable",
            "calibration_not_frozen_before_exposure",
        ),
        (
            lambda p: p.update(identities_blinded=False),
            "insufficient_evidence",
            "evaluation_not_blinded",
        ),
        (
            lambda p: p.update(evidence_origin="synthetic"),
            "insufficient_evidence",
            "controlled_evidence_required",
        ),
        (
            lambda p: p.update(evidence_origin="observational"),
            "insufficient_evidence",
            "controlled_evidence_required",
        ),
        (
            lambda p: p["cases"][0].update(candidate_quality=None),
            "insufficient_evidence",
            "quality_observation_missing",
        ),
    ],
)
def test_missing_incompatible_exposed_or_noncontrolled_evidence_never_passes(
    change, classification, reason
):
    payload = evaluation(120)
    change(payload)
    result = evaluate_policy(payload)
    assert result["classification"] == classification
    assert result["reasons"] == [reason]


def test_each_policy_split_needs_enough_independent_pairs_and_uncertainty():
    payload = evaluation(4)
    assert evaluate_policy(payload)["reasons"] == ["uncertainty_exceeds_quality_limits"]
    payload = evaluation(120)
    for case in payload["cases"]:
        case["split"] = "policy_holdout"
    payload["cases"][0]["split"] = "policy_regression"
    assert evaluate_policy(payload)["reasons"] == ["minimum_pairs_not_met_in_each_split"]
    payload["cases"][0]["split"] = "policy_holdout"
    assert evaluate_policy(payload)["reasons"] == ["both_policy_splits_required"]


def test_observed_quality_loss_and_missing_results_are_not_replaced_by_preference():
    payload = evaluation(120)
    for case in payload["cases"]:
        case.update(baseline_quality=1.0, candidate_quality=0.9)
    assert evaluate_policy(payload)["classification"] == "quality_regression"
    payload["host_preference"] = "candidate"
    with pytest.raises(ContractError):
        evaluate_policy(payload)


@pytest.mark.parametrize("value", [-0.01, 1.01, True, "0.95", float("nan")])
def test_quality_scores_are_strict_bounded_values(value):
    payload = evaluation()
    payload["cases"][0]["candidate_quality"] = value
    with pytest.raises(ContractError):
        evaluate_policy(payload)
