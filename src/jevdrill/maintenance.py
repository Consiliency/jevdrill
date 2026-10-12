"""Bounded retention, process locks and authenticated deletion-safe recovery."""

import hashlib
import json
import platform
import plistlib
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from time import time
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from .contracts import ContractError, canonical_digest, parse_contract
from .integrations.archive import archive_key, decrypt_archive, encode_archive, maintenance_lock
from .storage import SQLiteStorage

DAY = 86400


class Maintenance:
    def __init__(
        self,
        storage: SQLiteStorage,
        key_provider: Callable[[str], bytes | None] = archive_key,
        clock: Callable[[], float] = time,
    ) -> None:
        self.storage, self.key_provider, self.clock = storage, key_provider, clock

    def _notice(
        self,
        scope: Mapping[str, str],
        task: str,
        kind: str,
        identity: str,
        deadline: float | None = None,
    ) -> None:
        pair = self.storage._task_scope(scope)
        notice = {
            "notice_id": str(uuid5(NAMESPACE_URL, canonical_digest([pair, task, kind, identity]))),
            "kind": "archive_prompt" if kind == "archive_prompt" else "decision_required",
            "summary": {
                "archive_prompt": "Content is 30 days old. Encrypted archival is due after seven days.",
                "archive_expiry": "Archived content expires in seven days. Restore or export it before the deadline.",
                "archive_key_missing": "Archive key unavailable; content remains local. Configure the supported OS key store and retry.",
                "clock_rollback": "The clock moved backwards; retention remains paused until it catches up.",
            }[kind],
            "deadline": datetime.fromtimestamp(deadline, UTC).isoformat().replace("+00:00", "Z")
            if deadline is not None
            else None,
            "automatic_action": "archive" if kind == "archive_prompt" else "none",
        }
        with self.storage._connect(True) as c:
            if self.storage._admit(c, pair, task):
                c.execute(
                    "INSERT OR REPLACE INTO lifecycle_notices VALUES (?,?,?,?)",
                    (pair, task, notice["notice_id"], self.storage._encode(notice)),
                )

    def _interactive(self, request: Mapping[str, Any]) -> bool:
        if request["interactive_busy"]:
            return True
        if request["request_path"] is None:
            return False
        current = parse_contract(
            "MaintenanceRequest",
            json.loads(Path(request["request_path"]).read_text(encoding="utf-8")),
        ).payload()
        if current["scope"] != request["scope"]:
            raise ContractError("maintenance request scope changed")
        return bool(current["interactive_busy"])

    def _key(self, pair: str) -> bytes | None:
        try:
            return self.key_provider(canonical_digest(pair))
        except (OSError, TimeoutError, ValueError):
            return None

    def run(self, request: Mapping[str, Any]) -> dict[str, Any]:
        request = parse_contract("MaintenanceRequest", request).payload()
        scope = request["scope"]
        pair = self.storage._task_scope(scope)
        now = self.clock()
        result: dict[str, Any] = {
            "schema_version": "1",
            "status": "completed",
            "processed": 0,
            "pending": 0,
            "notices": [],
            "scheduler_instructions": [],
        }
        action = request["action"]
        if action == "schedule":
            result.update(status="schedule_proposed", scheduler_instructions=self.schedule(request))
            return result
        with self.storage._connect(True) as c:
            if action in {"pause", "resume", "cancel"}:
                c.execute(
                    "INSERT INTO maintenance_control VALUES (?,?,?,NULL) ON CONFLICT(scope) DO UPDATE SET action=excluded.action",
                    (pair, "run" if action == "resume" else action, now),
                )
                result["status"] = {"pause": "paused", "resume": "completed", "cancel": "canceled"}[
                    action
                ]
                return result
        if self._interactive(request):
            result["status"] = "busy"
            return result
        with maintenance_lock(self.storage.path.with_suffix(".maintenance.lock")) as acquired:
            if not acquired:
                result["status"] = "busy"
                return result
            with self.storage._connect(True) as c:
                control = c.execute(
                    "SELECT action,last_clock,cursor FROM maintenance_control WHERE scope=?",
                    (pair,),
                ).fetchone()
                if control and control[0] != "run":
                    result["status"] = "paused" if control[0] == "pause" else "canceled"
                    return result
                if control and now < control[1]:
                    result["status"] = "paused"
                else:
                    c.execute(
                        "INSERT INTO maintenance_control VALUES (?,'run',?,NULL) ON CONFLICT(scope) DO UPDATE SET last_clock=excluded.last_clock",
                        (pair, now),
                    )
                cursor = control[2] if control else None
                rows = c.execute(
                    "SELECT a.artifact_id,a.task,a.kind,a.digest,l.created,l.prompted,l.archived FROM artifacts a JOIN artifact_lifecycle l ON a.scope=l.scope AND a.artifact_id=l.artifact_id JOIN tasks t ON a.scope=t.scope AND a.task=t.task WHERE a.scope=? AND t.deleted=0 AND a.retention!='retired' AND (? IS NULL OR a.artifact_id>?) ORDER BY a.artifact_id LIMIT ?",
                    (pair, cursor, cursor, request["max_items"] + 1),
                ).fetchall()
            if result["status"] == "paused":
                if rows:
                    self._notice(scope, rows[0][1], "clock_rollback", rows[0][0])
                result["notices"] = self.storage.load_notices(scope)
                return result
            for identity, task, kind, digest, created, prompted, archived in rows[
                : request["max_items"]
            ]:
                with self.storage._connect() as c:
                    action = c.execute(
                        "SELECT action FROM maintenance_control WHERE scope=?", (pair,)
                    ).fetchone()[0]
                if action != "run" or self._interactive(request):
                    result["status"] = (
                        "busy" if action == "run" else "paused" if action == "pause" else "canceled"
                    )
                    break
                if archived is not None:
                    expiry = archived + 365 * DAY
                    if now >= expiry:
                        self._retire(scope, identity)
                        result["processed"] += 1
                    elif now >= expiry - 7 * DAY:
                        self._notice(scope, task, "archive_expiry", identity, expiry)
                elif kind in {"raw_task", "raw_output", "context"} and now >= created + 30 * DAY:
                    if prompted is None:
                        self._notice(scope, task, "archive_prompt", identity, now + 7 * DAY)
                        with self.storage._connect(True) as c:
                            c.execute(
                                "UPDATE artifact_lifecycle SET prompted=? WHERE scope=? AND artifact_id=?",
                                (now, pair, identity),
                            )
                        result["processed"] += 1
                    elif now >= prompted + 7 * DAY:
                        key = self._key(pair)
                        if key is None:
                            self._notice(scope, task, "archive_key_missing", identity)
                            result["pending"] += 1
                        else:
                            content = (
                                self.storage._artifact_directory(pair) / identity
                            ).read_bytes()
                            if hashlib.sha256(content).hexdigest() != digest:
                                raise ContractError("artifact digest mismatch")
                            body = {
                                "scope": pair,
                                "task": task,
                                "kind": kind,
                                "content": content.hex(),
                                "digest": digest,
                                "source_id": identity,
                            }
                            with self.storage._connect() as c:
                                existing = c.execute(
                                    "SELECT a.artifact_id FROM artifacts a JOIN artifact_lifecycle l ON a.scope=l.scope AND a.artifact_id=l.artifact_id WHERE a.scope=? AND l.source_id=? AND a.kind='archive'",
                                    (pair, identity),
                                ).fetchone()
                            encrypted = (
                                (self.storage._artifact_directory(pair) / existing[0]).read_bytes()
                                if existing
                                else encode_archive(body, key)
                            )
                            if json.loads(decrypt_archive(encrypted, key)) != body:
                                raise ContractError("archive verification failed")
                            archive_id = self.storage.stage_artifact(
                                scope,
                                task,
                                encrypted,
                                kind="archive",
                                retention="archive",
                                encryption="fernet-v1",
                                archive_source=identity,
                                archived_at=now,
                            )
                            assert archive_id is not None
                            if (
                                json.loads(
                                    decrypt_archive(
                                        (
                                            self.storage._artifact_directory(pair) / archive_id
                                        ).read_bytes(),
                                        key,
                                    )
                                )
                                != body
                            ):
                                raise ContractError("durable archive verification failed")
                            self._retire(scope, identity)
                            result["processed"] += 1
                with self.storage._connect(True) as c:
                    c.execute(
                        "UPDATE maintenance_control SET cursor=? WHERE scope=?", (identity, pair)
                    )
            if result["status"] == "completed" and len(rows) <= request["max_items"]:
                with self.storage._connect(True) as c:
                    c.execute("UPDATE maintenance_control SET cursor=NULL WHERE scope=?", (pair,))
            result["pending"] += max(0, len(rows) - request["max_items"])
            result["notices"] = self.storage.load_notices(scope)
        return result

    def _retire(self, scope: Mapping[str, str], identity: str) -> None:
        pair = self.storage._task_scope(scope)
        with self.storage._connect(True) as c:
            row = c.execute(
                "SELECT task FROM artifacts WHERE scope=? AND artifact_id=?", (pair, identity)
            ).fetchone()
            c.execute(
                "UPDATE artifacts SET retention='retired' WHERE scope=? AND artifact_id=?",
                (pair, identity),
            )
            if row:
                for kind in (
                    "archive_prompt",
                    "archive_key_missing",
                    "archive_expiry",
                    "clock_rollback",
                ):
                    notice_id = str(
                        uuid5(NAMESPACE_URL, canonical_digest([pair, row[0], kind, identity]))
                    )
                    c.execute(
                        "DELETE FROM lifecycle_notices WHERE scope=? AND notice_id=?",
                        (pair, notice_id),
                    )
        self.storage.recover_artifacts()

    def schedule(self, request: Mapping[str, Any]) -> list[str]:
        if request["request_path"] is None:
            raise ContractError("schedule requires an explicit request path")
        path = Path(request["request_path"]).resolve()
        current = parse_contract(
            "MaintenanceRequest", json.loads(path.read_text(encoding="utf-8"))
        ).payload()
        if (
            current["action"] != "run"
            or current["scope"] != request["scope"]
            or current["request_path"] != str(path)
        ):
            raise ContractError(
                "scheduler request must be a scoped run with its absolute request path"
            )
        directory = (
            self.storage.path.parent
            / "schedules"
            / canonical_digest(self.storage._task_scope(request["scope"]))[:16]
        )
        directory.mkdir(parents=True, exist_ok=True)
        argv = [
            sys.executable,
            "-m",
            "jevdrill.cli",
            "--storage",
            str(self.storage.path.resolve()),
            "--request-file",
            str(path),
            "maintenance",
        ]
        label = "jevdrill-maintenance"
        if platform.system() == "Linux":
            command = " ".join(
                '"'
                + part.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("%", "%%")
                .replace("$", "$$")
                + '"'
                for part in argv
            )
            service = directory / (label + ".service")
            timer = directory / (label + ".timer")
            service.write_text(
                "[Unit]\nDescription=JEV Drill local maintenance\n[Service]\nType=oneshot\nExecStart="
                + command
                + "\n",
                encoding="utf-8",
            )
            timer.write_text(
                "[Unit]\nDescription=JEV Drill hourly maintenance\n[Timer]\nOnBootSec=5min\nOnUnitActiveSec=1h\n[Install]\nWantedBy=timers.target\n",
                encoding="utf-8",
            )
            files = [str(service), str(timer)]
        elif platform.system() == "Darwin":
            config = directory / (label + ".plist")
            config.write_bytes(
                plistlib.dumps(
                    {
                        "Label": label,
                        "ProgramArguments": argv,
                        "StartInterval": 3600,
                        "RunAtLoad": False,
                    }
                )
            )
            files = [str(config)]
        elif platform.system() == "Windows":
            config = directory / (label + ".xml")
            task = ET.Element(
                "Task",
                {
                    "version": "1.2",
                    "xmlns": "http://schemas.microsoft.com/windows/2004/02/mit/task",
                },
            )
            trigger = ET.SubElement(ET.SubElement(task, "Triggers"), "TimeTrigger")
            ET.SubElement(ET.SubElement(trigger, "Repetition"), "Interval").text = "PT1H"
            ET.SubElement(trigger, "StartBoundary").text = datetime.fromtimestamp(
                self.clock(), UTC
            ).isoformat()
            ET.SubElement(
                ET.SubElement(task, "Settings"), "MultipleInstancesPolicy"
            ).text = "IgnoreNew"
            execute = ET.SubElement(ET.SubElement(task, "Actions"), "Exec")
            ET.SubElement(execute, "Command").text = argv[0]
            ET.SubElement(execute, "Arguments").text = subprocess.list2cmdline(argv[1:])
            config.write_bytes(ET.tostring(task, encoding="utf-8", xml_declaration=True))
            files = [str(config)]
        else:
            raise ContractError("unsupported scheduler platform")
        return [
            "Configuration generated; installation requires an explicit host action.",
            "The host updates interactive_busy in the scoped request file; every bounded item rechecks it.",
            *files,
        ]

    def restore(self, scope: Mapping[str, str], identity: str) -> int:
        pair = self.storage._task_scope(scope)
        with self.storage._connect() as c:
            row = c.execute(
                "SELECT task,digest FROM artifacts WHERE scope=? AND artifact_id=? AND kind='archive'",
                (pair, identity),
            ).fetchone()
        if row is None or self.storage.is_deleted(scope, row[0]):
            raise ContractError("archive unavailable")
        key = self._key(pair)
        if key is None:
            self._notice(scope, row[0], "archive_key_missing", identity)
            raise ContractError("archive key unavailable")
        encrypted = (self.storage._artifact_directory(pair) / identity).read_bytes()
        if hashlib.sha256(encrypted).hexdigest() != row[1]:
            raise ContractError("archive digest mismatch")
        body = json.loads(decrypt_archive(encrypted, key))
        content = bytes.fromhex(body["content"])
        if (
            body["scope"] != pair
            or body["task"] != row[0]
            or hashlib.sha256(content).hexdigest() != body["digest"]
        ):
            raise ContractError("archive scope or content mismatch")
        self.storage.stage_artifact(
            scope,
            row[0],
            content,
            kind=body["kind"],
            retention="active",
            encryption="none",
            retain_raw_tasks=True,
            retain_raw_outputs=True,
            created_at=self.clock(),
        )
        return 1

    def recover(self, request: Mapping[str, Any]) -> dict[str, Any]:
        request = parse_contract("RecoveryRequest", request).payload()
        scope = request["scope"]
        action = request["action"]
        result: dict[str, Any] = {
            "schema_version": "1",
            "status": "restored",
            "encrypted_bundle": None,
            "restored_count": 0,
        }
        if action == "restore":
            if (
                not request["artifact_id"]
                or request["recovery_key"] is not None
                or request["encrypted_bundle"] is not None
            ):
                raise ContractError("restore requires only artifact identity")
            result["restored_count"] = self.restore(scope, request["artifact_id"])
            return result
        if request["artifact_id"] is not None or request["recovery_key"] is None:
            raise ContractError("portable recovery requires an explicit key")
        key = request["recovery_key"].encode("ascii")
        if action in {"export", "backup"}:
            if request["encrypted_bundle"] is not None:
                raise ContractError("export does not accept a bundle")
            body = self.storage.export_recovery(scope)
            for artifact in body["artifacts"]:
                if artifact["kind"] == "archive":
                    secret = self._key(body["scope"])
                    if secret is None:
                        raise ContractError("archive key unavailable for portable export")
                    archived = json.loads(
                        decrypt_archive(bytes.fromhex(artifact["content"]), secret)
                    )
                    if archived["scope"] != body["scope"] or archived["task"] != artifact["task"]:
                        raise ContractError("archive export lineage mismatch")
                    artifact.update(
                        kind=archived["kind"],
                        content=archived["content"],
                        digest=archived["digest"],
                    )
            result.update(
                status="exported",
                encrypted_bundle=encode_archive(
                    parse_contract("RecoveryBundle", body).payload(), key
                ).decode("ascii"),
            )
            return result
        if not request["encrypted_bundle"]:
            raise ContractError("encrypted bundle required")
        body = parse_contract(
            "RecoveryBundle",
            json.loads(decrypt_archive(request["encrypted_bundle"].encode("ascii"), key)),
        ).payload()
        result["restored_count"] = self.storage.import_recovery(scope, body, self.clock())
        result["status"] = "imported"
        return result
