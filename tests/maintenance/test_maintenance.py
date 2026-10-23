import json
import subprocess
import sys
from uuid import uuid4

from cryptography.fernet import Fernet

from jevdrill.integrations.archive import maintenance_lock
from jevdrill.maintenance import DAY, Maintenance
from tests.analysis.test_observations import case
from tests.retention.test_retention import artifact, request


def test_process_owned_nonoverlap_and_exit_release(tmp_path):
    app, scope, _, _ = case(tmp_path)
    path = app.storage.path.with_suffix(".maintenance.lock")
    script = "from pathlib import Path;from jevdrill.integrations.archive import maintenance_lock;import sys;\nwith maintenance_lock(Path(sys.argv[1])) as acquired:\n print(acquired,flush=True);sys.stdin.read()"
    worker = subprocess.Popen(
        [sys.executable, "-c", script, str(path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert worker.stdout.readline().strip() == "True"
        assert Maintenance(app.storage).run(request(scope))["status"] == "busy"
    finally:
        worker.communicate("stop", timeout=5)
    with maintenance_lock(path) as acquired:
        assert acquired


def test_bounded_resumable_cursor_pause_cancel_and_interactive_contention(tmp_path):
    app, scope, context, _ = case(tmp_path)
    key = Fernet.generate_key()
    now = [100 + 30 * DAY]
    for number in range(3):
        artifact(app, scope, context, str(number).encode())
    maintenance = Maintenance(app.storage, lambda _: key, lambda: now[0])
    assert maintenance.run(request(scope, max_items=1))["pending"] == 1
    assert maintenance.run(request(scope, "pause"))["status"] == "paused"
    assert maintenance.run(request(scope))["status"] == "paused"
    maintenance.run(request(scope, "resume"))
    assert maintenance.run(dict(request(scope), interactive_busy=True))["status"] == "busy"
    assert maintenance.run(request(scope, "cancel"))["status"] == "canceled"
    assert maintenance.run(request(scope))["status"] == "canceled"
    maintenance.run(request(scope, "resume"))
    maintenance.run(request(scope, max_items=1))
    maintenance.run(request(scope, max_items=1))
    with app.storage._connect() as c:
        assert (
            c.execute(
                "SELECT count(*) FROM artifact_lifecycle WHERE prompted IS NOT NULL"
            ).fetchone()[0]
            == 3
        )
    now[0] += 7 * DAY
    for _ in range(5):
        maintenance.run(request(scope, max_items=1))
    with app.storage._connect() as c:
        assert c.execute("SELECT count(*) FROM artifacts WHERE kind='archive'").fetchone()[0] == 3


def test_pause_and_interactive_start_are_rechecked_between_production_items(tmp_path):
    app, scope, context, _ = case(tmp_path)
    key = Fernet.generate_key()
    now = [100 + 30 * DAY]
    for number in range(3):
        artifact(app, scope, context, str(number).encode())
    path = tmp_path / "request with spaces.json"
    payload = request(scope, path=path)
    path.write_text(json.dumps(payload))
    maintenance = Maintenance(app.storage, lambda _: key, lambda: now[0])
    maintenance.run(payload)
    now[0] += 7 * DAY

    def provider(_):
        path.write_text(json.dumps(dict(payload, interactive_busy=True)))
        return key

    maintenance.key_provider = provider
    result = maintenance.run(payload)
    assert result["status"] == "busy" and result["processed"] == 1
    path.write_text(json.dumps(payload))

    def pause(_):
        maintenance.run(request(scope, "pause"))
        return key

    maintenance.key_provider = pause
    assert maintenance.run(payload)["status"] == "paused"


def test_os_key_store_failure_is_bounded_without_plaintext_fallback(monkeypatch):
    from jevdrill.integrations.archive import archive_key

    calls = []

    def unavailable(argv, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(argv, 2, b"", b"synthetic locked store")

    monkeypatch.setattr(subprocess, "run", unavailable)
    assert archive_key("synthetic-" + str(uuid4())) is None
    assert calls[0]["timeout"] == 2 and calls[0]["capture_output"]
