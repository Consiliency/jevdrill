"""Check the exposed development evaluator without claiming calibrated model quality."""

import json

from verify_discovery_calibration import ROOT, offline


def main():
    report = offline()
    result = {
        "schema_version": 1,
        "origin": "software_only_evaluator_diagnostic",
        "status": report["status"],
        "protocol_digest": report["protocol_digest"],
        "controls": report["controls"],
        "empirical_calibration": "pending_Q12_Q13",
        "promotion_authorized": False,
        "produced_if_gates": [],
    }
    output = ROOT / "evidence/EXPERIMENT/calibration-offline.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return int(result["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
