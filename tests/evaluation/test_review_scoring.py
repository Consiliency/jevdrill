import json

import pytest

from jevdrill.evaluation import score_review_components as score_review

EXPECTED = {"issues": ["offset", "validation"], "example": [10, 20]}
LABELS = ["offset", "validation", "mutation"]


def test_correct_defects_survive_wrong_example_without_passing():
    score = score_review('{"issues":["validation","offset"],"example":[20,30]}', EXPECTED, LABELS)
    assert score["defects_found"] == ["offset", "validation"]
    assert score["defects_missed"] == score["false_alarms"] == []
    assert score["defect_recall"] == 1
    assert score["example_correct"] is False
    assert score["critical_pass"] is False


def test_missing_defects_and_false_alarms_stay_separate():
    score = score_review('{"issues":["validation","mutation"],"example":[10,20]}', EXPECTED, LABELS)
    assert score["defects_found"] == ["validation"]
    assert score["defects_missed"] == ["offset"]
    assert score["false_alarms"] == ["mutation"]
    assert score["defect_recall"] == 0.5
    assert score["example_correct"] is True
    assert not score["critical_pass"]


def test_clean_code_has_no_recall_denominator():
    score = score_review('{"issues":[],"example":4}', {"issues": [], "example": 4}, ["upper_bound"])
    assert score["defect_recall"] is None
    assert score["critical_pass"] is True
    score = score_review(
        '{"issues":["upper_bound"],"example":4}', {"issues": [], "example": 4}, ["upper_bound"]
    )
    assert score["false_alarms"] == ["upper_bound"]
    assert score["example_correct"] is True
    assert not score["critical_pass"]


@pytest.mark.parametrize(
    "output",
    [
        None,
        "not JSON",
        "null",
        "[]",
        "{}",
        '{"issues":[],"issues":["offset"],"example":[10,20]}',
    ],
)
def test_invalid_responses_leave_metrics_unknown(output):
    score = score_review(output, EXPECTED, LABELS)
    assert not score["format_valid"]
    assert score["defects_found"] is None
    assert score["example_correct"] is None
    assert not score["critical_pass"]


def test_example_type_is_not_coerced():
    score = score_review(
        json.dumps({"issues": [], "example": True}), {"issues": [], "example": 1}, []
    )
    assert not score["example_correct"]


def test_missing_example_preserves_defect_detection():
    score = score_review('{"issues":["offset","validation"]}', EXPECTED, LABELS)
    assert score["defects_found"] == ["offset", "validation"]
    assert score["defect_recall"] == 1
    assert score["example_correct"] is None
    assert not score["example_present"]
    assert not score["format_valid"]
    assert not score["critical_pass"]


@pytest.mark.parametrize("issues", ["offset", [True], ["offset", "offset"], ["unknown"]])
def test_invalid_issues_preserve_valid_example(issues):
    score = score_review(json.dumps({"issues": issues, "example": [10, 20]}), EXPECTED, LABELS)
    assert score["example_correct"] is True
    assert score["defects_found"] is None
    assert not score["format_valid"]
    assert not score["critical_pass"]


def test_extra_fields_do_not_grant_full_pass():
    score = score_review('{"issues":[],"example":4,"extra":1}', {"issues": [], "example": 4}, [])
    assert score["defects_found"] == [] and score["example_correct"] is True
    assert not score["format_valid"] and not score["critical_pass"]


def test_nonfinite_example_does_not_erase_valid_issues():
    score = score_review('{"issues":[],"example":NaN}', EXPECTED, LABELS)
    assert score["defects_missed"] == ["offset", "validation"]
    assert score["example_correct"] is None
    assert not score["critical_pass"]
