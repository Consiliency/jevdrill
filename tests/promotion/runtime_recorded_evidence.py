"""Explicit operational probe; run only through the configured Linux verifier."""

import pytest

from jevdrill.contracts import ContractError
from tests.promotion.test_recorded_evidence import (
    development as development,  # noqa: PLC0414
)
from tests.promotion.test_recorded_evidence import (
    evaluate,
)
from tests.promotion.test_recorded_evidence import (
    provider as provider,  # noqa: PLC0414
)
from tests.promotion.test_recorded_evidence import (
    recorded as recorded,  # noqa: PLC0414
)
from tests.promotion.test_recorded_evidence import (
    setup as setup,  # noqa: PLC0414
)


@pytest.mark.parametrize("recorded", ["runtime_good", "runtime_bad"], indirect=True)
def test_recorded_comparison_uses_restricted_grader(recorded, request):
    candidate_passed = request.node.callspec.params["recorded"] == "runtime_good"
    service, request, study, _, calls, _, _, execution, _, provider = recorded
    before = len(provider["requests"])
    assert before == 8 and calls == []
    result = evaluate(recorded)
    assert result["status"] == "recorded", result
    record = result["record"]
    assert record["policy_status"] == "evaluated"
    assert record["exposed_at"] is not None
    assert record["preparation"]["evaluator_identity"] == study.evaluator_identity
    assert record["evaluation"]["identities_blinded"] is True
    assert record["evaluation"]["evidence_origin"] == "synthetic"
    assert len(calls) == 4 and len(provider["requests"]) == before
    for case in record["evaluation"]["cases"]:
        assert case["baseline_quality"] == 1.0
        assert case["baseline_critical"] == {"answers_match": True}
        assert case["candidate_quality"] == float(candidate_passed)
        assert case["candidate_critical"] == {"answers_match": candidate_passed}
        assert case["baseline_measurements"] and case["candidate_measurements"]
    if candidate_passed:
        assert "controlled_evidence_required" in record["assessment"]["reasons"]
    else:
        assert record["assessment"]["classification"] == "critical_regression"
    # A repeated request must not regrade exposed data or dispatch another call.
    assert (
        service.handle(request | {"action": "evaluate", "definition": None})["status"] == "denied"
    )
    assert len(calls) == 4 and len(provider["requests"]) == before
    assert service.handle(request | {"action": "promote", "definition": None})["status"] == "denied"
    execution.storage.delete_task(request["scope"], study.definition["cases"][0]["task_id"])
    assert (
        execution.storage.policy_study(request["scope"], study.definition["policy_revision"])
        is None
    )
    with pytest.raises(ContractError, match="policy_frozen_protocol_missing_or_changed"):
        service.evidence.prepare(study.definition)
    assert len(calls) == 4 and len(provider["requests"]) == before
