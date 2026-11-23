"""LEARN SL-2 Part B: maintenance faults, restarts and the generated schedule.

Consiliency/jevdrill#45 (one failing item), #46 (the expiry notice) and #52 (the
generated command's import path), with the plan's controls for recurrence, the
cursor and notices across a reopened store. Stores and keys are synthetic: every
`Maintenance` here gets an explicit key function, and the scheduled command runs
on a store with no item, so no OS key store is reached.
"""

import json
import math
import os
import platform
import plistlib
import shlex
import shutil
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from cryptography.fernet import Fernet

from jevdrill.contracts import canonical_digest
from jevdrill.integrations.archive import maintenance_lock
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
    # The environment a scheduler may hand it: the working directory on PYTHONPATH (an
    # empty entry, then the directory itself) and a user base holding a planted .pth.
    marked = tmp_path / "imported-from-the-user-site"
    userbase = tmp_path / "userbase"
    environment = dict(os.environ, PYTHONPATH=os.pathsep + str(job), PYTHONUSERBASE=str(userbase))
    user_site, site_packages = subprocess.run(
        [
            sys.executable,
            "-c",
            "import site; print(site.ENABLE_USER_SITE); print(site.getusersitepackages())",
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\n")[:2]
    Path(site_packages).mkdir(parents=True)
    (Path(site_packages) / "planted.pth").write_bytes(
        f"import os; open({str(marked)!r}, 'w').close()\n".encode()
    )
    result = subprocess.run(
        command,
        cwd=job,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert not mark.exists(), result.stdout + result.stderr
    # A venv without system site packages never reads a user site, whatever the flag, so
    # this half can only fail where the interpreter has a user site to read.
    if user_site == "True":
        assert not marked.exists(), result.stdout + result.stderr
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["status"] == "completed"


# LEARN SL-8: restored content kept (Consiliency/jevdrill#125) and expiry notices for
# archives in any page (#128). Every clock below is injected; no run reads the wall clock.


class YieldsAfter(Maintenance):
    """A run the host turns busy once `items` of its items are done: it yields part way.

    `run` asks once at its start, then once before each item; the host answers busy
    from the check before item `items + 1` on.
    """

    def __init__(self, storage, clock, items):
        super().__init__(storage, lambda _: KEY, clock)
        self.items, self.checks = items, 0

    def _interactive(self, request):
        self.checks += 1
        return self.checks > self.items + 1 or super()._interactive(request)


def archive_of(store, scope, source):
    """The identity and archival time of the unretired archive of `source`, or None."""
    with store._connect() as c:
        return c.execute(
            "SELECT a.artifact_id,l.archived FROM artifacts a JOIN artifact_lifecycle l ON a.scope=l.scope AND a.artifact_id=l.artifact_id WHERE a.scope=? AND l.source_id=? AND a.kind='archive' AND a.retention!='retired'",
            (store._task_scope(scope), source),
        ).fetchone()


def kept(store, scope, source, original, tmp_path):
    """Whether the content can be had back with its original bytes.

    It can if it is held as it is, or if `restore` brings it back from an archive.
    The restore runs on a copy of the store, so the store under test is unchanged.
    """
    pair = store._task_scope(scope)
    if source in active(store):
        return (store._artifact_directory(pair) / source).read_bytes() == original
    found = archive_of(store, scope, source)
    if found is None:
        return False
    copy = tmp_path / f"copy-{uuid4()}"
    copy.mkdir()
    with closing(sqlite3.connect(store.path)) as live, closing(sqlite3.connect(copy / "c.db")) as c:
        live.backup(c)
    duplicate = SQLiteStorage(copy / "c.db")
    shutil.copytree(store._artifact_directory(pair), duplicate._artifact_directory(pair))
    Maintenance(duplicate, lambda _: KEY, lambda: 0).restore(scope, found[0])
    return (duplicate._artifact_directory(pair) / source).read_bytes() == original


def restored_copy(tmp_path, order, days):
    """#125's sequence up to the copy's prompt.

    One item is archived; its archive is restored `days` later, and the copy is
    prompted 30 days after that, so the copy's archival is due seven days on. The
    copy's identity sorts `order` ("before" or "after") its archive's; the archive's
    bytes are random, so stores are made until one sorts so.
    """
    for attempt in range(64):
        (tmp_path / f"store-{attempt}").mkdir()
        app, scope, context, _ = case(tmp_path / f"store-{attempt}")
        ((source, original),) = items(app, scope, context, 1).items()
        clock = [START]
        due(app, scope, clock).run(request(scope))
        first, archived_at = archive_of(app.storage, scope, source)
        if (source < first) == (order == "before"):
            break
    else:
        raise AssertionError("no store sorted as asked")
    maintenance = Maintenance(app.storage, lambda _: KEY, lambda: clock[0])
    clock[0] = archived_at + days * DAY
    maintenance.restore(scope, first)
    clock[0] += 30 * DAY
    maintenance.run(request(scope))
    return app, scope, clock, source, original, first, archived_at


def runs(app, scope, clock, source, original, tmp_path, schedule):
    """Make the runs `schedule` gives as (time, maintenance or None, max_items).

    After each, the content must still be kept. Returns the time of the run that
    archived the copy again.
    """
    archived_again = None
    for when, maintenance, max_items in schedule:
        clock[0] = when
        maintenance = maintenance or Maintenance(app.storage, lambda _: KEY, lambda: clock[0])
        maintenance.run(request(scope, max_items=max_items))
        assert kept(app.storage, scope, source, original, tmp_path), when
        if archived_again is None and source not in active(app.storage):
            archived_again = when
    assert archived_again is not None
    return archived_again


def kept_for_a_year_from(app, scope, clock, source, original, tmp_path, archival):
    """Case 4: restorable before a year from `archival`; not after a run at that year."""
    maintenance = Maintenance(app.storage, lambda _: KEY, lambda: clock[0])
    clock[0] = archival + 365 * DAY - 1
    maintenance.run(request(scope, max_items=100))
    assert kept(app.storage, scope, source, original, tmp_path)
    clock[0] = archival + 365 * DAY
    maintenance.run(request(scope, max_items=100))
    assert not kept(app.storage, scope, source, original, tmp_path)


@pytest.mark.parametrize("order", ["before", "after"])
def test_125_restored_copy_archived_after_its_archive_expired_is_kept(tmp_path, order):
    """Case 1: #125's sequence, with the copy sorting before the archive and after it."""
    app, scope, clock, source, original, _, archived_at = restored_copy(tmp_path, order, 330)
    # No run from day 361 to 367 after the first archival; one run at day 368.
    archival = runs(
        app, scope, clock, source, original, tmp_path, [(archived_at + 368 * DAY, None, 10)]
    )
    kept_for_a_year_from(app, scope, clock, source, original, tmp_path, archival)


@pytest.mark.parametrize("order", ["before", "after"])
@pytest.mark.parametrize("split", ["max_items", "yield"])
def test_125_copy_and_archive_reached_in_different_runs(tmp_path, order, split):
    """Case 2: the two items reached in different runs, split by `max_items` or by a
    run that yields part way."""
    app, scope, clock, source, original, _, archived_at = restored_copy(tmp_path, order, 330)
    day = archived_at + 368 * DAY
    getter = lambda: clock[0]
    first_run = (
        (day, None, 1) if split == "max_items" else (day, YieldsAfter(app.storage, getter, 1), 10)
    )
    clock[0] = day
    archival = runs(
        app,
        scope,
        clock,
        source,
        original,
        tmp_path,
        [first_run, (day + 3600, None, first_run[2])],
    )
    # The first run reached only the first of the two in identity order.
    assert archival == (day if order == "before" else day + 3600)
    kept_for_a_year_from(app, scope, clock, source, original, tmp_path, archival)


@pytest.mark.parametrize("order", ["before", "after"])
def test_125_a_run_exactly_at_the_archive_deadline(tmp_path, order):
    """Case 3: the copy's archival is due before the archive's deadline, and the next run
    is exactly at it; by `maintenance.py`'s rule the archive has then expired."""
    app, scope, clock, source, original, _, archived_at = restored_copy(tmp_path, order, 320)
    deadline = archived_at + 365 * DAY
    archival = runs(app, scope, clock, source, original, tmp_path, [(deadline, None, 10)])
    kept_for_a_year_from(app, scope, clock, source, original, tmp_path, archival)


def test_125_copy_archived_again_before_the_archive_expires_keeps_its_expiry(tmp_path):
    """Case 5: archived again before the first archive expires, the content keeps that
    archive and its expiry (#46). SL-2's notice-text test passes unedited beside it."""
    app, scope, clock, source, original, first, archived_at = restored_copy(tmp_path, "before", 300)
    runs(app, scope, clock, source, original, tmp_path, [(archived_at + 340 * DAY, None, 10)])
    assert archive_of(app.storage, scope, source) == (first, archived_at)
    kept_for_a_year_from(app, scope, clock, source, original, tmp_path, archived_at)


def archived_store(tmp_path, count):
    """A store of `count` archives made at one time; returns them sorted, and the expiry."""
    app, scope, context, _ = case(tmp_path)
    contents = items(app, scope, context, count)
    clock = [START]
    due(app, scope, clock).run(request(scope, max_items=100))
    found = [archive_of(app.storage, scope, source) for source in contents]  # one archival time
    return app, scope, context, sorted(identity for identity, _ in found), found[0][1] + 365 * DAY


def expiry_notice(store, pair, task, identity):
    """The archive's expiry notice, found by the identity the code gives it, or None."""
    notice_id = str(
        uuid5(NAMESPACE_URL, canonical_digest([pair, task, "archive_expiry", identity]))
    )
    with store._connect() as c:
        row = c.execute(
            "SELECT payload FROM lifecycle_notices WHERE scope=? AND notice_id=?", (pair, notice_id)
        ).fetchone()
    return None if row is None else json.loads(row[0])


def expiry_notices(store):
    """Every expiry notice in the store, in any scope."""
    with store._connect() as c:
        payloads = [
            json.loads(row[0]) for row in c.execute("SELECT payload FROM lifecycle_notices")
        ]
    return [n for n in payloads if n["summary"].startswith("Archived content expires")]


def announced(app, scope, context, archives, expiry):
    """Whether every archive given has its expiry notice, dated at its expiry."""
    pair = app.storage._task_scope(scope)
    deadline = datetime.fromtimestamp(expiry, UTC).isoformat().replace("+00:00", "Z")
    notices = [expiry_notice(app.storage, pair, context["task_id"], a) for a in archives]
    return all(n is not None and n["deadline"] == deadline for n in notices)


def cursor(store, scope):
    with store._connect() as c:
        return c.execute(
            "SELECT cursor FROM maintenance_control WHERE scope=?", (store._task_scope(scope),)
        ).fetchone()[0]


@pytest.mark.parametrize("layout", ["one_page_and_one", "inside_one_page"])
def test_128_archive_outside_the_page_is_announced_by_the_first_run_in_its_last_week(
    tmp_path, layout
):
    """Case 1: the first run in the last seven days writes the notice of an archive its page
    does not reach. The store is one page and one item, or fits inside one page with the
    cursor left part way, so no threshold on the store's size can pass."""
    app, scope, context, archives, expiry = archived_store(
        tmp_path, 3 if layout == "one_page_and_one" else 2
    )
    clock = [expiry - 7 * DAY - 1]
    getter = lambda: clock[0]
    if layout == "one_page_and_one":
        Maintenance(app.storage, lambda _: KEY, getter).run(request(scope, max_items=2))
        assert cursor(app.storage, scope) == archives[1]
        max_items = 2
    else:
        YieldsAfter(app.storage, getter, 1).run(request(scope, max_items=10))
        assert cursor(app.storage, scope) == archives[0]
        max_items = 10
    assert expiry_notices(app.storage) == []
    clock[0] = expiry - 7 * DAY + 3600  # the first run in the last seven days
    Maintenance(app.storage, lambda _: KEY, getter).run(request(scope, max_items=max_items))
    assert announced(app, scope, context, archives, expiry)


def test_128_a_run_that_yields_part_way_has_written_the_notices(tmp_path):
    """Case 2: the first run in the last seven days yields after one item; every archive,
    reached or not, has its notice."""
    app, scope, context, archives, expiry = archived_store(tmp_path, 3)
    clock = [expiry - 7 * DAY + 3600]
    result = YieldsAfter(app.storage, lambda: clock[0], 1).run(request(scope, max_items=10))
    assert result["status"] == "busy"
    assert announced(app, scope, context, archives, expiry)


@pytest.mark.parametrize("held", ["paused", "cancelled", "clock_rollback", "busy", "locked"])
def test_128_a_run_that_does_nothing_writes_none_and_the_next_run_does(tmp_path, held):
    """Case 3: a run paused, cancelled, held by a clock rollback, or turned away as busy
    before it reads anything writes no notice; the next run that is none of those does."""
    app, scope, context, archives, expiry = archived_store(tmp_path, 1)
    clock = [expiry - 7 * DAY + 3600]
    maintenance = Maintenance(app.storage, lambda _: KEY, lambda: clock[0])
    store, pair = app.storage, app.storage._task_scope(scope)
    run = request(scope)
    if held == "paused":
        maintenance.run(request(scope, "pause"))
    elif held == "cancelled":
        maintenance.run(request(scope, "cancel"))
    elif held == "clock_rollback":
        # As a run with the clock a day ahead left it; the clock has since been set back.
        with store._connect(True) as c:
            c.execute(
                "UPDATE maintenance_control SET last_clock=? WHERE scope=?", (clock[0] + DAY, pair)
            )
    elif held == "busy":
        run = dict(run, interactive_busy=True)
    if held == "locked":
        # Another holder of the lock, as a second run would be.
        with maintenance_lock(store.path.with_suffix(".maintenance.lock")):
            result = maintenance.run(run)
    else:
        result = maintenance.run(run)
    expected = {"paused": "paused", "cancelled": "canceled", "clock_rollback": "paused"}
    assert result["status"] == expected.get(held, "busy")
    assert expiry_notices(store) == []
    if held in {"paused", "cancelled"}:
        maintenance.run(request(scope, "resume"))
    clock[0] += DAY if held == "clock_rollback" else 3600  # the clock catches up
    maintenance.run(request(scope))
    assert announced(app, scope, context, archives, expiry)


def test_128_the_notice_is_written_by_the_first_eligible_run_not_the_second(tmp_path):
    """Case 4: a run just before the last seven days writes none; the first run in them,
    at their first instant, writes the notice, dated at the expiry."""
    app, scope, context, archives, expiry = archived_store(tmp_path, 1)
    clock = [expiry - 7 * DAY - 1]
    maintenance = Maintenance(app.storage, lambda _: KEY, lambda: clock[0])
    maintenance.run(request(scope))
    assert expiry_notices(app.storage) == []
    clock[0] = expiry - 7 * DAY
    maintenance.run(request(scope))
    assert announced(app, scope, context, archives, expiry)


def test_128_an_expired_archive_with_no_notice_is_retired_by_the_run_that_reaches_it(tmp_path):
    """Case 5: no run in the archive's last seven days, so no notice was ever written; the
    first run after the expiry retires it all the same."""
    app, scope, _, archives, expiry = archived_store(tmp_path, 1)
    clock = [expiry - 7 * DAY - 1]
    maintenance = Maintenance(app.storage, lambda _: KEY, lambda: clock[0])
    maintenance.run(request(scope))
    assert expiry_notices(app.storage) == []
    clock[0] = expiry + 3600
    assert maintenance.run(request(scope))["processed"] == 1
    with app.storage._connect() as c:
        rows = c.execute("SELECT count(*) FROM artifacts").fetchone()[0]
    file = app.storage._artifact_directory(app.storage._task_scope(scope)) / archives[0]
    assert (rows, file.exists()) == (0, False)


@pytest.mark.parametrize("other", ["another_scope", "deleted_task", "already_retired"])
def test_128_no_notice_for_an_archive_the_run_does_not_admit(tmp_path, other):
    """Case 6: no notice for an archive in another scope, of a deleted task, or already
    retired. Each then gets one once admitted, which shows it was in its last week."""
    app, scope, context, archives, expiry = archived_store(tmp_path, 1)
    store, pair = app.storage, app.storage._task_scope(scope)
    clock = [expiry - 7 * DAY + 3600]
    maintenance = Maintenance(store, lambda _: KEY, lambda: clock[0])
    runner = scope
    if other == "another_scope":
        runner = dict(scope, project_id=str(uuid4()))
        artifact(app, runner, {"task_id": str(uuid4())}, b"the other scope's item", clock[0])
    elif other == "deleted_task":
        # The moment between a deletion's commit and its erasure.
        with store._connect(True) as c:
            c.execute(
                "UPDATE tasks SET deleted=1 WHERE scope=? AND task=?", (pair, context["task_id"])
            )
    else:
        # The moment between `_retire` marking the archive and its removal.
        with store._connect(True) as c:
            c.execute(
                "UPDATE artifacts SET retention='retired' WHERE scope=? AND artifact_id=?",
                (pair, archives[0]),
            )
    maintenance.run(request(runner))
    assert expiry_notices(store) == []
    with store._connect(True) as c:
        c.execute("UPDATE tasks SET deleted=0 WHERE scope=?", (pair,))
        c.execute(
            "UPDATE artifacts SET retention='archive' WHERE scope=? AND kind='archive'", (pair,)
        )
    maintenance.run(request(scope))
    assert announced(app, scope, context, archives, expiry)
