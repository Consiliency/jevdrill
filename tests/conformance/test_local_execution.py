"""Item 8: an ordinary macOS launch stays local (HOST SL-7). Defined on macOS only.

The probe `test_ordinary_macos_launch_stays_local` writes the record; every assertion is here.
An exit status, an output line or a marker file is never accepted alone.
"""

import sys

if sys.platform == "darwin":

    def test_ordinary_macos_launch_stays_local(host_conformance):
        (record,) = [
            row["local_execution"]
            for row in host_conformance["records"]
            if "local_execution" in row
        ]
        assert record["refusal"] is None and record["unavailable_reason"] is None
        assert record["available"] is True and record["returncode"] == 0
        assert record["connected"] is True
        pid = record["pid_sent"]
        assert pid != record["parent_pid"] and record["pid_found"] == pid
        assert record["ancestry"][0] == pid and record["parent_pid"] in record["ancestry"][1:]
        assert record["child_digest"] is not None
        assert record["child_digest"] == record["parent_digest"]
        assert record["child_platform"] == record["parent_platform"] == "darwin"
