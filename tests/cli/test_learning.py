import json
import platform
import plistlib
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from jevdrill.maintenance import Maintenance
from tests.analysis.test_observations import case
from tests.application.test_learning import analysis_request
from tests.maintenance.test_recovery import recovery
from tests.retention.test_retention import request


def invoke(app, command, payload):
    result = subprocess.run(
        [sys.executable, "-m", "jevdrill.cli", "--storage", str(app.storage.path), command],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result.returncode, json.loads(result.stdout)


def test_installed_cli_analyze_notices_recovery_and_reject_unknown_claims(tmp_path):
    app, scope, _context, _ = case(tmp_path)
    code, response = invoke(app, "analyze", analysis_request(scope))
    assert code == 0 and response["status"] == "updated"
    assert (
        invoke(app, "analyze", dict(analysis_request(scope), evidence_scope="whole_skill"))[0] == 2
    )
    assert (
        invoke(app, "analyze", dict(analysis_request(scope), settings_layers=[]))[1]["status"]
        == "denied"
    )
    key = Fernet.generate_key()
    code, exported = invoke(app, "recovery", recovery(scope, key))
    assert code == 0 and exported["status"] == "exported"
    assert (
        invoke(app, "recovery", recovery(scope, key, "import", exported["encrypted_bundle"]))[1][
            "status"
        ]
        == "imported"
    )
    assert invoke(app, "notices", {"schema_version": "1", "scope": scope})[1]["notices"] == []


def test_native_scheduler_argv_enters_installed_maintenance_and_host_contention(tmp_path):
    app, scope, _, _ = case(tmp_path)
    path = tmp_path / "scheduled request $percent%.json"
    payload = request(scope, path=path)
    path.write_text(json.dumps(payload))
    maintenance = Maintenance(app.storage)
    proposed = maintenance.run(dict(payload, action="schedule"))
    files = [Path(p) for p in proposed["scheduler_instructions"][2:]]
    native = platform.system()
    if native == "Linux":
        text = files[0].read_text()
        line = next(l for l in text.splitlines() if l.startswith("ExecStart="))[10:]
        argv = shlex.split(line.replace("%%", "%").replace("$$", "$"))
    elif native == "Darwin":
        argv = plistlib.loads(files[0].read_bytes())["ProgramArguments"]
    else:
        xml = ET.parse(files[0])
        ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
        arguments = xml.findtext(".//t:Exec/t:Arguments", namespaces=ns)
        import ctypes

        count = ctypes.c_int()
        shell = ctypes.windll.shell32
        shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
        parsed = shell.CommandLineToArgvW("synthetic.exe " + arguments, ctypes.byref(count))
        try:
            argv = [
                xml.findtext(".//t:Exec/t:Command", namespaces=ns),
                *[parsed[i] for i in range(1, count.value)],
            ]
        finally:
            ctypes.windll.kernel32.LocalFree(parsed)
    assert argv[-1] == "maintenance" and argv[argv.index("--request-file") + 1] == str(path)
    result = subprocess.run(argv, capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == 0 and json.loads(result.stdout)["status"] == "completed"
    payload["interactive_busy"] = True
    path.write_text(json.dumps(payload))
    result = subprocess.run(argv, capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == 0 and json.loads(result.stdout)["status"] == "busy"
    assert not list(tmp_path.glob("*.installed"))


def test_schedule_requires_explicit_scoped_request_path(tmp_path):
    from jevdrill.contracts import ContractError

    app, scope, _, _ = case(tmp_path)
    with pytest.raises(ContractError):
        Maintenance(app.storage).run(request(scope, "schedule"))
