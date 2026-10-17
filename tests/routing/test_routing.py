import copy
import itertools
import json
from decimal import Decimal
from pathlib import Path

from jevdrill.costing import AttemptCost
from jevdrill.routing import candidate_fingerprint, select_plan

ROOT = Path(__file__).resolve().parents[2]


def request():
    rows = json.loads((ROOT / "tests/contracts/fixtures/boundary.json").read_text())
    value = copy.deepcopy(next(row["payload"] for row in rows if row["id"] == "RouteRequest-0"))
    value["optimization_objective"]["metric_id"] = "raw_token_cost"
    return value


def candidate():
    rows = json.loads((ROOT / "tests/contracts/fixtures/route-inputs.json").read_text())
    return copy.deepcopy(rows[0]["payload"]["candidates"][0]) | {
        "candidate_id": "candidate",
        "available": True,
        "effective_capabilities": ["text"],
    }


def test_unknown_cost_cannot_satisfy_hard_cap():
    payload = request()
    payload["hard_constraints"]["spending_ceiling"] = {"amount": "1", "currency": "USD"}
    result = select_plan(payload, [candidate()], AttemptCost(None, None, None, "USD", "rates"))
    assert result["status"] == "no_compatible_plan"
    assert result["details"]["exclusions"] == [
        {"candidate_id": "candidate", "reasons": ["cost_cap"]}
    ]


def test_stable_model_id_breaks_ties():
    payload = request()
    second = candidate() | {"candidate_id": "second", "model_id": "model-z"}
    result = select_plan(
        payload, [second, candidate()], AttemptCost(Decimal(0), None, None, "USD", "rates")
    )
    assert result["execution_plan"]["model_id"] == "model-a"


def test_costs_quality_time_and_boolean_default_are_permutation_invariant():
    payload = request()
    rows = [
        candidate()
        | {"candidate_id": "expensive", "cost": AttemptCost(Decimal(3), None, None, "USD", "r")},
        candidate()
        | {
            "candidate_id": "cheap",
            "model_id": "z",
            "cost": AttemptCost(Decimal(1), None, None, "USD", "r"),
        },
        candidate()
        | {
            "candidate_id": "bad",
            "quality_sufficient": False,
            "cost": AttemptCost(Decimal(0), None, None, "USD", "r"),
        },
        candidate()
        | {
            "candidate_id": "slow",
            "completion_time_limit_ms": 1,
            "cost": AttemptCost(Decimal(0), None, None, "USD", "r"),
        },
    ]
    for permutation in itertools.permutations(rows):
        result = select_plan(payload, permutation)
        assert result["execution_plan"]["model_id"] == "z"
        assert result["details"]["cost_estimate"]["raw_token_cost"]["amount"] == "1"
    rows[0]["cost"] = rows[1]["cost"]
    rows[1]["default"] = True
    assert select_plan(payload, rows)["execution_plan"]["model_id"] == "z"


def test_foreign_currency_cannot_prove_a_hard_cap():
    payload = request()
    payload["hard_constraints"]["spending_ceiling"] = {"amount": "1", "currency": "EUR"}
    assert (
        select_plan(payload, [candidate()], AttemptCost(Decimal(0), None, None, "USD", "r"))[
            "status"
        ]
        == "no_compatible_plan"
    )


def test_policy_ordering_cannot_override_eligibility_and_pins_model_revision():
    payload = request()
    ordinary = candidate() | {"cost": AttemptCost(Decimal(1), None, None, "USD", "r")}
    preferred = candidate() | {
        "candidate_id": "preferred",
        "model_id": "preferred",
        "cost": AttemptCost(Decimal(2), None, None, "USD", "r"),
    }
    policy = {
        "policy_revision": "learned",
        "evidence_digest": "proof",
        "candidate_order": [
            {
                "candidate_id": row["candidate_id"],
                "candidate_fingerprint": candidate_fingerprint(row),
            }
            for row in (preferred, ordinary)
        ],
    }
    selected = select_plan(payload, [ordinary, preferred], policy=policy)
    assert selected["execution_plan"]["model_id"] == "preferred"
    assert selected["details"]["versions"]["policy_revision"] == "learned"
    assert "proof" in selected["details"]["evidence_refs"]
    for change in (
        {"quality_sufficient": False},
        {"available": False},
        {"completion_time_limit_ms": 0},
    ):
        selected = select_plan(payload, [ordinary, preferred | change], policy=policy)
        assert selected["execution_plan"]["model_id"] == "model-a"
    preferred["resolved_model_revision"] = "changed"
    assert (
        select_plan(payload, [ordinary, preferred], policy=policy)["error_code"]
        == "policy_candidate_changed"
    )
