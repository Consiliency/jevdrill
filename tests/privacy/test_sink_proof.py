"""The sink proof: text the credential check refuses reaches no judge and no local storage.

`redact` is the oracle. docs/sanitization-contract.md says what it refuses; this file shows
that the application honours a refusal at each of its six text boundaries. When `redact`
returns a text, nothing here claims the text is kept from the judge or from storage: the
contract says such text passes. Everything is deterministic and needs no network.
"""

import copy
import hashlib
import json
from uuid import uuid4

import pytest

from jevdrill.application import Application
from jevdrill.context import redact
from jevdrill.contracts import ContractError, canonical_digest
from tests.application.test_route_integration import inputs, policy

MESSAGE = "credential-like material"
MARKER = "SYNTHETIC_SENTINEL"
REFUSED_IN_MATRIX = 1104  # the count tests/context pins as I5
STRIDE = 11  # coprime to the six labels, so every boundary meets every label
FIELDS = (
    "route_task",
    "route_attachment",
    "work_objective_text",
    "authorized_context",
    "description",
    "attachment_refs",
)
RETURNED = "Ordinary context. " + MARKER
REFUSED = "password: " + MARKER


def refused(text):
    try:
        result = redact(text)
    except ContractError as error:
        assert type(error) is ContractError and error.args == (MESSAGE,), repr(text)
        return True
    assert result is text, repr(text)
    return False


class Judge:
    """Stands in for both judgment ports and records every argument it is given."""

    def __init__(self):
        self.calls = []

    def judge(self, task, candidates, deadline):
        self.calls.append([task, list(candidates)])
        return {
            "schema_version": "1",
            "function_revision": "JudgeCandidate-v2",
            "model_revision": "jev-latest",
            "candidate_digest": canonical_digest(list(candidates)),
            "judgments": {row["candidate_id"]: True for row in candidates},
            "measurements": [],
        }

    def observe_option(self, task, offered, question_digest, option_id, deadline):
        self.calls.append([task, offered])
        return {
            "schema_version": "1",
            "function_revision": "ObserveDiscoveryOption-v1",
            "model_revision": "jev-latest",
            "question_digest": question_digest,
            "judgments": {option_id: True},
            "measurements": [],
        }


def request_for(field, text, discovery_inputs):
    """One request with `text` at one boundary, raw retention on and a judgment due."""
    attachment = {
        "reference": "public.txt",
        "authorized": True,
        "modality": "document",
        "representation_source": "supplied",
        "text_representation": text,
    }
    retain = {"source": "request", "values": {"retain_raw_tasks": True}}
    if field.startswith("route_"):
        payload = inputs()
        payload["judgment_policy"] = policy()
        payload["inventory"]["candidates"][0]["quality_sufficient"] = None
        payload["settings_layers"] = [retain]
        if field == "route_task":
            payload["request"]["task_representation"] = text
        else:
            payload["request"]["attachment_refs"] = [attachment]
        return payload
    payload = copy.deepcopy(discovery_inputs)
    payload["settings_layers"].append(retain)
    payload["limits"]["max_rounds"] = 1
    if field == "description":
        payload["descriptions"][0]["description"] = text
    elif field == "attachment_refs":
        payload[field] = [attachment]
    else:
        payload[field] = text
    return payload


def send(app, field, payload):
    return (app.route if field.startswith("route_") else app.discover)(payload)


def stored_files(directory):
    return sorted(path for path in directory.rglob("*") if path.is_file())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def refused_texts(credential_matrix):
    texts = [text for text in credential_matrix.texts if refused(text)]
    assert len(texts) == REFUSED_IN_MATRIX
    return texts


@pytest.mark.parametrize("slot", range(100))
@pytest.mark.parametrize("field", FIELDS)
def test_a_refused_text_reaches_no_judge_and_no_storage(
    privacy_case_path, privacy_storage, discovery_inputs, refused_texts, field, slot
):
    text = refused_texts[FIELDS.index(field) + STRIDE * slot]
    assert MARKER in text
    empty = digest(privacy_storage.path)
    judge = Judge()
    app = Application(privacy_storage, judgments=judge, discovery_judgments=judge)
    with pytest.raises(ContractError) as caught:
        send(app, field, request_for(field, text, discovery_inputs))
    assert type(caught.value) is ContractError and caught.value.args == (MESSAGE,), repr(text)
    # Nothing travels with the refusal: the message is fixed and no other error is chained.
    assert caught.value.__cause__ is None and caught.value.__context__ is None, repr(text)
    assert judge.calls == [], repr(text)
    assert stored_files(privacy_case_path) == [privacy_storage.path], repr(text)
    assert digest(privacy_storage.path) == empty, repr(text)
    assert MARKER.encode() not in privacy_storage.path.read_bytes(), repr(text)


@pytest.mark.parametrize("field", FIELDS)
def test_a_returned_text_reaches_the_judge_and_storage(
    privacy_case_path, privacy_storage, discovery_inputs, field
):
    """The control: each boundary above is live, so a refusal is what kept the text out."""
    assert not refused(RETURNED)
    judge = Judge()
    app = Application(privacy_storage, judgments=judge, discovery_judgments=judge)
    send(app, field, request_for(field, RETURNED, discovery_inputs))
    assert MARKER in json.dumps(judge.calls)
    artifacts = stored_files(privacy_case_path / "artifacts")
    assert artifacts
    if field != "route_attachment":  # route retains the task text only
        assert any(MARKER.encode() in path.read_bytes() for path in artifacts)


@pytest.mark.parametrize("part", ["inventory", "catalog"])
def test_refused_inventory_or_catalog_text_is_a_stored_failure_with_the_fixed_code(
    privacy_case_path, privacy_storage, part
):
    assert refused(REFUSED)
    payload = inputs()
    payload["judgment_policy"] = policy()
    payload["inventory"]["candidates"][0]["quality_sufficient"] = None
    if part == "inventory":
        payload["inventory"]["candidates"][0]["source"] = REFUSED
    else:
        payload["catalog"] = {
            "schema_version": "1",
            "revision": payload["request"]["versions"]["catalog_revision"],
            "resources": [
                {
                    "resource_id": "resource",
                    "revision": "v1",
                    "content_hash": hashlib.sha256(REFUSED.encode()).hexdigest(),
                    "rights": "synthetic-owned",
                    "admission": "explicitly_enabled",
                    "source_occurrences": ["synthetic"],
                    "aliases": [],
                    "domain": "test",
                    "specialty": "test",
                    "task_family": "test",
                    "facets": [],
                    "benchmark_protocol": None,
                    "benchmark_split": None,
                    "benchmark_effort": None,
                    "instructions": REFUSED,
                    "conflicts": [],
                }
            ],
        }
    judge = Judge()
    app = Application(privacy_storage, judgments=judge)
    decision = app.route(payload)
    assert decision["status"] == "routing_failed"
    assert decision["error_code"] == MESSAGE
    assert judge.calls == []
    envelope = payload["request"]["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "route",
    }
    assert app.replay(scope, decision["details"]["routing_decision_id"]) == decision
    assert all(MARKER.encode() not in path.read_bytes() for path in stored_files(privacy_case_path))


@pytest.mark.parametrize("field", ["acceptance_requirement", "governing_reference"])
def test_route_refuses_text_outside_the_task_and_attachments_before_any_effect(
    privacy_case_path, privacy_storage, discovery_inputs, field
):
    """`route` checks its whole request itself.

    The task and attachment boundaries above are also refused when the context is collected,
    so only a field that step never sees shows that the request check is there.
    """
    assert refused(REFUSED)
    payload = request_for("route_task", "Ordinary task", discovery_inputs)
    if field == "acceptance_requirement":
        payload["request"]["optimization_objective"]["acceptance_requirements"].append(
            {
                "description": REFUSED,
                "evaluator_ref": "checks-v1",
                "requirement_id": "refused-requirement",
                "source": "user",
            }
        )
    else:
        payload["request"]["hard_constraints"]["governing_instruction_refs"].append(REFUSED)
    empty = digest(privacy_storage.path)
    judge = Judge()
    app = Application(privacy_storage, judgments=judge, discovery_judgments=judge)
    with pytest.raises(ContractError) as caught:
        app.route(payload)
    assert type(caught.value) is ContractError and caught.value.args == (MESSAGE,)
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert judge.calls == []
    assert stored_files(privacy_case_path) == [privacy_storage.path]
    assert digest(privacy_storage.path) == empty


@pytest.mark.parametrize("identifier", ["harness_id", "idempotency_key"])
def test_a_report_with_a_refused_identifier_is_refused_before_it_is_stored(
    privacy_case_path, privacy_storage, identifier
):
    assert refused(REFUSED)
    envelope = inputs()["request"]["envelope"] | {"operation": "report", identifier: REFUSED}
    event = {
        "schema_version": "1",
        "event_id": str(uuid4()),
        "task_id": str(uuid4()),
        "routing_decision_id": str(uuid4()),
        "execution_run_id": str(uuid4()),
        "source_id": "synthetic-host",
        "source_sequence": 1,
        "occurred_at": "2026-10-09T00:00:00Z",
        "supersedes_event_id": None,
        "payload": {
            "kind": "lifecycle",
            "event_type": "failed",
            "applied_plan_id": None,
            "reason": "synthetic",
        },
    }
    empty = digest(privacy_storage.path)
    with pytest.raises(ContractError) as caught:
        Application(privacy_storage).report({"envelope": envelope, "event": event})
    assert caught.value.args == (MESSAGE,)
    assert stored_files(privacy_case_path) == [privacy_storage.path]
    assert digest(privacy_storage.path) == empty


@pytest.mark.parametrize("entry_point", ["experiment", "execute_experiment", "manage_policy"])
def test_the_other_checked_entry_points_refuse_before_any_effect(
    privacy_case_path, privacy_storage, entry_point
):
    empty = digest(privacy_storage.path)
    with pytest.raises(ContractError) as caught:
        getattr(Application(privacy_storage), entry_point)({"note": REFUSED})
    assert caught.value.args == (MESSAGE,)
    assert stored_files(privacy_case_path) == [privacy_storage.path]
    assert digest(privacy_storage.path) == empty


def test_the_sample_reaches_every_matrix_label_at_every_boundary(credential_matrix, refused_texts):
    """The stride sample is 600 different refused entries, 100 at each boundary."""
    chosen = {
        (field, FIELDS.index(field) + STRIDE * slot) for field in FIELDS for slot in range(100)
    }
    assert len({index for _, index in chosen}) == 600 and max(i for _, i in chosen) < 1104
    labels = [label.strip() for label in credential_matrix.labels]
    for field in FIELDS:
        texts = [refused_texts[index] for name, index in chosen if name == field]
        assert all(any(label in text for text in texts) for label in labels), field
