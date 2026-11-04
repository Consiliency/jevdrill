from decimal import Decimal

import pytest

from jevdrill.contracts import ContractError
from jevdrill.costing import ConservativeTokenCounter, estimate_attempt_cost


def test_estimates_are_bounded_adjusted_and_never_observed():
    value = estimate_attempt_cost(10, 2, "0.1", "0.2", "USD", "rates-v1", "0.5")
    assert value.raw == Decimal("1.4")
    assert value.adjusted == Decimal("0.7")
    assert value.observed is None
    assert estimate_attempt_cost(10, 2, None, "0.2", "USD", "r").raw is None


@pytest.mark.parametrize("rate", ["NaN", "Infinity", "-1", "invalid"])
def test_nonfinite_negative_rates_rejected(rate):
    with pytest.raises(ContractError):
        estimate_attempt_cost(10, 2, rate, "0", "USD", "r")


def test_counter_binds_method_and_counts_utf8_not_characters():
    counter = ConservativeTokenCounter()
    assert counter.count("é", "utf8-bytes-upper-bound-v1") == 2
    with pytest.raises(ContractError):
        counter.count("text", "unknown")
