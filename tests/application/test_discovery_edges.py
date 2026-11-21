"""Discovery at two edges: a retry that overtakes a running call, and several revisions."""

import copy

import pytest

from jevdrill.application import Application
from jevdrill.storage import SQLiteStorage
from tests.application.test_discovery_application import scope


def test_a_same_key_retry_during_a_running_discovery_gives_both_calls_the_committed_result(
    tmp_path, discovery_inputs, discovery_observer
):
    discovery_inputs["work_objective_text"] = "objective with no alias, so several rounds run"
    first = Application(
        SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer
    )
    retry = Application(
        SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer
    )
    begin = first.storage.begin_discovery_round
    rounds = []
    retried = []

    def retry_before_the_second_round(*arguments):
        rounds.append(arguments)
        if len(rounds) == 2:
            retried.append(retry.discover(copy.deepcopy(discovery_inputs)))
        return begin(*arguments)

    first.storage.begin_discovery_round = retry_before_the_second_round
    result = first.discover(copy.deepcopy(discovery_inputs))
    assert len(retried) == 1
    assert retried[0]["status"] == "discovery_failed" and retried[0]["error_code"] == "interrupted"
    assert result == retried[0]
    assert (
        first.inspect_discovery(scope(discovery_inputs), result["details"]["discovery_id"])
        == result
    )


@pytest.mark.parametrize("case", ["a newer revision conflicts", "an unadmitted revision conflicts"])
def test_replay_agrees_with_selection_when_another_revision_declares_a_conflict(
    tmp_path, discovery_inputs, discovery_observer, case
):
    alpha = discovery_inputs["catalog"]["resources"][0]
    other = copy.deepcopy(alpha) | {"revision": "v0", "conflicts": ["beta"], "aliases": []}
    if case == "a newer revision conflicts":
        other["revision"] = "v2"
        discovery_inputs["work_objective_text"] = "shared"
    else:
        other["admission"] = "unadmitted"
        beta = discovery_inputs["catalog"]["resources"][1]
        discovery_inputs["required_guidance"] = [
            {
                "resource_id": beta["resource_id"],
                "revision": beta["revision"],
                "content_hash": beta["content_hash"],
                "role": "required",
                "admission": beta["admission"],
                "authority": "synthetic",
                "task_id": discovery_inputs["work_objective_id"],
                "token_count": None,
            }
        ]
    discovery_inputs["catalog"]["resources"].append(other)
    discovery_observer.answer = lambda task, option: True
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=discovery_observer)
    result = app.discover(discovery_inputs)
    selected = [(row["resource_id"], row["revision"]) for row in result["details"]["guidance_refs"]]
    print(case, result["status"], selected, len(discovery_observer.calls))
    replayed = app.inspect_discovery(
        scope(discovery_inputs), result["details"]["discovery_id"], True
    )
    assert replayed == result
