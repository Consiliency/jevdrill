"""LEARN SL-1: user-wide values are specific to the requester (Consiliency/jevdrill#86).

One producer shares a discovery-linked task with two runs; two requesters in other
projects analyze with user-wide evidence included. Everyone consents. Values are read
from the public analysis path (`Application.analyze`). All inputs are synthetic and the
store makes no request.
"""

import base64
import copy
import hashlib
import hmac
import json
import shutil
import time
from uuid import uuid4

import pytest

from jevdrill.application import Application
from jevdrill.contracts import canonical_digest
from jevdrill.storage import SQLiteStorage
from tests.analysis.test_observations import case, report

NEVER = 10**9  # an interval no test reaches, so only the batch count can make analysis due


def request(scope, minimum_batch=1):
    return {
        "schema_version": "1",
        "scope": scope,
        "action": "analyze",
        "context": None,
        "objectives": [],
        "minimum_batch": minimum_batch,
        "interval_seconds": NEVER,
        "include_user_wide": True,
        "settings_layers": [{"source": "request", "values": {"local_analysis_enabled": True}}],
    }


def completed(app, scope, context, decision):
    """One finished run of the producer's task, with the same reports as every other run."""
    run = str(uuid4())
    plan = decision["execution_plan"]["execution_plan_id"]
    for sequence, event_type in enumerate(("plan_applied", "completed"), 1):
        payload = {
            "kind": "lifecycle",
            "event_type": event_type,
            "applied_plan_id": plan if event_type == "plan_applied" else None,
            "reason": None,
        }
        report(app, scope, context, run, payload, sequence)
    return run


def values(response):
    """The two user-wide values a requester receives: per group, and per observation."""
    return (
        sorted(g["conditions"]["discovery_identity"] for g in response["groups"]),
        sorted(ref for g in response["groups"] for ref in g["observation_refs"]),
    )


@pytest.fixture
def shared(tmp_path, discovery_inputs):
    app, producer, context, decision = case(tmp_path, discovery_inputs)
    context["share_user_wide"] = True
    app.storage.record_learning_context(producer, context)
    runs = [completed(app, producer, context, decision) for _ in range(2)]
    requesters = [dict(producer, project_id=str(uuid4())) for _ in range(2)]
    return app, producer, context, decision, runs, requesters


def main_formula(app, producer, context, run):
    """What `main` gave before this change, from the producer's own inputs."""
    pair = SQLiteStorage._task_scope(producer)
    events = sorted(
        (
            json.loads(payload)
            for (payload,) in _rows(app, "SELECT payload FROM events_v1 WHERE task_scope=?", pair)
        ),
        key=lambda e: (e["source_sequence"], e["source_id"], e["event_id"]),
    )
    current = [e for e in events if e["execution_run_id"] == run]
    linkage = context["discovery_ref"]
    return canonical_digest(linkage), canonical_digest(
        [pair, context["task_id"], context["routing_decision_id"], linkage, run, current]
    )


def _rows(app, sql, *parameters):
    with app.storage._connect() as connection:
        return connection.execute(sql, parameters).fetchall()


def test_user_wide_source_names_no_producer_identity(shared):
    app, producer, context, decision, runs, requesters = shared
    response = app.analyze(request(requesters[0]))
    assert response["status"] == "updated"
    sources = [s for g in response["groups"] for s in g["sources"]]
    assert sources and all(s["origin"] == "user_wide_redacted" for s in sources)
    assert all(
        s[k] is None
        for s in sources
        for k in ("task_id", "routing_decision_id", "execution_run_id", "discovery_ref")
    )
    linkage = context["discovery_ref"]
    identities = [
        context["task_id"],
        context["routing_decision_id"],
        decision["execution_plan"]["execution_plan_id"],
        producer["project_id"],
        *runs,
        *linkage.values(),
    ]
    text = json.dumps(response)
    assert [value for value in identities if value in text] == []


def test_values_differ_from_main_and_from_another_store_with_the_same_inputs(shared, tmp_path):
    app, producer, context, _decision, runs, requesters = shared
    identities, references = values(app.analyze(request(requesters[0])))
    assert len(identities) == 1 and len(references) == 2
    formula = [main_formula(app, producer, context, run) for run in runs]
    assert not {f[0] for f in formula} & set(identities)
    assert not {f[1] for f in formula} & set(references)
    # Both values come from the key this store holds, and from nothing a requester knows.
    ((key,),) = _rows(app, "SELECT key FROM shared_record_key")
    pair = SQLiteStorage._task_scope(requesters[0])

    def keyed(value):
        return hmac.new(key, canonical_digest([pair, value]).encode(), hashlib.sha256).hexdigest()

    assert identities == sorted({keyed(f[0]) for f in formula})
    assert references == sorted(keyed(f[1]) for f in formula)
    # A second store holding the same producer records, for the same requester. Only the
    # store's key differs, so equal values here would mean the inputs alone rebuild them.
    (tmp_path / "other").mkdir()  # the same file name as the first store, elsewhere
    other = Application(SQLiteStorage(tmp_path / "other" / app.storage.path.name))
    other.storage.import_recovery(producer, app.storage.export_recovery(producer), time.time())
    assert other.storage.learning_observations(producer) == app.storage.learning_observations(
        producer
    )
    other_identities, other_references = values(other.analyze(request(requesters[0])))
    assert len(other_references) == len(references) == 2
    assert not set(other_identities) & set(identities)
    assert not set(other_references) & set(references)


def test_two_requesters_receive_different_values(shared):
    app, _producer, _context, _decision, _runs, requesters = shared
    first, second = (values(app.analyze(request(r))) for r in requesters)
    assert len(first[0]) == len(second[0]) == 1
    assert len(first[1]) == len(second[1]) == 2
    assert not set(first[0]) & set(second[0])
    assert not set(first[1]) & set(second[1])


def test_a_requester_keeps_its_values_across_analyses_and_reopening(shared):
    app, _producer, _context, _decision, _runs, requesters = shared
    first = app.storage.learning_observations(requesters[0], True)
    assert app.storage.learning_observations(requesters[0], True) == first
    reopened = SQLiteStorage(app.storage.path)
    assert reopened.learning_observations(requesters[0], True) == first
    analyzed = values(app.analyze(request(requesters[0])))
    assert analyzed == values(Application(reopened).analyze(request(requesters[0])))
    assert analyzed[1] == sorted(o["observation_ref"] for o in first)


def test_one_discovery_shares_a_group_and_the_batch_counts_new_references(
    shared, monkeypatch, tmp_path
):
    app, _producer, _context, _decision, _runs, requesters = shared
    monkeypatch.setattr("jevdrill.application.time", lambda: 100)
    first = app.analyze(request(requesters[0]))
    assert first["status"] == "updated"
    (group,) = first["groups"]  # the producer's two runs of one discovery
    assert len(group["observation_refs"]) == 2
    # An unchanged set is no new reference.
    assert app.analyze(request(requesters[0]))["status"] == "not_due"
    # A new observation from a task the saved evidence does not depend on. (A report on
    # the producer's task would invalidate that evidence, and every reference would count.)
    _, second, context, decision = case(tmp_path, project=str(uuid4()))
    context["share_user_wide"] = True
    app.storage.record_learning_context(second, context)
    completed(app, second, context, decision)
    assert app.storage.latest_evidence(requesters[0]) is not None
    # One new observation is exactly one new reference: not two, and not zero.
    assert app.analyze(request(requesters[0], minimum_batch=2))["status"] == "not_due"
    after = app.analyze(request(requesters[0], minimum_batch=1))
    assert after["status"] == "updated"
    assert sorted(len(g["observation_refs"]) for g in after["groups"]) == [1, 2]


def test_local_observations_are_unchanged(shared):
    app, producer, context, _decision, runs, _requesters = shared
    local = app.storage.learning_observations(producer, True)
    assert len(local) == 2 and all(o["source"]["origin"] == "local" for o in local)
    expected = {main_formula(app, producer, context, run) for run in runs}
    assert {(o["conditions"]["discovery_identity"], o["observation_ref"]) for o in local} == (
        expected
    )


def test_an_exported_bundle_does_not_contain_the_key(shared, tmp_path):
    app, producer, _context, _decision, _runs, requesters = shared
    ((key,),) = _rows(app, "SELECT key FROM shared_record_key")
    assert len(key) == 32
    # The key is random: not derived from the store's path or name, which others can know.
    path = tmp_path / "again" / app.storage.path.name
    keys = []
    for _ in range(2):  # the same path twice, the store removed between
        path.parent.mkdir()
        with SQLiteStorage(path)._connect() as connection:
            keys += connection.execute("SELECT key FROM shared_record_key").fetchone()
        shutil.rmtree(path.parent)
    assert len({key, *keys}) == 3
    for scope in (producer, *requesters):
        body = json.dumps(app.storage.export_recovery(scope))
        forms = (key.hex(), key.hex().upper(), base64.b64encode(key).decode())
        forms += (base64.urlsafe_b64encode(key).decode(),)
        assert [form for form in forms if form in body] == []
        assert "shared_record_key" not in body


# LEARN SL-7: the revisions digest in user-wide groups (Consiliency/jevdrill#86).


def discovery_for(discovery_inputs, project, token_limit):
    """A discovery of one producer; equal inputs give equal revisions."""
    inputs = copy.deepcopy(discovery_inputs)
    inputs["envelope"].update(project_id=project, idempotency_key=str(uuid4()))
    inputs["envelope"]["request_id"] = str(uuid4())
    inputs["work_objective_id"] = str(uuid4())
    inputs["hard_constraints"]["context_token_limit"] = token_limit
    return inputs


@pytest.fixture
def revisions(tmp_path, discovery_inputs):
    """One producer: A1 and A2 with equal inputs (A1 run twice), A3 with another limit."""
    project = str(uuid4())
    made = {}
    for name, limit, runs in (("A1", 32768, 2), ("A2", 32768, 1), ("A3", 16384, 1)):
        app, producer, context, decision = case(
            tmp_path, discovery_for(discovery_inputs, project, limit)
        )
        context["share_user_wide"] = True
        app.storage.record_learning_context(producer, context)
        for _ in range(runs):
            completed(app, producer, context, decision)
        made[name] = context
    requesters = [dict(producer, project_id=str(uuid4())) for _ in range(2)]
    return app, producer, made, requesters


def revisions_of(app, context):
    ((result,),) = _rows(
        app,
        "SELECT result FROM discoveries WHERE discovery_id=?",
        context["discovery_ref"]["discovery_id"],
    )
    return canonical_digest(json.loads(result)["details"]["revisions"])


def keyed_value(app, scope, value):
    ((key,),) = _rows(app, "SELECT key FROM shared_record_key")
    pair = SQLiteStorage._task_scope(scope)
    return hmac.new(key, canonical_digest([pair, value]).encode(), hashlib.sha256).hexdigest()


def received(app, scope):
    """The `discovery_revisions` values `scope` receives in user-wide observations."""
    return [
        o["conditions"]["discovery_revisions"]
        for o in app.storage.learning_observations(scope, True)
        if o["source"]["origin"] == "user_wide_redacted"
    ]


def test_revisions_value_needs_the_store_key(revisions):
    app, _producer, made, requesters = revisions
    got = set(received(app, requesters[0]))
    unkeyed = {revisions_of(app, context) for context in made.values()}
    assert len(got) == 2 and not got & unkeyed
    assert got == {keyed_value(app, requesters[0], value) for value in unkeyed}


def test_revisions_value_differs_between_requesters_and_stores(revisions, tmp_path):
    app, producer, _made, requesters = revisions
    first, second = (set(received(app, r)) for r in requesters)
    assert len(first) == len(second) == 2 and not first & second
    (tmp_path / "elsewhere").mkdir()
    other = SQLiteStorage(tmp_path / "elsewhere" / app.storage.path.name)
    other.import_recovery(producer, app.storage.export_recovery(producer), time.time())
    elsewhere = {
        o["conditions"]["discovery_revisions"]
        for o in other.learning_observations(requesters[0], True)
        if o["source"]["origin"] == "user_wide_redacted"
    }
    assert len(elsewhere) == 2 and not elsewhere & first


def test_revisions_value_is_stable_for_a_requester(revisions):
    app, _producer, _made, requesters = revisions
    first = received(app, requesters[0])
    assert len(first) == 4  # A1's two runs, A2 and A3
    assert received(app, requesters[0]) == first
    assert values(app.analyze(request(requesters[0]))) == values(
        Application(SQLiteStorage(app.storage.path)).analyze(request(requesters[0]))
    )
    reopened = SQLiteStorage(app.storage.path)
    assert [
        o["conditions"]["discovery_revisions"]
        for o in reopened.learning_observations(requesters[0], True)
        if o["source"]["origin"] == "user_wide_redacted"
    ] == first


def test_equal_revisions_get_equal_values_and_unequal_ones_differ(revisions):
    app, _producer, made, requesters = revisions
    assert revisions_of(app, made["A1"]) == revisions_of(app, made["A2"])
    assert revisions_of(app, made["A1"]) != revisions_of(app, made["A3"])
    per_discovery = {}
    for o in app.storage.learning_observations(requesters[0], True):
        if o["source"]["origin"] == "user_wide_redacted":
            per_discovery.setdefault(o["conditions"]["discovery_identity"], set()).add(
                o["conditions"]["discovery_revisions"]
            )
    assert len(per_discovery) == 3 and all(len(v) == 1 for v in per_discovery.values())
    a1, a2, a3 = (keyed_value(app, requesters[0], revisions_of(app, made[n])) for n in made)
    assert {next(iter(v)) for v in per_discovery.values()} == {a1, a3}
    assert a1 == a2 != a3


def test_one_discovery_still_shares_a_group_with_all_three_values_keyed(revisions):
    app, _producer, _made, requesters = revisions
    groups = app.analyze(request(requesters[0]))["groups"]
    assert sorted(len(g["observation_refs"]) for g in groups) == [1, 1, 2]


def test_local_revisions_values_are_unchanged(revisions):
    app, producer, made, _requesters = revisions
    local = {
        o["conditions"]["discovery_revisions"]
        for o in app.storage.learning_observations(producer, True)
        if o["source"]["origin"] == "local"
    }
    assert local == {revisions_of(app, context) for context in made.values()}
