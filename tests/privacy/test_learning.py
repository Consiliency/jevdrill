from uuid import uuid4

import pytest

from jevdrill.contracts import ContractError
from tests.analysis.test_observations import case


def test_default_workspace_scope_and_explicit_redacted_user_wide_consent(tmp_path):
    app, scope, context, _ = case(tmp_path)
    other = dict(scope, project_id=str(uuid4()))
    assert app.storage.learning_observations(other) == []
    assert app.storage.learning_observations(other, True) == []
    context["share_user_wide"] = True
    app.storage.record_learning_context(scope, context)
    observations = app.storage.learning_observations(other, True)
    assert len(observations) == 1
    assert (
        not {"task_id", "discovery_ref", "project_id", "raw_task", "raw_output"}
        & observations[0].keys()
    )
    same_project_other_workspace = dict(scope, workspace_id=str(uuid4()))
    assert app.storage.learning_observations(same_project_other_workspace) == []
    app.storage.restrict_learning(scope, context["task_id"], False)
    assert app.storage.learning_observations(other, True) == []
    with pytest.raises(ContractError, match="opted out"):
        app.storage.record_learning_context(scope, context)
