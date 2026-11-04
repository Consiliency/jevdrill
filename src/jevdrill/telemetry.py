"""Retain only numeric JEV call measurements; discard provider payloads."""

from baml_sdk import JevUsageObservation
from baml_sdk.ai.events import LLMCall

from .contracts import jev_usage_measurements


def _counter(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def retain_jev_call(event: object) -> dict[str, object] | None:
    """Use the call's usage once; separate Usage events are not additive."""
    if isinstance(event, JevUsageObservation):
        result: dict[str, object] = {"source": "provider_reported"}
        result["invocation_id"] = event.invocation_id
        for row in jev_usage_measurements(event):
            result[row["metric_id"].removeprefix("routing_")] = row["measurement_value"].get(
                "value"
            )
        result.update(
            first_output_ms=_counter(event.first_output_ms),
            cached_input_tokens=None,
            reasoning_tokens=None,
        )
        return result
    if not isinstance(event, LLMCall) or event.provider != "typesafeai":
        return None
    usage = event.usage
    return {
        "source": "provider_reported",
        "duration_ms": _counter(event.timing.duration_ms),
        "first_output_ms": _counter(event.timing.ttft_ms),
        "input_tokens": _counter(usage.input_tokens) if usage else None,
        "output_tokens": _counter(usage.output_tokens) if usage else None,
        "cached_input_tokens": _counter(usage.cached_input_tokens) if usage else None,
        "reasoning_tokens": _counter(usage.reasoning_tokens) if usage else None,
    }
