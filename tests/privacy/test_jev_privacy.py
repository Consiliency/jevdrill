from time import monotonic

import pytest

from jevdrill.contracts import ContractError
from jevdrill.integrations.jev import JevAdapter


def test_no_policy_never_calls_provider(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("provider called without authority")

    monkeypatch.setattr("jevdrill.integrations.jev.JudgeCandidate", forbidden)
    with pytest.raises(ContractError, match="not authorized"):
        JevAdapter().judge("synthetic", ({"candidate_id": "candidate"},), monotonic() + 1)
