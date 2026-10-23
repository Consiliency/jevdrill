import pytest

from jevdrill.contracts import ContractError
from jevdrill.guidance import select_guidance


def resource(name, role="test", count=4):
    return {
        "resource_id": name,
        "revision": "v1",
        "role": role,
        "token_count": count,
        "admission": "explicitly_enabled",
    }


def test_no_guidance_and_required_never_truncated():
    assert select_guidance([], [], 1) == {"required": [], "optional": []}
    with pytest.raises(ContractError, match="exceeds"):
        select_guidance([resource("required")], [], 3)
    with pytest.raises(ContractError, match="unknown"):
        select_guidance([resource("required", count=None)], [], 100)


def test_reinjection_roles_and_admission_are_checked():
    for required, optional in (
        ([resource("r")], [resource("r")]),
        ([], [resource("a"), resource("b")]),
        ([], [resource("a") | {"admission": "review_priority"}]),
    ):
        with pytest.raises(ContractError):
            select_guidance(required, optional, 100)
