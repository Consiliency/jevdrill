import copy

import pytest

from jevdrill.contracts import ContractError
from jevdrill.discovery import apply_answers, complete, initial_state, next_question


def answer(question, judgments):
    return {
        "schema_version": "1",
        "function_revision": "ObserveDiscoveryOption-v1",
        "model_revision": "jev-latest",
        "question_digest": question["question_digest"],
        "judgments": judgments,
        "measurements": [],
    }


def traverse(inputs, category=True):
    state = initial_state(inputs, inputs["limits"])
    questions = []
    while (question := next_question(state)) is not None:
        questions.append(question)
        state = apply_answers(
            state,
            question,
            answer(
                question,
                {
                    row["option_id"]: (category(row) if callable(category) else category)
                    if row["level"] != "resource"
                    else True
                    for row in question["options"]
                    if row["feasible"] is True
                },
            ),
        )
    return state, questions


def test_successive_questions_false_categories_recover_and_permutations(discovery_inputs):
    discovery_inputs["work_objective_text"] = "Find useful guidance"
    state, questions = traverse(discovery_inputs, category=False)
    assert complete(state)
    assert len(state["supported"]) == 2
    assert {row["level"] for row in questions} == {"domain", "specialty", "task_family", "resource"}
    shuffled = copy.deepcopy(discovery_inputs)
    shuffled["catalog"]["resources"].reverse()
    shuffled["descriptions"].reverse()
    assert traverse(shuffled, False) == (state, questions)


def test_swapping_answers_changes_fifo_service(discovery_inputs):
    discovery_inputs["work_objective_text"] = "Find guidance"
    discovery_inputs["limits"]["active_branch_width"] = 1
    first, _ = traverse(discovery_inputs, lambda row: "alpha" in (row["label"] or ""))
    second, _ = traverse(discovery_inputs, lambda row: "beta" in (row["label"] or ""))
    assert first["visited"] != second["visited"]
    assert set(first["supported"]) == set(second["supported"])


def test_binding_unknown_duplicate_and_stale_answers(discovery_inputs):
    state = initial_state(discovery_inputs, discovery_inputs["limits"])
    question = next_question(state)
    with pytest.raises(ContractError, match="unoffered"):
        apply_answers(state, question, answer(question, {"spoof": True}))
    advanced = apply_answers(state, question, answer(question, {}))
    with pytest.raises(ContractError, match="stale"):
        apply_answers(advanced, question, answer(question, {}))
    assert advanced["unresolved"]
    assert not complete(advanced)


@pytest.mark.parametrize("field,value", [("max_rounds", 0), ("max_candidates", 0)])
def test_explicit_bounds(discovery_inputs, field, value):
    discovery_inputs["limits"][field] = value
    state, questions = traverse(discovery_inputs)
    assert not complete(state)
    assert not questions


def test_absent_description_is_unknown_not_negative(discovery_inputs):
    discovery_inputs["descriptions"] = []
    state, _ = traverse(discovery_inputs)
    assert not state["supported"] and not state["rejected"]
    assert not complete(state)


def test_exact_and_ambiguous_aliases_remain_suitability_questions(discovery_inputs):
    state = initial_state(discovery_inputs, discovery_inputs["limits"])
    assert next_question(state)["level"] == "resource"
    discovery_inputs["work_objective_text"] = "shared"
    question = next_question(initial_state(discovery_inputs, discovery_inputs["limits"]))
    assert question["level"] == "resource" and len(question["options"]) == 2


def test_bad_description_reference_rejected(discovery_inputs):
    discovery_inputs["descriptions"][0]["revision"] = "spoofed"
    with pytest.raises(ContractError):
        initial_state(discovery_inputs, discovery_inputs["limits"])


def test_false_domain_children_follow_already_queued_alternate_domains(discovery_inputs):
    discovery_inputs["work_objective_text"] = "Find suitable guidance"
    discovery_inputs["limits"]["active_branch_width"] = 1
    state = initial_state(discovery_inputs, discovery_inputs["limits"])
    first = next_question(state)
    assert first["level"] == "domain"
    state = apply_answers(state, first, answer(first, {first["options"][0]["option_id"]: False}))
    second = next_question(state)
    assert second["level"] == "domain"
    assert second["options"][0]["option_id"] != first["options"][0]["option_id"]
