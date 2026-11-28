"""LEARN SL-9: discovery erasure (Consiliency/jevdrill#138, #144 and #21's delete-discovery half).

A finished deletion of a discovery, requested or imported, leaves neither the
discovery's recovered metadata nor a notice row naming its items in the store's files.
Until then it answers as `delete_task` does since SL-2: the existing storage failure,
with the deletion committed.

Two checks, used throughout:

- the discovery's domain label, a synthetic value no other record holds, is searched
  as bytes in every file the store writes under its directory: the database, its
  write-ahead log, any rollback journal and the artifact files;
- its item identities (its content artifacts, and the discovery identity they are
  filed under) are searched in the notice rows only, `lifecycle_notices` and
  `notices`, every column. Not in whole files: the plan's non-claim leaves a deleted
  discovery's identities in the decisions and retries of tasks routed with it.

The tests hold another connection's read transaction open themselves, so nothing
here depends on timing. All values are synthetic; nothing reaches an OS key store.
"""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from jevdrill.contracts import ContractError, canonical_digest
from jevdrill.integrations.archive import encode_archive
from jevdrill.maintenance import Maintenance
from jevdrill.storage import SQLiteStorage

STORAGE_FAILURE = {
    "schema_version": "1",
    "status": "storage_failure",
    "code": "infrastructure_failure",
}
REVISIONS = dict.fromkeys(
    (
        "authorization_digest",
        "catalog_digest",
        "catalog_revision",
        "content_revision",
        "descriptions_digest",
        "policy_digest",
        "settings_revision",
        "taxonomy_revision",
    ),
    "synthetic-revision",
)


def store_files(store):
    """Every file the store writes under its own directory, but its shared-memory file.

    The shared-memory file holds only the write-ahead log's index, never row content.
    It is not opened: closing a descriptor on it would drop this process's SQLite
    locks on it (POSIX), including the held reader's, and on Windows another
    connection's locks on it can refuse the read.
    """
    return sorted(
        path
        for path in store.path.parent.rglob("*")
        if path.is_file() and not path.name.endswith("-shm")
    )


def found(store, value):
    """The store files that hold `value`, searched as bytes."""
    needle = value.encode()
    return [path.name for path in store_files(store) if needle in path.read_bytes()]


def notice_rows(store, identities):
    """The notice rows, of either notice table, in which any of `identities` appears."""
    with store._connect() as connection:
        rows = [
            (table, *row)
            for table in ("lifecycle_notices", "notices")
            for row in connection.execute(f"SELECT * FROM {table}").fetchall()
        ]
    return [row for row in rows if any(i in json.dumps(row) for i in identities)]


def metadata(store, discovery_id):
    with store._connect() as connection:
        return connection.execute(
            "SELECT domains FROM recovered_discovery_metadata WHERE discovery_id=?",
            (discovery_id,),
        ).fetchone()


def reader(store):
    """Another connection holding a read transaction open until it is closed."""
    connection = sqlite3.connect(store.path, isolation_level=None)
    connection.execute("BEGIN")
    connection.execute("SELECT count(*) FROM recovered_discovery_metadata").fetchone()
    return connection


def idle(store):
    """An idle connection kept open, so that no other close is the last one.

    SQLite checkpoints when its last connection closes; with this one open, only the
    deletion's own checkpoint can erase anything.
    """
    connection = sqlite3.connect(store.path, isolation_level=None)
    connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
    return connection


def bundle(scope, objectives, discoveries=()):
    return {
        "schema_version": "1",
        "scope": SQLiteStorage._task_scope(scope),
        "tasks": {},
        "objectives": objectives,
        "learning_policy": {},
        "decisions": [],
        "events": [],
        "contexts": [],
        "discoveries": list(discoveries),
        "artifacts": [],
    }


class Discovery:
    """One imported discovery, of its own objective unless one is given, with content
    items and notices."""

    def __init__(self, store, scope, objective=None):
        self.store, self.scope = store, scope
        self.objective, self.id = objective or str(uuid4()), str(uuid4())
        self.label = f"sl9-synthetic-domain-{uuid4().hex}"
        record = {
            "scope": dict(scope, operation="route"),
            "discovery_ref": {
                "discovery_id": self.id,
                "work_objective_id": self.objective,
                "trace_digest": uuid4().hex * 2,
            },
            "status": "no_optional_guidance",
            "revisions": REVISIONS,
            "guidance_refs": [],
            "domains": [self.label],
        }
        self.record = record
        self.bundle = bundle(scope, {self.objective: False}, [record])
        assert store.import_recovery(scope, self.bundle, 0.0) == 0
        self.items = [self.id]
        for kind in ("raw_task", "context"):
            identity = store.stage_artifact(
                scope,
                self.id,
                f"{kind}-{uuid4().hex}".encode(),
                kind=kind,
                retention="active",
                encryption="none",
                retain_raw_tasks=True,
                discovery_id=self.id,
            )
            assert identity is not None
            self.items.append(identity)
        maintenance = Maintenance(store, key_provider=lambda _: None)
        maintenance._notice(scope, self.id, "item_failed", self.items[1])
        maintenance._notice(scope, self.id, "archive_prompt", self.items[2], 0.0)
        store.archive(scope, self.id, b"unarchived", lambda: None, lambda c, k: c)
        # Preconditions: the label is on disk, and each notice row names an item.
        assert metadata(store, self.id) is not None
        assert found(store, self.label)
        assert len(notice_rows(store, self.items)) == 3

    @property
    def discover_scope(self):
        return dict(self.scope, operation="discover")

    def deleted(self):
        return {"schema_version": "1", "status": "deleted", "work_objective_id": self.objective}

    def erased(self):
        """The two checks: label in no store file, no item identity in a notice row."""
        return found(self.store, self.label) == [] and notice_rows(self.store, self.items) == []


def other_store(tmp_path):
    directory = tmp_path / f"source-{uuid4().hex}"
    directory.mkdir()
    return SQLiteStorage(directory / "route.db")


def deletion_record(tmp_path, scope, objective, carried=None):
    """The objective's deletion record, as another store exports it after deleting it.

    With `carried`, the bundle also carries one ordinary task's retained content, so an
    import of it has a nonzero count.
    """
    source = other_store(tmp_path)
    source.delete_discovery(dict(scope, operation="discover"), objective)
    if carried is not None:
        source.stage_artifact(
            scope,
            str(uuid4()),
            carried,
            kind="raw_task",
            retention="active",
            encryption="none",
            retain_raw_tasks=True,
        )
    body = source.export_recovery(scope)
    assert body["objectives"] == {objective: True} and body["discoveries"] == []
    return body


@pytest.fixture
def store(tmp_path):
    directory = tmp_path / "store"
    directory.mkdir()
    return SQLiteStorage(directory / "route.db")


@pytest.fixture
def scope():
    return {
        "project_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "producer": "synthetic-host",
        "operation": "route",
    }


def test_1_requested_deletion_erases_metadata_and_notices(store, scope):
    made = Discovery(store, scope)
    keeper = idle(store)
    try:
        assert store.delete_discovery(made.discover_scope, made.objective) == made.deleted()
        assert found(store, made.label) == []
        assert notice_rows(store, made.items) == []
    finally:
        keeper.close()


def test_2_imported_deletion_erases_metadata_and_notices(store, scope, tmp_path):
    made = Discovery(store, scope)
    record = deletion_record(tmp_path, scope, made.objective)
    keeper = idle(store)
    try:
        assert store.import_recovery(scope, record, 0.0) == 0
        assert found(store, made.label) == []
        assert notice_rows(store, made.items) == []
        # The discovery imported again after its deletion does not come back.
        assert store.import_recovery(scope, made.bundle, 0.0) == 0
        assert metadata(store, made.id) is None
        assert found(store, made.label) == []
        assert notice_rows(store, made.items) == []
    finally:
        keeper.close()


@pytest.mark.parametrize("path", ["request", "import"])
def test_1_and_2_finished_deletion_leaves_no_digest_of_the_discovery_record(
    store, scope, tmp_path, path
):
    """The imported discovery's request digest is a digest of its record, domains
    included, so a guessed label could be confirmed against it (#148, B1)."""
    made = Discovery(store, scope)
    digest = canonical_digest(made.record)  # with its real label
    assert found(store, digest)
    keeper = idle(store)
    try:
        if path == "request":
            assert store.delete_discovery(made.discover_scope, made.objective) == made.deleted()
        else:
            assert (
                store.import_recovery(scope, deletion_record(tmp_path, scope, made.objective), 0.0)
                == 0
            )
        assert found(store, digest) == []
    finally:
        keeper.close()


@pytest.mark.parametrize("path", ["request", "import"])
def test_1_and_2_every_discovery_of_the_objective_is_erased(store, scope, tmp_path, path):
    """An objective can have several discoveries; the deletion erases every one."""
    first = Discovery(store, scope)
    second = Discovery(store, scope, objective=first.objective)
    keeper = idle(store)
    try:
        if path == "request":
            assert store.delete_discovery(first.discover_scope, first.objective) == first.deleted()
        else:
            assert (
                store.import_recovery(scope, deletion_record(tmp_path, scope, first.objective), 0.0)
                == 0
            )
        for made in (first, second):
            assert made.erased()
            assert metadata(store, made.id) is None
            assert found(store, canonical_digest(made.record)) == []
    finally:
        keeper.close()


def test_a_repeat_of_a_deleted_discovery_request_under_its_key_is_refused(store, scope):
    """With its digest cleared, the deleted request's key is still not taken as new."""
    discover_scope = dict(scope, operation="discover")
    objective, key, digest = str(uuid4()), str(uuid4()), uuid4().hex * 2
    first = store.reserve_discovery(discover_scope, key, digest, objective, {}, {"o": "x"})
    assert first["created"]
    assert store.delete_discovery(discover_scope, objective)["status"] == "deleted"
    with pytest.raises(ContractError, match="objective deleted"):
        store.reserve_discovery(discover_scope, key, digest, objective, {}, {"o": "x"})
    # The same key and digest for another objective: a conflict, neither a new
    # discovery nor the deleted one handed back.
    with pytest.raises(ContractError, match="idempotency conflict"):
        store.reserve_discovery(discover_scope, key, digest, str(uuid4()), {}, {"o": "x"})
    with store._connect() as connection:
        rows = connection.execute(
            "SELECT discovery_id FROM discoveries WHERE request_key=?", (key,)
        ).fetchall()
    assert rows == [(first["discovery_id"],)]


def committed(store, made):
    """Nothing of the deleted discovery is readable through storage."""
    assert metadata(store, made.id) is None
    assert notice_rows(store, made.items) == []
    with pytest.raises(ContractError, match="objective deleted"):
        store.load_discovery(made.discover_scope, made.id)
    return True


def test_3_requested_deletion_is_unfinished_while_a_reader_holds_the_log(store, scope):
    made = Discovery(store, scope)
    keeper, held = idle(store), reader(store)
    try:
        with pytest.raises(sqlite3.OperationalError, match="not yet erased"):
            store.delete_discovery(made.discover_scope, made.objective)
        assert found(store, made.label)
        assert committed(store, made)
        held.close()
        assert found(store, made.label)  # closing the reader alone erases nothing
        assert store.delete_discovery(made.discover_scope, made.objective) == made.deleted()
        assert made.erased()
    finally:
        held.close()
        keeper.close()


def every_row(store):
    """Every row of every table, as storage reads it."""
    with store._connect() as connection:
        tables = [
            name
            for (name,) in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        return {
            table: sorted(map(repr, connection.execute(f"SELECT * FROM {table}")))
            for table in tables
        }


def checkpoint_blocked(store):
    """True if a checkpoint cannot finish now, as the import's own could not."""
    connection = sqlite3.connect(store.path, timeout=0, isolation_level=None)
    try:
        return connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 1
    finally:
        connection.close()


# The two imports below, side by side, each run with a reader blocking the checkpoint.


def test_3_import_applying_a_deletion_record_is_unfinished_while_a_reader_holds_the_log(
    store, scope, tmp_path
):
    made = Discovery(store, scope)
    record = deletion_record(tmp_path, scope, made.objective, carried=b"carried-" + uuid4().bytes)
    keeper, held = idle(store), reader(store)
    try:
        # The import answers the failure `delete_task` raises, not its count.
        with pytest.raises(sqlite3.OperationalError, match="not yet erased"):
            store.import_recovery(scope, record, 0.0)
        assert checkpoint_blocked(store)
        assert found(store, made.label)
        assert committed(store, made)
        applied = every_row(store)
        held.close()
        assert found(store, made.label)
        # The repeat answers as finished, with the bundle's count: its one carried
        # artifact, which the first import already restored.
        assert store.import_recovery(scope, record, 0.0) == 1
        assert made.erased()
        # Nothing is applied twice: every table is as the first import left it.
        assert every_row(store) == applied
        assert len(applied["artifacts"]) == 1
    finally:
        held.close()
        keeper.close()


@pytest.mark.parametrize("bundle", ["another_discovery", "the_deleted_discovery_again"])
def test_3_import_applying_none_answers_as_on_main_while_a_reader_holds_the_log(
    store, scope, tmp_path, bundle
):
    made = Discovery(store, scope)
    keeper = idle(store)
    held = None
    try:
        if bundle == "another_discovery":
            body = Discovery(other_store(tmp_path), scope).bundle
        else:
            # The store holds the deletion; the bundle, the discovery's own, carries none.
            store.delete_discovery(made.discover_scope, made.objective)
            body = made.bundle
            # One unrelated write, so that the log the reader starts on is not empty (the
            # deletion's own checkpoint emptied it) and the reader can block a checkpoint.
            store.archive(scope, str(uuid4()), b"unarchived", lambda: None, lambda c, k: c)
        assert True not in body["objectives"].values()
        held = reader(store)
        # As on main: the count, with the blocked checkpoint's result ignored.
        assert store.import_recovery(scope, body, 0.0) == 0
        assert checkpoint_blocked(store)
        if bundle == "the_deleted_discovery_again":
            assert made.erased()
    finally:
        if held is not None:
            held.close()
        keeper.close()


def test_3_import_repeated_under_the_same_reader_is_still_unfinished(store, scope, tmp_path):
    """The repeat while the first import's reader is still open has nothing new to
    erase, but the label is still on disk: it answers the storage failure again."""
    made = Discovery(store, scope)
    record = deletion_record(tmp_path, scope, made.objective)
    keeper, held = idle(store), reader(store)
    try:
        with pytest.raises(sqlite3.OperationalError, match="not yet erased"):
            store.import_recovery(scope, record, 0.0)
        assert found(store, made.label)
        with pytest.raises(sqlite3.OperationalError, match="not yet erased"):
            store.import_recovery(scope, record, 0.0)
        assert found(store, made.label)
        held.close()
        assert store.import_recovery(scope, record, 0.0) == 0
        assert made.erased()
    finally:
        held.close()
        keeper.close()


def applied_backup(store, scope, tmp_path):
    """An ordinary backup: new content, and a discovery deletion record this store has
    already applied. A bundle carries every tombstone its source recorded."""
    made = Discovery(store, scope)
    backup = deletion_record(tmp_path, scope, made.objective, carried=b"new-" + uuid4().bytes)
    assert store.delete_discovery(made.discover_scope, made.objective) == made.deleted()
    return made, backup


def test_3_backup_with_an_applied_deletion_record_answers_imported_with_no_reader(
    store, scope, tmp_path
):
    made, backup = applied_backup(store, scope, tmp_path)
    keeper = idle(store)
    try:
        assert store.import_recovery(scope, backup, 0.0) == 1  # as on main
        assert len(every_row(store)["artifacts"]) == 1  # the new content
        assert made.erased()
    finally:
        keeper.close()


def test_3_backup_with_an_applied_deletion_record_is_unfinished_while_a_reader_holds_the_log(
    store, scope, tmp_path
):
    """The stated cost: main answers `imported` here. The work is committed, and the
    repeat once the reader closes answers as finished."""
    keeper = idle(store)
    held = None
    try:
        made, backup = applied_backup(store, scope, tmp_path)
        # One unrelated write, so that the reader can block a checkpoint (see above).
        store.archive(scope, str(uuid4()), b"unarchived", lambda: None, lambda c, k: c)
        held = reader(store)
        with pytest.raises(sqlite3.OperationalError, match="not yet erased"):
            store.import_recovery(scope, backup, 0.0)
        assert checkpoint_blocked(store)
        applied = every_row(store)
        assert len(applied["artifacts"]) == 1  # committed: the new content is in
        held.close()
        assert store.import_recovery(scope, backup, 0.0) == 1
        assert every_row(store) == applied
        assert made.erased()
    finally:
        if held is not None:
            held.close()
        keeper.close()


def test_3_import_erasing_what_an_applied_tombstone_left_is_unfinished_while_a_reader_holds_the_log(
    store, scope, tmp_path
):
    """A store that holds the tombstone but still the discovery's rows, as main's
    `delete_discovery` left them: importing the tombstone again erases them, so it is
    not finished while the reader blocks the checkpoint."""
    made = Discovery(store, scope)
    record = deletion_record(tmp_path, scope, made.objective)
    keeper = idle(store)
    held = None
    try:
        with store._connect(True) as connection:
            connection.execute(
                "UPDATE discovery_objectives SET deleted=1 WHERE objective=?", (made.objective,)
            )
        assert metadata(store, made.id) is not None
        held = reader(store)
        with pytest.raises(sqlite3.OperationalError, match="not yet erased"):
            store.import_recovery(scope, record, 0.0)
        assert checkpoint_blocked(store)
        assert committed(store, made)
        held.close()
        assert store.import_recovery(scope, record, 0.0) == 0
        assert made.erased()
    finally:
        if held is not None:
            held.close()
        keeper.close()


def test_3_import_newly_tombstoning_a_discovery_is_unfinished_while_a_reader_holds_the_log(
    store, scope, tmp_path
):
    """A discovery that has only its own row (a reserved request's seed): the new
    tombstone clears the seed, which no deleted row reports, so the import that
    applies it is not finished while the reader blocks the checkpoint."""
    objective, sentinel = str(uuid4()), f"sl9-synthetic-seed-{uuid4().hex}"
    discover_scope = dict(scope, operation="discover")
    record = deletion_record(tmp_path, scope, objective)
    keeper = idle(store)
    held = None
    try:
        store.reserve_discovery(
            discover_scope, str(uuid4()), "digest", objective, {}, {"objective": sentinel}
        )
        assert found(store, sentinel)
        held = reader(store)
        with pytest.raises(sqlite3.OperationalError, match="not yet erased"):
            store.import_recovery(scope, record, 0.0)
        assert checkpoint_blocked(store)
        assert found(store, sentinel)
        held.close()
        assert store.import_recovery(scope, record, 0.0) == 0
        assert found(store, sentinel) == []
    finally:
        if held is not None:
            held.close()
        keeper.close()


def command_line(store, arguments, stdin="{}"):
    """The CLI in a child process, as a host calls it."""
    result = subprocess.run(
        [sys.executable, "-m", "jevdrill.cli", "--storage", str(store.path), *arguments],
        input=stdin,
        text=True,
        capture_output=True,
        cwd=Path(store.path).parent,
        check=False,
    )
    return result.returncode, json.loads(result.stdout)


def test_4_delete_discovery_command_answers_a_storage_failure_then_deleted(store, scope):
    made = Discovery(store, scope)
    arguments = ["delete-discovery", "--work-objective-id", made.objective]
    arguments += ["--scope", json.dumps(made.discover_scope)]
    keeper, held = idle(store), reader(store)
    try:
        assert command_line(store, arguments) == (4, STORAGE_FAILURE)
        held.close()
        assert found(store, made.label)
        assert command_line(store, arguments) == (0, made.deleted())
        assert made.erased()  # before the last close, which would checkpoint
    finally:
        held.close()
        keeper.close()


def test_4_recovery_import_command_answers_a_storage_failure_then_imported(store, scope, tmp_path):
    made = Discovery(store, scope)
    key = Fernet.generate_key()
    request = {
        "schema_version": "1",
        "scope": scope,
        "action": "import",
        "artifact_id": None,
        "recovery_key": key.decode("ascii"),
        "encrypted_bundle": encode_archive(
            deletion_record(tmp_path, scope, made.objective), key
        ).decode("ascii"),
    }
    keeper, held = idle(store), reader(store)
    imported = {
        "schema_version": "1",
        "status": "imported",
        "encrypted_bundle": None,
        "restored_count": 0,
    }
    try:
        assert command_line(store, ["recovery"], json.dumps(request)) == (4, STORAGE_FAILURE)
        held.close()
        assert found(store, made.label)
        assert command_line(store, ["recovery"], json.dumps(request)) == (0, imported)
        assert made.erased()
    finally:
        held.close()
        keeper.close()


def everything_of(store, made, task):
    """Another discovery's metadata, notice rows and stored result; a task's notices."""
    return (
        metadata(store, made.id),
        notice_rows(store, made.items),
        store.load_discovery(made.discover_scope, made.id),
        notice_rows(store, [task]),
    )


@pytest.mark.parametrize("path", ["request", "import"])
def test_5_nothing_else_goes(store, scope, tmp_path, path):
    deleted, kept = Discovery(store, scope), Discovery(store, scope)
    task = str(uuid4())  # an ordinary task with a notice of its own
    store.archive(scope, task, b"unarchived", lambda: None, lambda c, k: c)
    before = everything_of(store, kept, task)
    assert before[0] is not None and len(before[1]) == 3 and len(before[3]) == 1
    if path == "request":
        store.delete_discovery(deleted.discover_scope, deleted.objective)
    else:
        store.import_recovery(scope, deletion_record(tmp_path, scope, deleted.objective), 0.0)
    assert metadata(store, deleted.id) is None  # the deletion happened
    assert everything_of(store, kept, task) == before
    assert found(store, kept.label)


@pytest.mark.parametrize("path", ["request", "import"])
def test_6_no_notice_is_written_for_a_discovery_deleted_while_an_archive_key_is_pending(
    store, scope, tmp_path, path
):
    """The deletion commits while `archive_artifact` waits for its key, which then does
    not come: the notice it would write is refused, as it is with a key (#148, vendor)."""
    made = Discovery(store, scope)
    record = deletion_record(tmp_path, scope, made.objective) if path == "import" else None
    keeper = idle(store)
    ran = []

    def provider():
        if path == "request":
            assert store.delete_discovery(made.discover_scope, made.objective) == made.deleted()
        else:
            assert store.import_recovery(scope, record, 0.0) == 0
        assert made.erased()
        ran.append(True)  # and no key comes

    try:
        with pytest.raises(ContractError, match="objective deleted"):
            store.archive_artifact(scope, made.items[1], provider, lambda c, k: c)
        assert ran == [True]
        assert notice_rows(store, made.items) == []
        assert store.load_notices(scope) == []
        assert made.erased()
    finally:
        keeper.close()


def task_rows(store, task):
    with store._connect() as connection:
        return connection.execute(
            "SELECT artifact_id FROM artifacts WHERE task=?", (task,)
        ).fetchall()


def has_artifact(store, identity):
    with store._connect() as connection:
        return (
            connection.execute(
                "SELECT 1 FROM artifacts WHERE artifact_id=?", (identity,)
            ).fetchone()
            is not None
        )


@pytest.mark.parametrize(
    "case",
    [
        "the_store_that_erased_it",
        "the_store_that_erased_it_and_a_bundle_without_the_record",
        "a_store_that_imported_the_deletion_record_first",
    ],
)
def test_7_a_replayed_export_does_not_restore_a_deleted_discoverys_item(
    store, scope, tmp_path, case
):
    """An export made while a discovery's item was staged under its identity, but not
    yet linked to it, is replayed after the discovery's deletion (#148, vendor)."""
    made, kept = Discovery(store, scope), Discovery(store, scope)
    items = {}
    for owner in (made, kept):
        text = f"sl9-synthetic-item-{uuid4().hex}"
        identity = store.stage_artifact(
            scope, owner.id, text.encode(), kind="context", retention="active", encryption="none"
        )
        items[owner.id] = (identity, text)
    (made_item, made_text), (kept_item, _) = items[made.id], items[kept.id]
    export = store.export_recovery(scope)
    assert {(a["task"], bytes.fromhex(a["content"]).decode()) for a in export["artifacts"]} == {
        (owner, text) for owner, (_, text) in items.items()
    }
    assert not export["objectives"].get(made.objective)
    # Linked to its discovery now: the same artifact.
    assert (
        store.stage_artifact(
            scope,
            made.id,
            made_text.encode(),
            kind="context",
            retention="active",
            encryption="none",
            discovery_id=made.id,
        )
        == made_item
    )
    record = deletion_record(tmp_path, scope, made.objective)
    target = other_store(tmp_path) if case.startswith("a_store_that_imported") else store
    replay = export
    if case.endswith("a_bundle_without_the_record"):
        # An export made while a discovery has no result carries no record of it.
        replay = dict(
            export,
            discoveries=[
                r for r in export["discoveries"] if r["discovery_ref"]["discovery_id"] != made.id
            ],
        )
        assert len(replay["discoveries"]) == len(export["discoveries"]) - 1
    keeper = idle(target)
    try:
        assert target.import_recovery(scope, record, 0.0) == 0
        if target is store:
            assert not has_artifact(store, made_item)
            assert found(store, made_text) == []
        assert target.import_recovery(scope, replay, 0.0) == 1  # kept's item
        assert task_rows(target, made.id) == []
        assert found(target, made_text) == []
        assert has_artifact(target, kept_item)
        Maintenance(target, key_provider=lambda _: None)._notice(
            scope, made.id, "archive_prompt", made_item, 0.0
        )
        assert notice_rows(target, [made.id, made_item]) == []
        if target is store:
            assert made.erased()
    finally:
        keeper.close()
