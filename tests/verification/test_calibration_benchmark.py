import json
from pathlib import Path

from jevdrill.evaluation import evaluate_host_artifact


def test_family_specific_calibration_is_pending_and_references_are_independent():
    protocol = json.loads(
        (
            Path(__file__).parents[2] / "research/evaluation/discovery-calibration/protocol.json"
        ).read_text()
    )
    assert set(protocol["calibration"]) == {"implementation", "review", "documentation"}
    # Exercise pending settings without requiring the repository to stay pending forever.
    pending = {
        family: dict.fromkeys(settings) for family, settings in protocol["calibration"].items()
    }
    assert all(all(value is None for value in settings.values()) for settings in pending.values())
    for case in protocol["cases"]:
        assert all(
            evaluate_host_artifact(
                case["task_family"], case["expected"], case["reference_artifact"]
            ).values()
        )
        assert not all(
            evaluate_host_artifact(
                case["task_family"], case["expected"], case["unacceptable_artifact"]
            ).values()
        )
    assert (
        protocol["exposed"]
        and not protocol["holdouts_opened"]
        and not protocol["promotion_eligible"]
    )
