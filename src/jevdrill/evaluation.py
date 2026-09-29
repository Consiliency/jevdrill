"""Pure measurement aggregation and split checks; no routing or promotion effects."""

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from decimal import Decimal

from .contracts import ContractError, ValidatedDocument


def cost_per_accepted(
    costs: Sequence[Decimal | None], accepted: Sequence[bool | None]
) -> Decimal | None:
    if len(costs) != len(accepted):
        raise ValueError("cost/outcome lengths differ")
    if any(value is None for value in costs) or any(value is None for value in accepted):
        return None
    count = sum(value is True for value in accepted)
    if count == 0:
        return None
    total = sum((value for value in costs if value is not None), Decimal(0))
    return total / count


def elapsed_union_ms(intervals: Sequence[tuple[int, int]]) -> int:
    """Elapsed occupied wall time, counting overlapping candidate intervals once."""
    result = 0
    end: int | None = None
    for start, stop in sorted(intervals):
        if stop < start:
            raise ValueError("negative interval")
        result += max(0, stop - (start if end is None else max(start, end)))
        end = stop if end is None else max(end, stop)
    return result


def token_total(
    input_tokens: int | None,
    output_tokens: int | None,
    cached_input_tokens: int | None = None,
    reasoning_output_tokens: int | None = None,
) -> int | None:
    """Aggregate counters whose declared semantics make cache/reasoning subsets."""
    for count in (input_tokens, output_tokens, cached_input_tokens, reasoning_output_tokens):
        if count is not None and count < 0:
            raise ValueError("negative token count")
    if input_tokens is None or output_tokens is None:
        return None
    if cached_input_tokens is not None and cached_input_tokens > input_tokens:
        raise ValueError("cache subset exceeds input")
    if reasoning_output_tokens is not None and reasoning_output_tokens > output_tokens:
        raise ValueError("reasoning subset exceeds output")
    return input_tokens + output_tokens


def require_comparable(left: ValidatedDocument, right: ValidatedDocument) -> None:
    if left.contract_name != "Measurement" or right.contract_name != "Measurement":
        raise ContractError("measurement contracts required")
    a, b = left.payload(), right.payload()
    keys = ("metric_id", "metric_version", "method", "scope", "source", "counting_semantics")
    if any(a[key] != b[key] for key in keys):
        raise ContractError("incompatible metric definitions or provenance")
    av, bv = a["measurement_value"], b["measurement_value"]
    if av["kind"] != "known" or bv["kind"] != "known":
        raise ContractError("missing measurement")
    if av["unit"] != bv["unit"]:
        raise ContractError("incompatible units")


def validate_splits(
    assignments: Mapping[str, Sequence[str]],
    groups: Mapping[str, str],
    exposed_tasks: AbstractSet[str],
) -> None:
    allowed = {
        "development",
        "validation",
        "policy_holdout",
        "policy_regression",
        "release_holdout",
    }
    if set(assignments) - allowed:
        raise ValueError("unknown split")
    seen: dict[str, str] = {}
    group_split: dict[str, str] = {}
    for split, tasks in assignments.items():
        for task in tasks:
            if task not in groups or task in seen:
                raise ValueError("missing grouping or duplicated task")
            group = groups[task]
            if group in group_split and group_split[group] != split:
                raise ValueError("related-task leakage")
            if split in {"release_holdout", "policy_holdout"} and task in exposed_tasks:
                raise ValueError("holdout already exposed")
            seen[task] = split
            group_split[group] = split
