"""LEARN SL-2 Part B: maintenance faults, restarts and the generated schedule.

Consiliency/jevdrill#45 (one failing item), #46 (the expiry notice) and #52 (the
generated command's import path), with the plan's controls for recurrence, the
cursor and notices across a reopened store. Stores and keys are synthetic: every
`Maintenance` here gets an explicit key function, and the scheduled command runs
on a store with no item, so no OS key store is reached.
"""

import json
import math
import platform
import plistlib
import shlex
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from jevdrill.maintenance import DAY, Maintenance
from jevdrill.storage import SQLiteStorage
from tests.analysis.test_observations import case
from tests.retention.test_retention import artifact, request

KEY = Fernet.generate_key()
START = 100 + 30 * DAY  # the items below are 30 days old: due for an archive prompt


def items(app, scope, context, count):
    """`count` raw items, sorted as maintenance visits them, with their content."""
    contents = {
        artifact(app, scope, context, f"item-{uuid4()}".encode()): None for _ in range(count)
    }
    directory = app.storage._artifact_directory(app.storage._task_scope(scope))
    return {identity: (directory / identity).read_bytes() for identity in sorted(contents)}


def archived(store):
    with store._connect() as c:
        return {
            row[0]
            for row in c.execute(
                "SELECT l.source_id FROM artifact_lifecycle l JOIN artifacts a ON a.scope=l.scope AND a.artifact_id=l.artifact_id WHERE a.kind='archive'"
            )
        }


def active(store):
    """Items still held as they were: rows present with retention 'active'.

    (A retired row is deleted at once, so "not retired" cannot be read from it.)
    """
    with store._connect() as c:
        return {
            row[0]
            for row in c.execute("SELECT artifact_id FROM artifacts WHERE retention='active'")
        }


def failures(store, scope):
    return [n for n in store.load_notices(scope) if n["kind"] == "failure"]


def damage(store, scope, identity):
    """Change an item's file so its digest no longer matches: it can never be archived."""
    path = store._artifact_directory(store._task_scope(scope)) / identity
    path.write_bytes(b"damaged-" + path.read_bytes())


def due(app, scope, clock):
    """Prompt every item, then move the clock to when archival is due."""
    maintenance = Maintenance(app.storage, lambda _: KEY, lambda: clock[0])
    maintenance.run(request(scope, max_items=100))
    clock[0] += 7 * DAY
    return maintenance


def test_a_failing_item_is_reported_and_retried_without_stopping_the_others(tmp_path):
    app, scope, context, _ = case(tmp_path)
    contents = items(app, scope, context, 3)
    failing, *healthy = contents
    clock = [START]
    maintenance = due(app, scope, clock)
    damage(app.storage, scope, failing)
    result = maintenance.run(request(scope))
    assert result["status"] == "completed" and result["pending"] >= 1
    assert archived(app.storage) == set(healthy)
    assert failing in active(app.storage)
    (notice,) = failures(app.storage, scope)
    assert failing in notice["summary"]
    assert contents[failing].decode() not in json.dumps(app.storage.load_notices(scope))
    # Tried again on the next run, still reported, still not retired.
    maintenance.run(request(scope))
    assert failures(app.storage, scope) == [notice]
    assert failing in active(app.storage) and failing not in archived(app.storage)
    # Once the item can be processed, it is archived and its notice goes.
    (app.storage._artifact_directory(app.storage._task_scope(scope)) / failing).write_bytes(
        contents[failing]
    )
    maintenance.run(request(scope))
    assert failing in archived(app.storage)
    assert failures(app.storage, scope) == []


@pytest.mark.parametrize("max_items", [1, 2, 3])
def test_a_healthy_item_is_reached_within_the_bound_however_many_fail(tmp_path, max_items):
    app, scope, context, _ = case(tmp_path)
    contents = items(app, scope, context, 5)
    *failing, healthy = contents  # the healthy item is visited last
    clock = [START]
    maintenance = due(app, scope, clock)
    for identity in failing:
        damage(app.storage, scope, identity)
    bound = math.ceil(len(contents) / max_items)
    for _ in range(bound):
        maintenance.run(request(scope, max_items=max_items))
    assert archived(app.storage) == {healthy}
    assert set(failing) <= active(app.storage)
    assert len(failures(app.storage, scope)) == len(failing)


@pytest.mark.parametrize("max_items", [2, 3])
def test_from_a_cursor_left_part_way_the_bound_is_one_run_more(tmp_path, max_items):
    app, scope, context, _ = case(tmp_path)
    contents = items(app, scope, context, 5)
    order = list(contents)
    clock = [START]
    maintenance = due(app, scope, clock)
    for identity in order:
        damage(app.storage, scope, identity)
    # The healthy item is the one a pass left part way would visit last: just behind
    # a cursor left by a run that stopped after it (a pause or a busy host does this).
    healthy = order[0]
    (app.storage._artifact_directory(app.storage._task_scope(scope)) / healthy).write_bytes(
        contents[healthy]
    )
    with app.storage._connect(True) as c:
        c.execute(
            "UPDATE maintenance_control SET cursor=? WHERE scope=?",
            (healthy, app.storage._task_scope(scope)),
        )
    bound = math.ceil(len(contents) / max_items) + 1
    for _ in range(bound):
        maintenance.run(request(scope, max_items=max_items))
    assert healthy in archived(app.storage)
    assert set(order[1:]) <= active(app.storage)


def test_the_cursor_survives_a_reopened_store(tmp_path):
    app, scope, context, _ = case(tmp_path)
    contents = items(app, scope, context, 3)
    for run in range(3):
        store = SQLiteStorage(
            app.storage.path
        )  # a fresh store object each run, reading what the last left
        Maintenance(store, lambda _: KEY, lambda run=run: START + run).run(
            request(scope, max_items=1)
        )
    with SQLiteStorage(app.storage.path)._connect() as c:
        prompted = dict(c.execute("SELECT artifact_id,prompted FROM artifact_lifecycle").fetchall())
    # Each run prompted exactly the next item: none missed, none prompted twice.
    assert [prompted[identity] for identity in contents] == [START, START + 1, START + 2]


def test_notices_survive_a_reopened_store(tmp_path):
    app, scope, context, _ = case(tmp_path)
    failing = next(iter(items(app, scope, context, 1)))
    clock = [START]
    maintenance = due(app, scope, clock)
    damage(app.storage, scope, failing)
    maintenance.run(request(scope))
    before = app.storage.load_notices(scope)
    assert any(failing in n["summary"] for n in before)
    assert SQLiteStorage(app.storage.path).load_notices(scope) == before


def test_the_expiry_notice_says_re_archived_content_keeps_its_first_expiry(tmp_path):
    app, scope, context, _ = case(tmp_path)
    items(app, scope, context, 1)
    clock = [START]
    maintenance = due(app, scope, clock)
    maintenance.run(request(scope))
    clock[0] += 360 * DAY  # inside the seven days before expiry
    maintenance.run(request(scope))
    summaries = [n["summary"] for n in app.storage.load_notices(scope)]
    assert any(
        "Content restored and archived again before this archive expires keeps this expiry." in s
        for s in summaries
    )


def schedule(tmp_path, scope):
    """Generate this platform's entry; return the written files and the store."""
    (tmp_path / "store").mkdir()
    store = SQLiteStorage(tmp_path / "store" / "jev.db")
    path = (tmp_path / "maintenance.json").resolve()
    path.write_text(json.dumps(request(scope, path=path)), encoding="utf-8")
    instructions = Maintenance(store, lambda _: KEY).run(request(scope, "schedule", path=path))
    files = instructions["scheduler_instructions"][2:]
    return files, store


def command_of(files):
    """The command the scheduler would run, read back from the written entry."""
    system = platform.system()
    if system == "Linux":
        (service,) = [f for f in files if f.endswith(".service")]
        line = next(
            line
            for line in Path(service).read_text(encoding="utf-8").splitlines()
            if line.startswith("ExecStart=")
        )
        return shlex.split(line.removeprefix("ExecStart=").replace("%%", "%").replace("$$", "$"))
    if system == "Darwin":
        with open(files[0], "rb") as stream:
            return plistlib.load(stream)["ProgramArguments"]
    namespace = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    root = ET.parse(files[0]).getroot()
    command = root.find(".//t:Exec/t:Command", namespace).text
    arguments = root.find(".//t:Exec/t:Arguments", namespace).text
    return subprocess.list2cmdline([command]) + " " + arguments


def scope_of():
    return {
        "project_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "producer": "fixture",
        "operation": "route",
    }


def test_the_generated_entry_recurs(tmp_path):
    files, _ = schedule(tmp_path, scope_of())
    system = platform.system()
    if system == "Linux":
        (timer,) = [f for f in files if f.endswith(".timer")]
        lines = Path(timer).read_text(encoding="utf-8").splitlines()
        assert "OnUnitActiveSec=1h" in lines and "WantedBy=timers.target" in lines
    elif system == "Darwin":
        with open(files[0], "rb") as stream:
            entry = plistlib.load(stream)
        assert entry["StartInterval"] == 3600
    else:
        namespace = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
        root = ET.parse(files[0]).getroot()
        assert root.find(".//t:Repetition/t:Interval", namespace).text == "PT1H"


def test_the_generated_command_imports_nothing_from_the_working_directory(tmp_path):
    files, _ = schedule(tmp_path, scope_of())
    command = command_of(files)
    job = tmp_path / "job"
    job.mkdir()
    mark = tmp_path / "imported-from-the-working-directory"
    # A module under a standard-library name that the command line imports.
    (job / "json.py").write_bytes(
        f"open({str(mark)!r}, 'w').close()\nraise ImportError('planted')\n".encode()
    )
    result = subprocess.run(
        command, cwd=job, capture_output=True, text=True, timeout=120, check=False
    )
    assert not mark.exists(), result.stdout + result.stderr
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "completed"
