"""Bounded one-attempt Decimal costs, separate from observed charges."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .contracts import ContractError


@dataclass(frozen=True)
class AttemptCost:
    raw: Decimal | None
    adjusted: Decimal | None
    observed: Decimal | None
    currency: str
    rate_revision: str


def estimate_attempt_cost(
    input_tokens: int | None,
    output_tokens: int | None,
    input_rate: str | None,
    output_rate: str | None,
    currency: str,
    rate_revision: str,
    adjustment: str | None = None,
) -> AttemptCost:
    for count in (input_tokens, output_tokens):
        if count is not None and (type(count) is not int or count < 0):
            raise ContractError("invalid token bound")
    if (
        len(currency) != 3
        or not currency.isascii()
        or not currency.isupper()
        or not currency.isalpha()
    ):
        raise ContractError("invalid currency")
    try:
        rates = [
            None if value is None else Decimal(value)
            for value in (input_rate, output_rate, adjustment)
        ]
    except (InvalidOperation, ValueError) as error:
        raise ContractError("invalid rate") from error
    if any(value is not None and (not value.is_finite() or value < 0) for value in rates):
        raise ContractError("invalid rate")
    if input_tokens is None or output_tokens is None or rates[0] is None or rates[1] is None:
        return AttemptCost(None, None, None, currency, rate_revision)
    raw = Decimal(input_tokens) * rates[0] + Decimal(output_tokens) * rates[1]
    adjusted = None if rates[2] is None else raw * rates[2]
    return AttemptCost(raw, adjusted, None, currency, rate_revision)


class ConservativeTokenCounter:
    """A UTF-8 byte upper bound, only for explicitly declared byte-token models."""

    def __init__(self, revisions: dict[str, str] | None = None) -> None:
        self.revisions = revisions or {"utf8-bytes-upper-bound-v1": "utf8-bytes-upper-bound-v1"}

    def count(self, text: str, model_revision: str) -> int:
        if self.revisions.get(model_revision) != "utf8-bytes-upper-bound-v1":
            raise ContractError("token counter unavailable")
        return len(text.encode("utf-8"))
