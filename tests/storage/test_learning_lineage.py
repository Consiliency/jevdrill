from uuid import uuid4

import pytest

from jevdrill.contracts import ContractError
from tests.analysis.test_observations import case


@pytest.mark.parametrize("forged", ["task_id", "routing_decision_id", "discovery_ref", "producer"])
def test_forged_learning_link_enters_storage_and_is_rejected(tmp_path, discovery_inputs, forged):
    app, scope, context, _ = case(tmp_path, discovery_inputs)
    if forged == "producer":
        scope = dict(scope, producer="forged")
    elif forged == "discovery_ref":
        context = dict(context, discovery_ref=dict(context["discovery_ref"], trace_digest="0" * 64))
    else:
        context = dict(context, **{forged: str(uuid4())})
    with pytest.raises(ContractError):
        app.storage.record_learning_context(scope, context)


def test_cross_producer_objective_tombstone_suppresses_analysis_but_keeps_task_reports(
    tmp_path, discovery_inputs
):
    app, scope, context, _ = case(tmp_path, discovery_inputs)
    assert len(app.storage.learning_observations(scope)) == 1
    app.storage.delete_discovery(
        dict(scope, operation="discover", producer="other"),
        context["discovery_ref"]["work_objective_id"],
    )
    assert app.storage.learning_observations(scope) == []
    assert app.storage.load_replay(scope, context["routing_decision_id"]) is not None
    with pytest.raises(ContractError):
        app.storage.record_learning_context(scope, context)
