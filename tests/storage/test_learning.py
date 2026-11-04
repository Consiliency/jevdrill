from jevdrill.analysis import aggregate_observations
from jevdrill.contracts import canonical_digest
from jevdrill.storage import SQLiteStorage
from tests.analysis.test_observations import case


def test_restart_migration_evidence_history_and_optout(tmp_path):
    app, scope, context, decision = case(tmp_path)
    observations = app.storage.learning_observations(scope)
    digest = canonical_digest(observations)
    evidence = {
        "schema_version": "1",
        "status": "updated",
        "source_digest": digest,
        "evidence_revision": "v1",
        "groups": aggregate_observations(observations),
        "assessments": [],
        "objective_history": [decision["details"]["optimization_objective"]],
    }
    app.storage.save_evidence(scope, evidence, 100, digest, False)
    reopened = SQLiteStorage(app.storage.path)
    assert reopened.latest_evidence(scope) == (100, evidence)
    assert reopened.objective_versions(scope) == evidence["objective_history"]
    reopened.restrict_learning(scope, context["task_id"], False)
    assert reopened.latest_evidence(scope) is None and reopened.learning_observations(scope) == []
    assert reopened.objective_versions(scope) == evidence["objective_history"]


def test_deletion_preserves_unrelated_project_evidence_and_objective_history(tmp_path):
    from uuid import uuid4

    app, scope, context, decision = case(tmp_path)
    app, other_scope, _other_context, other_decision = case(tmp_path, project=str(uuid4()))
    for selected_scope, selected_decision in ((scope, decision), (other_scope, other_decision)):
        observations = app.storage.learning_observations(selected_scope)
        digest = canonical_digest(observations)
        evidence = {
            "schema_version": "1",
            "status": "updated",
            "source_digest": digest,
            "evidence_revision": "v1",
            "groups": aggregate_observations(observations),
            "assessments": [],
            "objective_history": [selected_decision["details"]["optimization_objective"]],
        }
        app.storage.save_evidence(selected_scope, evidence, 100, digest, False)
    app.storage.delete_task(scope, context["task_id"])
    assert app.storage.latest_evidence(scope) is None
    assert app.storage.latest_evidence(other_scope) is not None
    assert app.storage.objective_versions(other_scope) == [
        other_decision["details"]["optimization_objective"]
    ]
