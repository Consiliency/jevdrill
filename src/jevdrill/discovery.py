"""Pure, bounded taxonomy traversal with digest-bound Boolean observations."""

import copy
import hashlib
import itertools
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from .catalog import catalog_digest, retrieve
from .contracts import ContractError, canonical_digest, parse_contract


def reference(row: Mapping[str, Any]) -> dict[str, str]:
    return {key: row[key] for key in ("resource_id", "revision", "content_hash")}


def initial_state(inputs: Mapping[str, Any], limits: Mapping[str, Any]) -> dict[str, Any]:
    resources = inputs["catalog"]["resources"]
    catalog_digest(resources)
    descriptions: dict[str, dict[str, Any]] = {}
    identities = {canonical_digest(reference(row)) for row in resources}
    for row in inputs["descriptions"]:
        identity = canonical_digest(reference(row))
        if identity not in identities or identity in descriptions:
            raise ContractError("invalid or duplicate description reference")
        descriptions[identity] = dict(row)
    nodes: dict[str, dict[str, Any]] = {}
    required = {canonical_digest(reference(row)) for row in inputs["required_guidance"]}
    roots = set()
    for row in sorted(resources, key=lambda item: (item["resource_id"], item["revision"])):
        parent = None
        path = []
        for level in ("domain", "specialty", "task_family"):
            path.append(row[level])
            identity = level + ":" + canonical_digest(path)
            if identity not in nodes:
                nodes[identity] = {
                    "option_id": identity,
                    "level": level,
                    "label": row[level],
                    "description": None,
                    "description_digest": None,
                    "reference": None,
                    "children": [],
                    "feasible": True,
                    "reason": None,
                }
            if parent is None:
                roots.add(identity)
            elif identity not in nodes[parent]["children"]:
                nodes[parent]["children"].append(identity)
            parent = identity
        ref = reference(row)
        key = canonical_digest(ref)
        identity = "resource:" + key
        description = descriptions.get(key)
        text = None if description is None else description["description"]
        reason = None
        feasible: bool | None = True
        if row["admission"] == "unadmitted" or key in required:
            feasible, reason = False, "unadmitted" if key not in required else "required guidance"
        elif text is None or not text.strip():
            feasible, reason = None, "description unavailable"
        elif len(text.encode()) > limits["max_description_utf8_bytes"]:
            feasible, reason, text = None, "description oversized", None
        nodes[identity] = {
            "option_id": identity,
            "level": "resource",
            "label": row["resource_id"],
            "description": text,
            "description_digest": None if description is None else canonical_digest(description),
            "reference": ref,
            "children": [],
            "feasible": feasible,
            "reason": reason,
        }
        assert parent is not None
        nodes[parent]["children"].append(identity)
    for node in nodes.values():
        node["children"].sort()
    shortcut = []
    objective = inputs["work_objective_text"].strip()
    for row in resources:
        if objective in [
            row["resource_id"],
            row["resource_id"] + "@" + row["revision"],
            *row["aliases"],
        ]:
            shortcut.append("resource:" + canonical_digest(reference(row)))
    preferred = []
    deferred = []
    sequence = 0
    if shortcut:
        preferred.append({"option_ids": sorted(shortcut), "enqueue_sequence": sequence})
        sequence += 1
    if roots:
        ordered = sorted(roots)
        width = 0 if shortcut else limits["active_branch_width"]
        if width:
            preferred.append({"option_ids": ordered[:width], "enqueue_sequence": sequence})
            sequence += 1
        if ordered[width:]:
            deferred.append({"option_ids": ordered[width:], "enqueue_sequence": sequence})
            sequence += 1
    excluded = sorted(key for key, row in nodes.items() if row["feasible"] is False)
    return dict(
        parse_contract(
            "DiscoveryState",
            {
                "schema_version": "1",
                "transition_policy": "discovery-fifo-v1",
                "nodes": [nodes[key] for key in sorted(nodes)],
                "preferred": preferred,
                "deferred": deferred,
                "next_sequence": sequence,
                "prefer_next": True,
                "visited": list(excluded),
                "supported": [],
                "rejected": [],
                "excluded": excluded,
                "unresolved": [],
                "limits": dict(limits),
                "budget": {
                    "rounds": 0,
                    "candidates": 0,
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reserved_spend": "0",
                    "currency": None,
                },
            },
        ).payload()
    )


def metadata_state(state: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(state))
    for node in result["nodes"]:
        node["description"] = node["label"] = None
    return result


def next_question(state: Mapping[str, Any]) -> dict[str, Any] | None:
    if state["budget"]["rounds"] >= state["limits"]["max_rounds"]:
        return None
    preferred, deferred = state["preferred"], state["deferred"]
    queue = "preferred" if preferred and (state["prefer_next"] or not deferred) else "deferred"
    cursors = state[queue]
    if not cursors:
        return None
    nodes = {row["option_id"]: row for row in state["nodes"]}
    available = [
        identity for identity in cursors[0]["option_ids"] if identity not in state["visited"]
    ]
    # A cursor whose descendants were reached by a shortcut still advances once.
    width = state["limits"]["active_branch_width"]
    if available and nodes[available[0]]["level"] == "resource":
        width = min(width, state["limits"]["max_candidates"] - state["budget"]["candidates"])
        if width <= 0:
            return None
    options = [copy.deepcopy(nodes[key]) for key in available[:width]]
    level = options[0]["level"] if options else nodes[cursors[0]["option_ids"][0]]["level"]
    identity = canonical_digest(
        [metadata_state(state), queue, [row["option_id"] for row in options]]
    )
    return {
        "schema_version": "1",
        "question_digest": identity,
        "level": level,
        "options": options,
        "queue": queue,
    }


def apply_answers(
    state: Mapping[str, Any],
    question: Mapping[str, Any],
    answers: Mapping[str, Any],
    budget_after: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    expected = next_question(state)
    record = parse_contract("DiscoveryJudgmentRecord", answers).payload()
    if expected is None or question["question_digest"] != expected["question_digest"]:
        raise ContractError("stale discovery question")
    if metadata_question(question) != metadata_question(expected):
        raise ContractError("changed discovery options")
    offered = {row["option_id"] for row in expected["options"] if row["feasible"] is True}
    if (
        record["question_digest"] != expected["question_digest"]
        or not set(record["judgments"]) <= offered
    ):
        raise ContractError("unoffered discovery answer")
    result = copy.deepcopy(dict(state))
    cursor = result[question["queue"]].pop(0)
    chosen = {row["option_id"] for row in expected["options"]}
    remaining = [
        key for key in cursor["option_ids"] if key not in chosen and key not in state["visited"]
    ]

    def enqueue(queue: str, identities: list[str]) -> None:
        children = sorted(set(identities) - set(result["visited"]))
        if children:
            result[queue].append(
                {"option_ids": children, "enqueue_sequence": result["next_sequence"]}
            )
            result["next_sequence"] += 1

    enqueue(question["queue"], remaining)
    for option in expected["options"]:
        identity = option["option_id"]
        result["visited"].append(identity)
        answer = record["judgments"].get(identity)
        if option["feasible"] is False:
            result["excluded"].append(identity)
        elif option["feasible"] is None or answer is None:
            result["unresolved"].append(identity)
        elif option["level"] == "resource":
            result["supported" if answer else "rejected"].append(identity)
        else:
            enqueue("preferred" if answer else "deferred", option["children"])
    result["prefer_next"] = question["queue"] != "preferred"
    if budget_after is not None:
        for key in ("rounds", "candidates", "calls", "input_tokens", "output_tokens"):
            if budget_after[key] < state["budget"][key]:
                raise ContractError("discovery allowance replenished")
        if (
            budget_after["calls"] > state["limits"]["max_calls"]
            or budget_after["input_tokens"] > state["limits"]["max_input_tokens"]
            or budget_after["output_tokens"]
            > budget_after["calls"] * state["limits"]["output_planning_reservation"]
        ):
            raise ContractError("discovery allowance exceeded")
        ceiling = state["limits"]["spending_ceiling"]
        if (
            ceiling is not None
            and budget_after["calls"]
            and (
                budget_after["reserved_spend"] is None
                or budget_after["currency"] != ceiling["currency"]
                or Decimal(budget_after["reserved_spend"]) > Decimal(ceiling["amount"])
            )
        ):
            raise ContractError("discovery spending allowance exceeded")
        result["budget"] = dict(budget_after)
    result["budget"]["rounds"] = state["budget"]["rounds"] + 1
    result["budget"]["candidates"] = state["budget"]["candidates"] + sum(
        row["level"] == "resource" for row in expected["options"]
    )
    return result


def metadata_question(question: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(question))
    for row in result["options"]:
        row["description"] = row["label"] = None
    return result


def complete(state: Mapping[str, Any]) -> bool:
    leaves = {row["option_id"] for row in state["nodes"] if row["level"] == "resource"}
    examined = set(state["supported"] + state["rejected"] + state["excluded"])
    return leaves <= examined


def select_resources(
    state: Mapping[str, Any],
    resources: list[dict[str, Any]],
    required: list[dict[str, Any]],
    context_limit: int,
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    required_text = [retrieve(resources, row) for row in required]
    required_ids = {row["resource_id"] for row in required}
    if len(required_ids) != len(required) or any(
        set(row["conflicts"]) & required_ids
        for row in resources
        if row["resource_id"] in required_ids
    ):
        raise ContractError("required guidance conflict")
    if sum(len(text.encode()) for text in required_text) > context_limit:
        raise ContractError("required guidance exceeds context")
    nodes = {row["option_id"]: row for row in state["nodes"]}
    rows = sorted(
        [nodes[key]["reference"] for key in state["supported"]],
        key=lambda row: (row["resource_id"], row["revision"]),
    )
    # Only judged-supported leaves reach full instruction retrieval.
    texts = {}
    feasible = []
    omitted = []
    for ref in rows:
        resource = next(row for row in resources if reference(row) == ref)
        text = retrieve(resources, ref | {"admission": resource["admission"]})
        ids = required_ids | {ref["resource_id"]}
        if sum(len(item.encode()) for item in required_text) + len(
            text.encode()
        ) > context_limit or any(
            set(row["conflicts"]) & ids for row in resources if row["resource_id"] in ids
        ):
            omitted.append("resource:" + canonical_digest(ref))
            continue
        texts[canonical_digest(ref)] = text
        feasible.append(ref)
    combinations = [combo for count in (2, 1) for combo in itertools.combinations(feasible, count)]
    for combo in combinations:
        ids = required_ids | {row["resource_id"] for row in combo}
        content = required_text + [texts[canonical_digest(row)] for row in combo]
        if (
            len(ids) != len(required_ids) + len(combo)
            or sum(len(text.encode()) for text in content) > context_limit
            or any(set(row["conflicts"]) & ids for row in resources if row["resource_id"] in ids)
        ):
            continue
        return list(combo), content, omitted
    return [], required_text, omitted


def replay_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    document = parse_contract("DiscoveryTrace", trace).payload()
    if not document["replay_available"]:
        raise ContractError("discovery replay unavailable")
    state = document["initial_state"]
    for transition in document["transitions"]:
        if transition["budget_before"] != state["budget"]:
            raise ContractError("discovery replay budget mismatch")
        state = apply_answers(
            state, transition["question"], transition["answers"], transition["budget_after"]
        )
        if state["budget"] != transition["budget_after"]:
            raise ContractError("discovery replay transition mismatch")
    optional_facts = [row for row in document["shortlist"] if not row["required"]]
    if {"resource:" + canonical_digest(row["reference"]) for row in optional_facts} != set(
        state["supported"]
    ):
        raise ContractError("discovery replay shortlist mismatch")
    result = document["result"]
    selected, exclusions, required_feasible = select_fact_references(
        document["shortlist"],
        document["guidance_context_limit"],
        result["details"]["required_guidance"],
    )
    if document["required_feasible"] and not required_feasible:
        raise ContractError("discovery replay required feasibility mismatch")
    if document["required_feasible"] and exclusions != document["finalization_exclusions"]:
        raise ContractError("discovery replay feasibility mismatch")
    for identity in document["finalization_exclusions"]:
        if identity not in state["supported"]:
            raise ContractError("discovery replay exclusion mismatch")
        state["supported"].remove(identity)
        state["excluded"].append(identity)
    if metadata_state(state) != metadata_state(document["final_state"]):
        raise ContractError("discovery replay final state mismatch")
    expected = (
        "needs_context"
        if document["missing_context"]
        else "constraint_conflict"
        if not document["required_feasible"]
        else "selected_guidance"
        if selected
        else "no_optional_guidance"
        if complete(state)
        else "discovery_failed"
    )
    if result["status"] != expected or result["details"]["guidance_refs"] != (
        selected if document["required_feasible"] else []
    ):
        raise ContractError("discovery replay result mismatch")
    if document["required_feasible"]:
        refs = [reference(row) for row in result["details"]["required_guidance"]] + selected
        texts = result["details"]["assembled_instructions"]
        if len(refs) != len(texts) or any(
            hashlib.sha256(text.encode()).hexdigest() != ref["content_hash"]
            for ref, text in zip(refs, texts, strict=True)
        ):
            raise ContractError("discovery replay instruction mismatch")
    unsigned = copy.deepcopy(document)
    unsigned["result"]["details"]["trace_digest"] = "0" * 64
    if canonical_digest(unsigned) != document["result"]["details"]["trace_digest"]:
        raise ContractError("discovery trace digest mismatch")
    return dict(document["result"])


def select_fact_references(
    facts: list[dict[str, Any]],
    context_limit: int,
    required: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[str], bool]:
    mandatory = [row for row in facts if row["required"]]
    ids = {row["reference"]["resource_id"] for row in mandatory}
    required_refs = [reference(row) for row in required]
    if (
        len(mandatory) != len(required_refs)
        or len(ids) != len(mandatory)
        or {canonical_digest(row["reference"]) for row in mandatory}
        != {canonical_digest(row) for row in required_refs}
        or any(not row["admitted"] or set(row["conflicts"]) & ids for row in mandatory)
    ):
        return [], [], False
    required_bytes = sum(row["instruction_utf8_bytes"] for row in mandatory)
    if required_bytes > context_limit:
        return [], [], False
    optional = sorted(
        [row for row in facts if not row["required"]],
        key=lambda row: (row["reference"]["resource_id"], row["reference"]["revision"]),
    )
    feasible = []
    omitted = []
    for row in optional:
        identity = row["reference"]["resource_id"]
        combined = ids | {identity}
        if (
            not row["admitted"]
            or identity in ids
            or required_bytes + row["instruction_utf8_bytes"] > context_limit
            or any(set(item["conflicts"]) & combined for item in mandatory + [row])
        ):
            omitted.append("resource:" + canonical_digest(row["reference"]))
        else:
            feasible.append(row)
    for count in (2, 1):
        for combo in itertools.combinations(feasible, count):
            combined = ids | {row["reference"]["resource_id"] for row in combo}
            if (
                len(combined) != len(ids) + count
                or required_bytes + sum(row["instruction_utf8_bytes"] for row in combo)
                > context_limit
                or any(set(row["conflicts"]) & combined for row in mandatory + list(combo))
            ):
                continue
            return [row["reference"] for row in combo], omitted, True
    return [], omitted, True
