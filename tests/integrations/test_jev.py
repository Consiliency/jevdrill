import time

import pytest

from jevdrill.contracts import ContractError
from jevdrill.integrations.jev import JevAdapter


def test_expired_judgment_never_calls_provider():
    with pytest.raises(ContractError, match="deadline"):
        JevAdapter().judge("synthetic", ({"candidate_id": "candidate"},), time.monotonic() - 1)


def test_optional_frontier_shrinks_without_truncating_task():
    import json

    from baml_sdk import candidate_request_shape

    task = "Required binding task."
    candidate = {"candidate_id": "one"}
    limit = len(candidate_request_shape(task, json.dumps(candidate, sort_keys=True)).encode())
    policy = {
        "enabled": True,
        "cloud_allowed": True,
        "max_calls": 2,
        "max_candidates": 2,
        "max_input_tokens": limit,
        "max_output_tokens": 1,
        "spending_ceiling": None,
        "rates": None,
        "model_revision": "jev-latest",
        "function_revision": "JudgeCandidate-v2",
        "token_counter_revision": "utf8-bytes-upper-bound-v1",
    }
    assert JevAdapter(policy).bounded_candidates(task, (candidate, {"candidate_id": "two"})) == (
        candidate,
    )
    legacy = policy | {"function_revision": "JudgeCandidate-v1"}
    with pytest.raises(ContractError, match="legacy judgment policy"):
        JevAdapter(legacy).judge(task, (candidate,), time.monotonic() + 1)


@pytest.mark.parametrize(
    "direct, call, invalid, expected",
    [
        (3, None, False, {"kind": "known", "value": 3, "unit": "tokens"}),
        (None, 3, False, {"kind": "known", "value": 3, "unit": "tokens"}),
        (3, 3, False, {"kind": "known", "value": 3, "unit": "tokens"}),
        (3, 4, False, {"kind": "unknown", "reason": "incomplete"}),
        (None, 3, True, {"kind": "unknown", "reason": "incomplete"}),
        (None, None, False, {"kind": "unknown", "reason": "not_reported"}),
    ],
)
def test_usage_sources_reconcile_without_adding(direct, call, invalid, expected):
    from baml_sdk import JevUsageObservation
    from jevdrill.contracts import jev_usage_measurements

    observation = JevUsageObservation(
        input_tokens=direct,
        output_tokens=0,
        input_invalid=invalid,
        output_invalid=False,
        call_input_tokens=call,
        call_output_tokens=None,
        duration_ms=1,
        first_output_ms=None,
    )
    rows = jev_usage_measurements(observation)
    assert rows[1]["measurement_value"] == expected
    assert rows[2]["measurement_value"] == {"kind": "known", "value": 0, "unit": "tokens"}
