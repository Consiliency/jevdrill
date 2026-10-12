"""Local transactional storage with scoped retries and deletion-safe recovery."""

import hashlib
import json
import os
import sqlite3
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from time import monotonic, time
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from .contracts import ContractError, canonical_digest, parse_contract


class SQLiteStorage:
    def __init__(self, path: Path, deadline: float | None = None) -> None:
        self.path = path
        self.deadline = deadline
        self._initialize()
        self._initialize_discovery()
        self._initialize_learning()
        self._initialize_experiments()
        self.recover_artifacts()

    def _initialize_experiments(self) -> None:
        with self._connect(True) as connection:
            for statement in (
                "CREATE TABLE IF NOT EXISTS experiment_proposals (scope TEXT, identity TEXT, dedup TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(scope,identity), UNIQUE(scope,dedup))",
                "CREATE TABLE IF NOT EXISTS experiment_occurrences (scope TEXT, identity TEXT, task TEXT, PRIMARY KEY(scope,identity,task))",
                "CREATE TABLE IF NOT EXISTS experiment_requests (scope TEXT, producer TEXT, key TEXT, digest TEXT NOT NULL, identity TEXT, PRIMARY KEY(scope,producer,key))",
                "CREATE TABLE IF NOT EXISTS experiment_executions (scope TEXT, identity TEXT, task TEXT, harness TEXT, day INTEGER, reserved INTEGER, status TEXT, payload TEXT, PRIMARY KEY(scope,identity))",
                "CREATE TABLE IF NOT EXISTS experiment_clock (scope TEXT PRIMARY KEY, observed_ms INTEGER NOT NULL)",
                "CREATE TABLE IF NOT EXISTS experiment_recovery_blocks (scope TEXT PRIMARY KEY)",
                "CREATE TABLE IF NOT EXISTS policy_records (scope TEXT, revision TEXT, task_group TEXT, status TEXT, payload TEXT, PRIMARY KEY(scope,revision))",
                "CREATE TABLE IF NOT EXISTS policy_exposures (scope TEXT, dataset TEXT, related_group TEXT, revision TEXT, PRIMARY KEY(scope,dataset,related_group))",
                "CREATE TABLE IF NOT EXISTS policy_uses (scope TEXT, revision TEXT, request_id TEXT, PRIMARY KEY(scope,revision,request_id))",
                "CREATE TABLE IF NOT EXISTS policy_studies (scope TEXT, revision TEXT, payload TEXT, PRIMARY KEY(scope,revision))",
                "CREATE TABLE IF NOT EXISTS experiment_lineage (scope TEXT, identity TEXT, payload TEXT NOT NULL, PRIMARY KEY(scope,identity))",
                "CREATE TABLE IF NOT EXISTS policy_dependencies (scope TEXT, revision TEXT, source_scope TEXT, task TEXT, objective TEXT, PRIMARY KEY(scope,revision,source_scope,task,objective))",
                "CREATE TABLE IF NOT EXISTS policy_support (scope TEXT, revision TEXT, payload TEXT NOT NULL, PRIMARY KEY(scope,revision))",
            ):
                connection.execute(statement)

    def _experiment_source(
        self, connection: sqlite3.Connection, pair: str, task: str
    ) -> dict[str, Any]:
        live = connection.execute(
            "SELECT deleted FROM tasks WHERE scope=? AND task=?", (pair, task)
        ).fetchone()
        policy = connection.execute(
            "SELECT enabled FROM task_learning_policy WHERE scope=? AND task=?", (pair, task)
        ).fetchone()
        if not live or live[0] or (policy is not None and not policy[0]):
            raise ContractError("experiment_context_deleted_or_opted_out")
        rows = connection.execute(
            "SELECT scope,bundle FROM decisions_v1 WHERE task_scope=? AND task=? ORDER BY decision_id",
            (pair, task),
        ).fetchall()
        if not rows:
            raise ContractError("experiment_authoritative_task_required")
        decisions = []
        for encoded, payload in rows:
            bundle = json.loads(payload)
            linkage = bundle["decision"]["details"].get("discovery_ref")
            if linkage is not None:
                self._check_discovery_link(connection, json.loads(encoded), linkage)
            decisions.append(canonical_digest(bundle))
        events = [
            row[0]
            for row in connection.execute(
                "SELECT digest FROM events_v1 WHERE task_scope=? AND task=? ORDER BY event_id",
                (pair, task),
            )
        ]
        return {"decisions": decisions, "events": events}

    def experiment_context_current(self, scope: Mapping[str, str], identity: str) -> bool:
        pair = self._task_scope(scope)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT p.payload,l.payload FROM experiment_proposals p JOIN experiment_lineage l ON p.scope=l.scope AND p.identity=l.identity WHERE p.scope=? AND p.identity=?",
                (pair, identity),
            ).fetchone()
            if row is None:
                return False
            try:
                source = self._experiment_source(
                    connection, pair, json.loads(row[0])["experiment"]["task_id"]
                )
            except ContractError:
                return False
            return bool(self._encode(source) == row[1])

    def freeze_policy_study(self, scope: Mapping[str, str], protocol: Mapping[str, Any]) -> None:
        """Trusted study registration must precede admission of every comparison."""
        pair = self._task_scope(scope)
        revision = protocol["definition"]["policy_revision"]
        with self._connect(True) as connection:
            prior = connection.execute(
                "SELECT payload FROM policy_studies WHERE scope=? AND revision=?", (pair, revision)
            ).fetchone()
            if prior:
                if prior[0] != self._encode(protocol):
                    raise ContractError("policy_study_already_frozen")
                return
            if any(
                not self._admit(connection, pair, case["task_id"])
                for case in protocol["definition"]["cases"]
            ):
                raise ContractError("policy_task_deleted")
            for case in protocol["definition"]["cases"]:
                self._experiment_source(connection, pair, case["task_id"])
            if any(
                connection.execute(
                    "SELECT 1 FROM experiment_executions WHERE scope=? AND identity=?",
                    (pair, binding["comparison_experiment_id"]),
                ).fetchone()
                for binding in protocol["comparisons"].values()
            ):
                raise ContractError("policy_study_must_precede_execution")
            connection.execute(
                "INSERT INTO policy_studies VALUES (?,?,?)",
                (pair, revision, self._encode(protocol)),
            )

    def policy_study(self, scope: Mapping[str, str], revision: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM policy_studies WHERE scope=? AND revision=?",
                (self._task_scope(scope), revision),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def policy_records(
        self, scope: Mapping[str, str], task_group: str | None = None
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM policy_records WHERE scope=? AND (? IS NULL OR task_group=?) ORDER BY revision",
                (self._task_scope(scope), task_group, task_group),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def store_policy(
        self,
        scope: Mapping[str, str],
        following: Mapping[str, Any],
        previous: Mapping[str, Any] | None,
    ) -> bool:
        pair = self._task_scope(scope)
        definition = following["definition"]
        revision = definition["policy_revision"]
        with self._connect(True) as connection:
            current = connection.execute(
                "SELECT payload FROM policy_records WHERE scope=? AND revision=?", (pair, revision)
            ).fetchone()
            if (current[0] if current else None) != (
                self._encode(previous) if previous is not None else None
            ):
                return False
            if following["policy_status"] not in {"suspended", "stale"} and any(
                not self._admit(connection, pair, case["task_id"]) for case in definition["cases"]
            ):
                raise ContractError("policy_task_deleted")
            if following["policy_status"] not in {"suspended", "stale"}:
                support = {
                    case["task_id"]: self._experiment_source(connection, pair, case["task_id"])
                    for case in definition["cases"]
                }
                frozen = connection.execute(
                    "SELECT payload FROM policy_support WHERE scope=? AND revision=?",
                    (pair, revision),
                ).fetchone()
                if frozen is not None and frozen[0] != self._encode(support):
                    raise ContractError("policy_support_changed")
                connection.execute(
                    "INSERT OR IGNORE INTO policy_support VALUES (?,?,?)",
                    (pair, revision, self._encode(support)),
                )
            if (
                following["policy_status"] == "exposed"
                and previous
                and previous["policy_status"] == "registered"
            ):
                dataset = definition["calibration"]["dataset_revision"]
                groups = [case["related_group"] for case in definition["cases"]]
                if any(
                    connection.execute(
                        "SELECT 1 FROM policy_exposures WHERE scope=? AND dataset=? AND related_group=?",
                        (pair, dataset, group),
                    ).fetchone()
                    for group in groups
                ):
                    raise ContractError("policy_holdout_already_exposed")
                connection.executemany(
                    "INSERT INTO policy_exposures VALUES (?,?,?,?)",
                    [(pair, dataset, group, revision) for group in groups],
                )
            if following["policy_status"] == "active" and (
                previous is None or previous["policy_status"] != "active"
            ):
                active = connection.execute(
                    "SELECT revision,payload FROM policy_records WHERE scope=? AND task_group=? AND status='active'",
                    (pair, definition["task_group"]),
                ).fetchone()
                if (active[0] if active else None) != following["previous_policy_revision"]:
                    return False
                if active:
                    prior = json.loads(active[1])
                    prior["policy_status"] = "evaluated"
                    connection.execute(
                        "UPDATE policy_records SET status='evaluated',payload=? WHERE scope=? AND revision=?",
                        (self._encode(prior), pair, active[0]),
                    )
            connection.execute(
                "INSERT INTO policy_records VALUES (?,?,?,?,?) ON CONFLICT(scope,revision) DO UPDATE SET status=excluded.status,payload=excluded.payload",
                (
                    pair,
                    revision,
                    definition["task_group"],
                    following["policy_status"],
                    self._encode(following),
                ),
            )
            for case in definition["cases"]:
                rows = connection.execute(
                    "SELECT bundle FROM decisions_v1 WHERE task_scope=? AND task=?",
                    (pair, case["task_id"]),
                ).fetchall()
                objectives = {
                    (json.loads(row[0])["decision"]["details"].get("discovery_ref") or {}).get(
                        "work_objective_id", ""
                    )
                    for row in rows
                }
                connection.executemany(
                    "INSERT OR IGNORE INTO policy_dependencies VALUES (?,?,?,?,?)",
                    [
                        (pair, revision, pair, case["task_id"], objective)
                        for objective in objectives | {""}
                    ],
                )
        return True

    def use_policy(
        self, scope: Mapping[str, str], record: Mapping[str, Any], request_id: str, observed_at: str
    ) -> bool:
        pair, revision = self._task_scope(scope), record["definition"]["policy_revision"]
        with self._connect(True) as connection:
            current = connection.execute(
                "SELECT payload FROM policy_records WHERE scope=? AND revision=? AND status='active'",
                (pair, revision),
            ).fetchone()
            if current is None or current[0] != self._encode(record):
                return False
            frozen = connection.execute(
                "SELECT payload FROM policy_support WHERE scope=? AND revision=?", (pair, revision)
            ).fetchone()
            try:
                support = {
                    case["task_id"]: self._experiment_source(connection, pair, case["task_id"])
                    for case in record["definition"]["cases"]
                }
            except ContractError:
                return False
            if frozen is None or frozen[0] != self._encode(support):
                return False
            if connection.execute(
                "SELECT 1 FROM policy_uses WHERE scope=? AND revision=? AND request_id=?",
                (pair, revision, request_id),
            ).fetchone():
                return True
            if record["used_routes"] >= record["authorization"]["max_routes"]:
                return False
            following = dict(record) | {
                "used_routes": record["used_routes"] + 1,
                "observed_at": observed_at,
            }
            connection.execute(
                "INSERT INTO policy_uses VALUES (?,?,?)", (pair, revision, request_id)
            )
            connection.execute(
                "UPDATE policy_records SET payload=? WHERE scope=? AND revision=?",
                (self._encode(following), pair, revision),
            )
        return True

    def experiment_proposal(self, scope: Mapping[str, str], identity: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM experiment_proposals WHERE scope=? AND identity=?",
                (self._task_scope(scope), identity),
            ).fetchone()
        return json.loads(row[0])["experiment"] if row else None

    def experiment_execution(
        self, scope: Mapping[str, str], identity: str
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM experiment_executions WHERE scope=? AND identity=?",
                (self._task_scope(scope), identity),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def experiment_recovery_blocked(self, scope: Mapping[str, str]) -> bool:
        with self._connect() as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM experiment_recovery_blocks WHERE scope=?",
                    (self._task_scope(scope),),
                ).fetchone()
                is not None
            )

    def admit_experiment(
        self,
        scope: Mapping[str, str],
        job: Mapping[str, Any],
        daily_limit: int,
        total_limit: int,
        concurrency: int,
    ) -> dict[str, Any]:
        pair = self._task_scope(scope)
        record, experiment = job["record"], job["experiment"]
        identity, now = record["comparison_experiment_id"], record["admitted_at_ms"]
        day = now // 86_400_000
        with self._connect(True) as connection:
            previous = connection.execute(
                "SELECT payload FROM experiment_executions WHERE scope=? AND identity=?",
                (pair, identity),
            ).fetchone()
            if previous:
                return dict(json.loads(previous[0]))
            if connection.execute(
                "SELECT 1 FROM experiment_recovery_blocks WHERE scope=?", (pair,)
            ).fetchone():
                raise ContractError("experiment_recovery_authority_unreconciled")
            clock = connection.execute(
                "SELECT observed_ms FROM experiment_clock WHERE scope=?", (pair,)
            ).fetchone()
            if clock and now < clock[0]:
                raise ContractError("experiment_clock_regression")
            current = connection.execute(
                "SELECT payload FROM experiment_proposals WHERE scope=? AND identity=?",
                (pair, identity),
            ).fetchone()
            if (
                not current
                or canonical_digest(json.loads(current[0])["experiment"])
                != record["experiment_digest"]
            ):
                raise ContractError("experiment_changed_before_admission")
            if not self._admit(connection, pair, experiment["task_id"]):
                raise ContractError("task_deleted")
            lineage = connection.execute(
                "SELECT payload FROM experiment_lineage WHERE scope=? AND identity=?",
                (pair, identity),
            ).fetchone()
            if lineage is None or lineage[0] != self._encode(
                self._experiment_source(connection, pair, experiment["task_id"])
            ):
                raise ContractError("experiment_context_changed")
            active = ("accepted", "running", "cancel_pending")
            count = connection.execute(
                "SELECT count(*) FROM experiment_executions WHERE (scope=? OR harness=?) AND status IN (?,?,?)",
                (pair, record["harness_id"], *active),
            ).fetchone()[0]
            if count >= concurrency:
                raise ContractError("experiment_concurrency_exhausted")
            total, daily = connection.execute(
                "SELECT coalesce(sum(reserved),0),coalesce(sum(CASE WHEN day=? THEN reserved ELSE 0 END),0) FROM experiment_executions WHERE scope=?",
                (day, pair),
            ).fetchone()
            if (
                total + record["reserved_microusd"] > total_limit
                or daily + record["reserved_microusd"] > daily_limit
            ):
                raise ContractError("experiment_budget_exhausted")
            connection.execute(
                "INSERT INTO experiment_executions VALUES (?,?,?,?,?,?,?,?)",
                (
                    pair,
                    identity,
                    experiment["task_id"],
                    record["harness_id"],
                    day,
                    record["reserved_microusd"],
                    "accepted",
                    self._encode(job),
                ),
            )
            connection.execute(
                "INSERT INTO experiment_clock VALUES (?,?) ON CONFLICT(scope) DO UPDATE SET observed_ms=excluded.observed_ms",
                (pair, now),
            )
        return dict(job)

    def update_experiment_execution(
        self,
        scope: Mapping[str, str],
        identity: str,
        previous: Mapping[str, Any],
        following: Mapping[str, Any],
    ) -> bool:
        with self._connect(True) as connection:
            changed = connection.execute(
                "UPDATE experiment_executions SET status=?,payload=? WHERE scope=? AND identity=? AND payload=?",
                (
                    following["record"]["execution_status"],
                    self._encode(following),
                    self._task_scope(scope),
                    identity,
                    self._encode(previous),
                ),
            )
        return changed.rowcount == 1

    @staticmethod
    def _cancel_experiment(
        connection: sqlite3.Connection,
        pair: str,
        identity: str,
        deleted: bool = False,
    ) -> None:
        row = connection.execute(
            "SELECT payload FROM experiment_executions WHERE scope=? AND identity=?",
            (pair, identity),
        ).fetchone()
        if row is None:
            return
        job = json.loads(row[0])
        if job["record"]["execution_status"] != "canceled":
            job["record"]["execution_status"] = "cancel_pending"
        if deleted:
            job["experiment"] = None
            job["record"]["receipt"] = None
            job["receipts"] = []
        connection.execute(
            "UPDATE experiment_executions SET status=?,payload=? WHERE scope=? AND identity=?",
            (job["record"]["execution_status"], SQLiteStorage._encode(job), pair, identity),
        )

    def cancel_experiment_execution(self, scope: Mapping[str, str], identity: str) -> None:
        with self._connect(True) as connection:
            self._cancel_experiment(connection, self._task_scope(scope), identity)

    def experiment_queue(self, request: Mapping[str, Any], digest: str) -> dict[str, Any]:
        pair = self._task_scope(request["scope"])
        producer, key = request["scope"]["producer"], request["idempotency_key"]
        with self._connect(True) as connection:
            previous = connection.execute(
                "SELECT digest FROM experiment_requests WHERE scope=? AND producer=? AND key=?",
                (pair, producer, key),
            ).fetchone()
            if previous and previous[0] != digest:
                raise ContractError("experiment idempotency conflict")
            identity = request["comparison_experiment_id"]
            status = "duplicate" if previous else "listed"
            if not previous and request["action"] == "propose":
                proposal = request["proposal"]
                experiment = proposal["experiment"]
                task = experiment["task_id"]
                source = self._experiment_source(connection, pair, task)
                if not self._admit(connection, pair, task):
                    raise ContractError("task deleted")
                # Only identities differ across equivalent occurrences; preserve every semantic input.
                semantic = dict(experiment)
                for field in ("comparison_experiment_id", "task_id"):
                    semantic.pop(field)
                plans = []
                plan_keys = {}
                for index, plan in enumerate(experiment["candidate_plans"]):
                    normalized = dict(plan)
                    plan_keys[normalized.pop("execution_plan_id")] = str(index)
                    for field in ("optional_guidance", "required_guidance"):
                        normalized[field] = [
                            {key: value for key, value in row.items() if key != "task_id"}
                            for row in normalized[field]
                        ]
                    plans.append(normalized)
                semantic["candidate_plans"] = plans
                semantic["assignment_probabilities"] = {
                    plan_keys[key]: value
                    for key, value in experiment["assignment_probabilities"].items()
                }
                dedup = canonical_digest(dict(proposal) | {"experiment": semantic})
                existing = connection.execute(
                    "SELECT identity,payload FROM experiment_proposals WHERE scope=? AND dedup=?",
                    (pair, dedup),
                ).fetchone()
                identity = experiment["comparison_experiment_id"]
                collision = connection.execute(
                    "SELECT dedup FROM experiment_proposals WHERE scope=? AND identity=?",
                    (pair, identity),
                ).fetchone()
                if collision and collision[0] != dedup:
                    raise ContractError("immutable experiment identity conflict")
                if existing:
                    identity = existing[0]
                    if json.loads(existing[1])["experiment"]["experiment_state"] != "proposed":
                        raise ContractError("experiment is terminal")
                    status = "duplicate"
                else:
                    connection.execute(
                        "INSERT INTO experiment_proposals VALUES (?,?,?,?)",
                        (pair, identity, dedup, self._encode(proposal)),
                    )
                    connection.execute(
                        "INSERT INTO experiment_lineage VALUES (?,?,?)",
                        (pair, identity, self._encode(source)),
                    )
                    status = "recorded"
                connection.execute(
                    "INSERT OR IGNORE INTO experiment_occurrences VALUES (?,?,?)",
                    (pair, identity, task),
                )
            elif not previous and request["action"] == "cancel":
                self._cancel_experiment(connection, pair, identity)
                row = connection.execute(
                    "SELECT payload FROM experiment_proposals WHERE scope=? AND identity=?",
                    (pair, identity),
                ).fetchone()
                status = "not_found"
                if row:
                    proposal = json.loads(row[0])
                    proposal["experiment"]["experiment_state"] = "canceled"
                    connection.execute(
                        "UPDATE experiment_proposals SET payload=? WHERE scope=? AND identity=?",
                        (self._encode(proposal), pair, identity),
                    )
                    status = "canceled"
            if not previous:
                connection.execute(
                    "INSERT INTO experiment_requests VALUES (?,?,?,?,?)",
                    (pair, producer, key, digest, identity),
                )
            rows = connection.execute(
                "SELECT p.payload,count(o.task) FROM experiment_proposals p "
                "JOIN experiment_occurrences o ON p.scope=o.scope AND p.identity=o.identity "
                "WHERE p.scope=? GROUP BY p.identity",
                (pair,),
            ).fetchall()
        return {
            "status": status,
            "experiments": [
                {"proposal": json.loads(row[0]), "occurrence_count": row[1]} for row in rows
            ],
        }

    def _remaining(self) -> float:
        remaining = 1.0 if self.deadline is None else min(1.0, self.deadline - monotonic())
        if remaining <= 0:
            raise TimeoutError("storage deadline expired")
        return remaining

    @contextmanager
    def _connect(self, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=self._remaining(), isolation_level=None)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA secure_delete = ON")
            connection.set_progress_handler(
                lambda: int(self.deadline is not None and monotonic() >= self.deadline), 100
            )
            if write:
                connection.execute("BEGIN IMMEDIATE")
            yield connection
            if write:
                self._remaining()
                connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
        with self._connect(True) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > 3:
                raise ContractError("unsupported storage version")
            if version >= 1:
                return
            statements = (
                "CREATE TABLE tasks (scope TEXT, task TEXT, deleted INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(scope,task))",
                "CREATE TABLE decisions_v1 (scope TEXT, task_scope TEXT NOT NULL, task TEXT NOT NULL, decision_id TEXT, bundle TEXT NOT NULL, PRIMARY KEY(task_scope,decision_id), FOREIGN KEY(task_scope,task) REFERENCES tasks(scope,task))",
                "CREATE TABLE retries (scope TEXT, key TEXT, digest TEXT NOT NULL, task_scope TEXT NOT NULL, task TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(scope,key), FOREIGN KEY(task_scope,task) REFERENCES tasks(scope,task))",
                "CREATE TABLE events_v1 (scope TEXT, task_scope TEXT NOT NULL, task TEXT NOT NULL, event_id TEXT, run_id TEXT NOT NULL, supersedes TEXT, digest TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(task_scope,event_id), FOREIGN KEY(task_scope,task) REFERENCES tasks(scope,task))",
                "CREATE TABLE artifacts (scope TEXT, task TEXT, artifact_id TEXT, digest TEXT NOT NULL, kind TEXT NOT NULL, retention TEXT NOT NULL, encryption TEXT NOT NULL, pending BLOB, PRIMARY KEY(scope,artifact_id), FOREIGN KEY(scope,task) REFERENCES tasks(scope,task))",
                "CREATE TABLE notices (scope TEXT, task TEXT, kind TEXT, PRIMARY KEY(scope,task,kind))",
                "CREATE TABLE policy_validation (scope TEXT PRIMARY KEY, stale INTEGER NOT NULL)",
            )
            for statement in statements:
                connection.execute(statement)
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if "tombstones" in tables:
                for scope, task in connection.execute(
                    "SELECT scope,task_id FROM tombstones"
                ).fetchall():
                    pair = self._task_scope(json.loads(scope))
                    connection.execute("INSERT OR REPLACE INTO tasks VALUES (?,?,1)", (pair, task))
            if "decisions" in tables:
                for scope, key, digest, identity, bundle in connection.execute(
                    "SELECT * FROM decisions"
                ).fetchall():
                    value = json.loads(bundle)
                    pair, task = self._task_scope(json.loads(scope)), value["task_id"]
                    if self._admit(connection, pair, task):
                        connection.execute(
                            "INSERT INTO decisions_v1 VALUES (?,?,?,?,?)",
                            (scope, pair, task, identity, bundle),
                        )
                        response = self._encode({"status": "committed", "bundle": value})
                        connection.execute(
                            "INSERT INTO retries VALUES (?,?,?,?,?,?)",
                            (scope, key, digest, pair, task, response),
                        )
                connection.execute("DROP TABLE decisions")
            if "events" in tables:
                for scope, identity, digest, payload in connection.execute(
                    "SELECT * FROM events"
                ).fetchall():
                    value = json.loads(payload)
                    pair, task = self._task_scope(json.loads(scope)), value["task_id"]
                    if self._admit(connection, pair, task):
                        connection.execute(
                            "INSERT INTO events_v1 VALUES (?,?,?,?,?,?,?,?)",
                            (
                                scope,
                                pair,
                                task,
                                identity,
                                value.get("execution_run_id", ""),
                                value.get("supersedes_event_id"),
                                digest,
                                payload,
                            ),
                        )
                connection.execute("DROP TABLE events")
            for table in ("tombstones", "deleted_tasks"):
                if table in tables:
                    connection.execute(f"DROP TABLE {table}")
            connection.execute("PRAGMA user_version = 1")

    @staticmethod
    def _encode(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _initialize_discovery(self) -> None:
        with self._connect(True) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS discovery_objectives (scope TEXT, objective TEXT, deleted INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(scope,objective))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS discoveries (scope TEXT, objective_scope TEXT, objective TEXT, request_key TEXT, request_digest TEXT, discovery_id TEXT UNIQUE, allowance TEXT, seed TEXT, result TEXT, trace TEXT, PRIMARY KEY(scope,request_key), FOREIGN KEY(objective_scope,objective) REFERENCES discovery_objectives(scope,objective))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS discovery_rounds (discovery_id TEXT, round_number INTEGER, question TEXT, budget_before TEXT, PRIMARY KEY(discovery_id,round_number), FOREIGN KEY(discovery_id) REFERENCES discoveries(discovery_id))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS discovery_calls (discovery_id TEXT, sequence INTEGER, round_number INTEGER, option_id TEXT, reservation TEXT, observation TEXT, PRIMARY KEY(discovery_id,sequence), FOREIGN KEY(discovery_id) REFERENCES discoveries(discovery_id))"
            )
            if connection.execute("PRAGMA user_version").fetchone()[0] < 2:
                connection.execute("PRAGMA user_version = 2")

    def _initialize_learning(self) -> None:
        with self._connect(True) as connection:
            for statement in (
                "CREATE TABLE IF NOT EXISTS learning_context (scope TEXT, task TEXT, decision_id TEXT, payload TEXT NOT NULL, PRIMARY KEY(scope,decision_id))",
                "CREATE TABLE IF NOT EXISTS learning_evidence (scope TEXT, revision TEXT, created REAL, valid INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(scope,revision))",
                "CREATE TABLE IF NOT EXISTS analysis_clock (scope TEXT PRIMARY KEY, first_seen REAL NOT NULL)",
                "CREATE TABLE IF NOT EXISTS task_learning_policy (scope TEXT, task TEXT, enabled INTEGER NOT NULL, PRIMARY KEY(scope,task))",
                "CREATE TABLE IF NOT EXISTS objective_history (scope TEXT, digest TEXT, payload TEXT NOT NULL, PRIMARY KEY(scope,digest))",
                "CREATE TABLE IF NOT EXISTS learning_dependencies (scope TEXT, revision TEXT, source_scope TEXT, task TEXT, objective TEXT, PRIMARY KEY(scope,revision,source_scope,task))",
                "CREATE TABLE IF NOT EXISTS recovered_discovery_metadata (discovery_id TEXT PRIMARY KEY, domains TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS maintenance_control (scope TEXT PRIMARY KEY, action TEXT NOT NULL, last_clock REAL NOT NULL, cursor TEXT)",
                "CREATE TABLE IF NOT EXISTS artifact_lifecycle (scope TEXT, artifact_id TEXT, created REAL NOT NULL, prompted REAL, archived REAL, source_id TEXT, PRIMARY KEY(scope,artifact_id))",
                "CREATE TABLE IF NOT EXISTS discovery_content_artifacts (scope TEXT, discovery_id TEXT, artifact_id TEXT, PRIMARY KEY(scope,artifact_id))",
                "CREATE TABLE IF NOT EXISTS lifecycle_notices (scope TEXT, task TEXT, notice_id TEXT, payload TEXT NOT NULL, PRIMARY KEY(scope,notice_id))",
            ):
                connection.execute(statement)
            connection.execute(
                "INSERT OR IGNORE INTO artifact_lifecycle(scope,artifact_id,created) SELECT scope,artifact_id,? FROM artifacts",
                (time(),),
            )
            connection.execute("PRAGMA user_version = 3")

    @staticmethod
    def _invalidate_learning(
        connection: sqlite3.Connection,
        pair: str,
        task: str | None = None,
        objective: str | None = None,
        purge: bool = False,
    ) -> None:
        selector = "SELECT scope,revision FROM learning_dependencies WHERE source_scope=? AND (? IS NULL OR task=?) AND (? IS NULL OR objective=?)"
        parameters = (pair, task, task, objective, objective)
        operation = (
            "DELETE FROM learning_evidence" if purge else "UPDATE learning_evidence SET valid=0"
        )
        connection.execute(operation + " WHERE (scope,revision) IN (" + selector + ")", parameters)
        connection.execute(
            "INSERT INTO policy_validation VALUES (?,1) ON CONFLICT(scope) DO UPDATE SET stale=1",
            (pair,),
        )
        connection.execute(
            "UPDATE policy_validation SET stale=1 WHERE scope IN (SELECT scope FROM learning_dependencies WHERE source_scope=?)",
            (pair,),
        )
        affected = connection.execute(
            "SELECT DISTINCT p.scope,p.revision,p.payload FROM policy_records p JOIN policy_dependencies d ON p.scope=d.scope AND p.revision=d.revision WHERE d.source_scope=? AND (? IS NULL OR d.task=?) AND (? IS NULL OR d.objective=?)",
            parameters,
        ).fetchall()
        for policy_scope, revision, payload in affected:
            record = json.loads(payload)
            record.update(
                policy_status="stale",
                reasons=["supporting_data_deleted" if purge else "supporting_data_changed"],
                evaluation=None,
                assessment=None,
                objective_improvement_lower_bound=None,
            )
            connection.execute(
                "UPDATE policy_records SET status='stale',payload=? WHERE scope=? AND revision=?",
                (SQLiteStorage._encode(record), policy_scope, revision),
            )

    def restrict_learning(self, scope: Mapping[str, str], task: str, enabled: bool) -> None:
        pair = self._task_scope(scope)
        with self._connect(True) as connection:
            if not self._admit(connection, pair, task):
                raise ContractError("task deleted")
            connection.execute(
                "INSERT INTO task_learning_policy VALUES (?,?,?) ON CONFLICT(scope,task) DO UPDATE SET enabled=min(enabled,excluded.enabled)",
                (pair, task, int(enabled)),
            )
            if not enabled:
                self._invalidate_learning(connection, pair, task, purge=True)

    def record_learning_context(self, scope: Mapping[str, str], context: Mapping[str, Any]) -> None:
        context = parse_contract("LearningContext", context).payload()
        pair = self._task_scope(scope)
        with self._connect(True) as connection:
            row = connection.execute(
                "SELECT scope,task,bundle FROM decisions_v1 WHERE task_scope=? AND decision_id=?",
                (pair, context["routing_decision_id"]),
            ).fetchone()
            if (
                row is None
                or row[0] != self._scope(dict(scope, operation="route"))
                or row[1] != context["task_id"]
            ):
                raise ContractError("learning requires an existing scoped decision")
            decision = json.loads(row[2])["decision"]
            if decision["details"].get("discovery_ref") != context["discovery_ref"]:
                raise ContractError("learning discovery lineage mismatch")
            if context["discovery_ref"] is not None:
                self._check_discovery_link(connection, scope, context["discovery_ref"])
            policy = connection.execute(
                "SELECT enabled FROM task_learning_policy WHERE scope=? AND task=?",
                (pair, context["task_id"]),
            ).fetchone()
            if policy is not None and not policy[0] and context["local_analysis_enabled"]:
                raise ContractError("task analysis opted out")
            existing = connection.execute(
                "SELECT payload FROM learning_context WHERE scope=? AND decision_id=?",
                (pair, context["routing_decision_id"]),
            ).fetchone()
            if existing:
                original = json.loads(existing[0])
                fixed = set(original) - {"local_analysis_enabled", "share_user_wide"}
                if any(original[key] != context[key] for key in fixed):
                    raise ContractError("learning context conflict")
                if original != context:
                    self._invalidate_learning(connection, pair, context["task_id"], purge=True)
            connection.execute(
                "INSERT INTO learning_context VALUES (?,?,?,?) ON CONFLICT(scope,decision_id) DO UPDATE SET payload=excluded.payload",
                (pair, context["task_id"], context["routing_decision_id"], self._encode(context)),
            )
            if not context["local_analysis_enabled"]:
                connection.execute(
                    "INSERT INTO task_learning_policy VALUES (?,?,0) ON CONFLICT(scope,task) DO UPDATE SET enabled=0",
                    (pair, context["task_id"]),
                )
                self._invalidate_learning(connection, pair, context["task_id"], purge=True)

    def learning_observations(
        self, scope: Mapping[str, str], include_user_wide: bool = False
    ) -> list[dict[str, Any]]:
        pair_requested = self._task_scope(scope)
        with self._connect() as connection:
            contexts = connection.execute(
                "SELECT c.scope,c.task,c.payload,d.scope,d.bundle FROM learning_context c "
                "JOIN decisions_v1 d ON c.scope=d.task_scope AND c.decision_id=d.decision_id "
                "JOIN tasks t ON c.scope=t.scope AND c.task=t.task "
                "LEFT JOIN task_learning_policy p ON c.scope=p.scope AND c.task=p.task "
                "WHERE t.deleted=0 AND coalesce(p.enabled,1)=1 ORDER BY c.scope,c.decision_id"
            ).fetchall()
            event_rows = connection.execute("SELECT task_scope,payload FROM events_v1").fetchall()
            deleted_objectives = set(
                connection.execute(
                    "SELECT scope,objective FROM discovery_objectives WHERE deleted=1"
                ).fetchall()
            )
            discoveries = {
                identity: (json.loads(result), json.loads(trace) if trace else None)
                for identity, result, trace in connection.execute(
                    "SELECT discovery_id,result,trace FROM discoveries WHERE result IS NOT NULL"
                )
            }
            recovered_domains = {
                identity: json.loads(domains)
                for identity, domains in connection.execute(
                    "SELECT discovery_id,domains FROM recovered_discovery_metadata"
                )
            }
        observations = []
        for pair, task, payload, decision_scope, bundle_json in contexts:
            context, bundle = json.loads(payload), json.loads(bundle_json)
            if not context["local_analysis_enabled"] or (
                pair != pair_requested and not (include_user_wide and context["share_user_wide"])
            ):
                continue
            linkage = context["discovery_ref"]
            if (
                linkage
                and (
                    self._objective_scope(json.loads(decision_scope)),
                    linkage["work_objective_id"],
                )
                in deleted_objectives
            ):
                continue
            decision = bundle["decision"]
            if decision["status"] != "ready":
                continue
            plan = decision["execution_plan"]
            events = [json.loads(e) for p, e in event_rows if p == pair]
            events = [
                e
                for e in events
                if e["task_id"] == task
                and e["routing_decision_id"] == context["routing_decision_id"]
            ]
            superseded = {e.get("supersedes_event_id") for e in events}
            events = [e for e in events if e["event_id"] not in superseded]
            for run in sorted({e["execution_run_id"] for e in events}) or [None]:
                current = sorted(
                    (e for e in events if e["execution_run_id"] == run),
                    key=lambda e: (e["source_sequence"], e["source_id"], e["event_id"]),
                )
                applied = [
                    e["payload"]["applied_plan_id"]
                    for e in current
                    if e["payload"]["kind"] == "lifecycle"
                    and e["payload"].get("applied_plan_id") is not None
                ]
                verified = bool(applied) and all(p == plan["execution_plan_id"] for p in applied)
                terminal = [
                    e
                    for e in current
                    if e["payload"].get("event_type") in {"completed", "failed", "canceled"}
                ]
                checks = [
                    e["payload"]["check_results"]
                    for e in current
                    if e["payload"]["kind"] == "evaluation"
                    and e["payload"]["evaluator_ref"] == context["evaluator_ref"]
                    and e["payload"]["rubric_revision"] == context["rubric_revision"]
                ]
                required = {
                    r["requirement_id"]
                    for r in decision["details"]["optimization_objective"][
                        "acceptance_requirements"
                    ]
                }
                evaluated = {key: value for check in checks for key, value in check.items()}
                accepted = (
                    all(evaluated[k] for k in required)
                    if required and required <= evaluated.keys()
                    else all(evaluated.values())
                    if evaluated and not required
                    else None
                )
                preference = [
                    e["payload"] for e in current if e["payload"]["kind"] == "host_choice"
                ]
                conditions = {
                    key: context[key]
                    for key in (
                        "task_family",
                        "task_group",
                        "environment_revision",
                        "isolation_revision",
                        "evaluator_ref",
                        "rubric_revision",
                    )
                }
                configuration = {
                    k: (
                        [{name: value for name, value in g.items() if name != "task_id"} for g in v]
                        if k in {"optional_guidance", "required_guidance"}
                        else v
                    )
                    for k, v in plan.items()
                    if k not in {"execution_plan_id", "predecessor_plan_id"}
                }
                conditions.update(
                    group_version="2",
                    origin="observational",
                    selected_configuration=canonical_digest(configuration),
                    applied_configuration=canonical_digest(configuration)
                    if verified
                    else "unknown",
                    applied_configuration_reason="reported_selected_plan"
                    if verified
                    else "different_plan"
                    if applied
                    else "not_reported",
                    policy_revision=decision["details"]["versions"]["policy_revision"],
                    discovery_status="linked" if linkage else "unbound",
                    observed_evaluators=canonical_digest(
                        list(
                            map(
                                list,
                                sorted(
                                    {
                                        (
                                            e["payload"]["evaluator_ref"],
                                            e["payload"]["rubric_revision"],
                                        )
                                        for e in current
                                        if e["payload"]["kind"] == "evaluation"
                                    }
                                ),
                            )
                        )
                    ),
                    selected_model=plan["model_id"],
                    selected_model_revision=plan["resolved_model_revision"] or "unknown",
                    selected_provider=plan["provider"],
                    selected_effort=canonical_digest(plan["native_effort"]),
                )
                if linkage:
                    discovery, trace = discoveries[linkage["discovery_id"]]
                    domains = (
                        sorted(
                            n["label"]
                            for n in trace["initial_state"]["nodes"]
                            if n["level"] == "domain" and n["label"] is not None
                        )
                        if trace
                        else recovered_domains[linkage["discovery_id"]]
                    )
                    conditions.update(
                        discovery_status=discovery["status"],
                        discovery_identity=canonical_digest(linkage),
                        discovery_domains=self._encode(domains),
                        discovery_choices=self._encode(discovery["details"]["guidance_refs"]),
                        discovery_revisions=canonical_digest(discovery["details"]["revisions"]),
                    )
                measurements = [
                    m
                    for e in current
                    if e["payload"]["kind"] in {"usage", "evaluation"}
                    for m in e["payload"]["measurements"]
                ]
                observations.append(
                    {
                        "conditions": conditions,
                        "observation_ref": canonical_digest(
                            [pair, task, context["routing_decision_id"], linkage, run, current]
                        ),
                        "status": terminal[-1]["payload"]["event_type"] if terminal else None,
                        "accepted": accepted,
                        "measurements": measurements,
                        "preference": (
                            "retained" if preference[-1]["selected_run_id"] == run else "declined"
                        )
                        if preference
                        else None,
                        "substituted": bool(applied)
                        and any(p != plan["execution_plan_id"] for p in applied),
                        "applied_unknown": not verified,
                        "source": {
                            "origin": "local" if pair == pair_requested else "user_wide_redacted",
                            "task_id": task if pair == pair_requested else None,
                            "routing_decision_id": context["routing_decision_id"]
                            if pair == pair_requested
                            else None,
                            "execution_run_id": run if pair == pair_requested else None,
                            "discovery_ref": linkage if pair == pair_requested else None,
                        },
                    }
                )
        return observations

    def save_evidence(
        self,
        scope: Mapping[str, str],
        evidence: Mapping[str, Any],
        now: float,
        observations_digest: str,
        include_user_wide: bool,
    ) -> None:
        evidence = parse_contract("AnalysisResult", evidence).payload()
        with self._connect(True) as connection:
            if (
                canonical_digest(self.learning_observations(scope, include_user_wide))
                != observations_digest
            ):
                raise ContractError("analysis sources changed; retry")
            for objective in evidence["objective_history"]:
                connection.execute(
                    "INSERT OR IGNORE INTO objective_history VALUES (?,?,?)",
                    (self._task_scope(scope), canonical_digest(objective), self._encode(objective)),
                )
            connection.execute(
                "INSERT OR IGNORE INTO learning_evidence VALUES (?,?,?,1,?)",
                (
                    self._task_scope(scope),
                    evidence["evidence_revision"],
                    now,
                    self._encode(evidence),
                ),
            )
            connection.execute(
                "INSERT INTO analysis_clock VALUES (?,?) ON CONFLICT(scope) DO UPDATE SET first_seen=excluded.first_seen",
                (self._task_scope(scope), now),
            )
            for pair, task, payload in connection.execute(
                "SELECT scope,task,payload FROM learning_context"
            ).fetchall():
                context = json.loads(payload)
                if context["local_analysis_enabled"] and (
                    pair == self._task_scope(scope)
                    or include_user_wide
                    and context["share_user_wide"]
                ):
                    linkage = context["discovery_ref"]
                    connection.execute(
                        "INSERT OR IGNORE INTO learning_dependencies VALUES (?,?,?,?,?)",
                        (
                            self._task_scope(scope),
                            evidence["evidence_revision"],
                            pair,
                            task,
                            linkage["work_objective_id"] if linkage else None,
                        ),
                    )

    def analysis_started(self, scope: Mapping[str, str], now: float) -> float:
        with self._connect(True) as connection:
            pair = self._task_scope(scope)
            connection.execute("INSERT OR IGNORE INTO analysis_clock VALUES (?,?)", (pair, now))
            return float(
                connection.execute(
                    "SELECT first_seen FROM analysis_clock WHERE scope=?", (pair,)
                ).fetchone()[0]
            )

    def latest_evidence(self, scope: Mapping[str, str]) -> tuple[float, dict[str, Any]] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT created,payload FROM learning_evidence WHERE scope=? AND valid=1 ORDER BY created DESC,revision DESC LIMIT 1",
                (self._task_scope(scope),),
            ).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def objective_versions(self, scope: Mapping[str, str]) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM objective_history WHERE scope=? ORDER BY digest",
                (self._task_scope(scope),),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def export_recovery(self, scope: Mapping[str, str]) -> dict[str, Any]:
        pair = self._task_scope(scope)
        with self._connect(True) as c:
            body: dict[str, Any] = {
                "schema_version": "1",
                "scope": pair,
                "tasks": {
                    task: bool(deleted)
                    for task, deleted in c.execute(
                        "SELECT task,deleted FROM tasks WHERE scope=?", (pair,)
                    )
                },
                "objectives": {
                    objective: bool(deleted)
                    for objective, deleted in c.execute(
                        "SELECT objective,deleted FROM discovery_objectives WHERE scope=?",
                        (self._objective_scope(scope),),
                    )
                },
                "learning_policy": {
                    task: bool(enabled)
                    for task, enabled in c.execute(
                        "SELECT task,enabled FROM task_learning_policy WHERE scope=?", (pair,)
                    )
                },
                "decisions": [
                    {"scope": json.loads(s), "bundle": json.loads(b)}
                    for s, b in c.execute(
                        "SELECT scope,bundle FROM decisions_v1 WHERE task_scope=?", (pair,)
                    )
                ],
                "events": [
                    {"scope": json.loads(s), "event": json.loads(e)}
                    for s, e in c.execute(
                        "SELECT scope,payload FROM events_v1 WHERE task_scope=?", (pair,)
                    )
                ],
                "contexts": [
                    json.loads(p)
                    for (p,) in c.execute(
                        "SELECT payload FROM learning_context WHERE scope=?", (pair,)
                    )
                ],
                "discoveries": [],
                "artifacts": [],
            }
            for s, result, trace in c.execute(
                "SELECT scope,result,trace FROM discoveries WHERE objective_scope=? AND result IS NOT NULL",
                (self._objective_scope(scope),),
            ):
                value = json.loads(result)
                if value["status"] not in {"selected_guidance", "no_optional_guidance"}:
                    continue
                details = value["details"]
                if trace:
                    domains = sorted(
                        n["label"]
                        for n in json.loads(trace)["initial_state"]["nodes"]
                        if n["level"] == "domain" and n["label"] is not None
                    )
                else:
                    domains = json.loads(
                        c.execute(
                            "SELECT domains FROM recovered_discovery_metadata WHERE discovery_id=?",
                            (details["discovery_id"],),
                        ).fetchone()[0]
                    )
                body["discoveries"].append(
                    {
                        "scope": dict(json.loads(s), operation="route"),
                        "discovery_ref": {
                            k: details[k]
                            for k in ("discovery_id", "work_objective_id", "trace_digest")
                        },
                        "status": value["status"],
                        "revisions": details["revisions"],
                        "guidance_refs": details["guidance_refs"],
                        "domains": domains,
                    }
                )
            for task, identity, kind, digest, pending in c.execute(
                "SELECT a.task,a.artifact_id,a.kind,a.digest,a.pending FROM artifacts a JOIN artifact_lifecycle l ON a.scope=l.scope AND a.artifact_id=l.artifact_id WHERE a.scope=? AND a.retention!='retired' AND a.kind IN ('raw_task','raw_output','context','archive') AND NOT EXISTS (SELECT 1 FROM discovery_content_artifacts d WHERE d.scope=a.scope AND (d.artifact_id=a.artifact_id OR d.artifact_id=l.source_id))",
                (pair,),
            ):
                content = (
                    pending
                    if pending is not None
                    else (self._artifact_directory(pair) / identity).read_bytes()
                )
                if hashlib.sha256(content).hexdigest() != digest:
                    raise ContractError("export artifact integrity failure")
                body["artifacts"].append(
                    {"task": task, "kind": kind, "content": content.hex(), "digest": digest}
                )
        return body

    def import_recovery(self, scope: Mapping[str, str], body: Mapping[str, Any], now: float) -> int:
        body = parse_contract("RecoveryBundle", body).payload()
        pair = self._task_scope(scope)
        if body["scope"] != pair:
            raise ContractError("portable bundle scope mismatch")
        for task in body["tasks"]:
            parse_contract(
                "DeleteRequest", {"schema_version": "1", "scope": dict(scope), "task_id": task}
            )
        for objective in body["objectives"]:
            parse_contract(
                "DiscoveryDeleteRequest",
                {
                    "schema_version": "1",
                    "scope": dict(scope, operation="discover"),
                    "work_objective_id": objective,
                },
            )
        if set(body["learning_policy"]) - set(body["tasks"]):
            raise ContractError("unknown learning policy task")
        decisions = {r["bundle"]["routing_decision_id"]: r for r in body["decisions"]}
        events = {r["event"]["event_id"]: r for r in body["events"]}
        discoveries = {r["discovery_ref"]["discovery_id"]: r for r in body["discoveries"]}
        if (
            len(decisions) != len(body["decisions"])
            or len(events) != len(body["events"])
            or len(discoveries) != len(body["discoveries"])
        ):
            raise ContractError("duplicate portable identity")
        for record in [*body["decisions"], *body["events"], *body["discoveries"]]:
            if self._task_scope(record["scope"]) != pair:
                raise ContractError("portable record scope mismatch")
        for record in body["decisions"]:
            bundle = record["bundle"]
            if (
                record["scope"]["operation"] != "route"
                or bundle["task_id"] not in body["tasks"]
                or bundle["decision"]["details"]["task_id"] != bundle["task_id"]
                or bundle["decision"]["details"]["routing_decision_id"]
                != bundle["routing_decision_id"]
            ):
                raise ContractError("portable decision lineage mismatch")
        for record in body["discoveries"]:
            if (
                record["scope"]["operation"] != "route"
                or record["discovery_ref"]["work_objective_id"] not in body["objectives"]
                or (record["status"] == "selected_guidance") != bool(record["guidance_refs"])
            ):
                raise ContractError("portable discovery lineage mismatch")
        for record in body["events"]:
            event = record["event"]
            if record["scope"]["operation"] != "report" or event["task_id"] not in body["tasks"]:
                raise ContractError("portable event lineage mismatch")
        for artifact in body["artifacts"]:
            if (
                artifact["task"] not in body["tasks"]
                or hashlib.sha256(bytes.fromhex(artifact["content"])).hexdigest()
                != artifact["digest"]
            ):
                raise ContractError("portable artifact integrity failure")
        with self._connect(True) as c:
            c.execute("INSERT OR IGNORE INTO experiment_recovery_blocks VALUES (?)", (pair,))
            for identity, record in decisions.items():
                existing = c.execute(
                    "SELECT scope,bundle FROM decisions_v1 WHERE task_scope=? AND decision_id=?",
                    (pair, identity),
                ).fetchone()
                if existing and (
                    existing[0] != self._scope(record["scope"])
                    or json.loads(existing[1]) != record["bundle"]
                ):
                    raise ContractError("import decision conflict")
            for identity, record in events.items():
                existing = c.execute(
                    "SELECT scope,payload FROM events_v1 WHERE task_scope=? AND event_id=?",
                    (pair, identity),
                ).fetchone()
                if existing and (
                    existing[0] != self._scope(record["scope"])
                    or json.loads(existing[1]) != record["event"]
                ):
                    raise ContractError("import event conflict")
                event = record["event"]
                if event["supersedes_event_id"]:
                    previous = event["supersedes_event_id"]
                    original = events.get(previous)
                    if original is None:
                        row = c.execute(
                            "SELECT scope,payload FROM events_v1 WHERE task_scope=? AND event_id=?",
                            (pair, previous),
                        ).fetchone()
                        original = (
                            {"scope": json.loads(row[0]), "event": json.loads(row[1])}
                            if row
                            else None
                        )
                    if (
                        original is None
                        or original["scope"] != record["scope"]
                        or any(
                            original["event"][k] != event[k]
                            for k in ("task_id", "execution_run_id", "routing_decision_id")
                        )
                    ):
                        raise ContractError("portable correction lineage mismatch")
                    if (
                        sum(r["event"]["supersedes_event_id"] == previous for r in events.values())
                        != 1
                    ):
                        raise ContractError("portable correction fork")
                    if c.execute(
                        "SELECT 1 FROM events_v1 WHERE task_scope=? AND supersedes=? AND event_id!=?",
                        (pair, previous, identity),
                    ).fetchone():
                        raise ContractError("import correction fork")
                    terminal = {"completed", "failed", "canceled"}
                    if (
                        original["event"]["payload"].get("event_type") in terminal
                        and event["payload"].get("event_type") not in terminal
                    ):
                        raise ContractError("portable terminal correction regression")
            for record in events.values():
                seen: set[str] = set()
                current = record["event"]
                while current["supersedes_event_id"] in events:
                    if current["event_id"] in seen:
                        raise ContractError("portable correction cycle")
                    seen.add(current["event_id"])
                    current = events[current["supersedes_event_id"]]["event"]
            for context in body["contexts"]:
                record = decisions.get(context["routing_decision_id"])
                if (
                    record is None
                    or record["bundle"]["task_id"] != context["task_id"]
                    or record["bundle"]["decision"]["details"].get("discovery_ref")
                    != context["discovery_ref"]
                ):
                    raise ContractError("portable context lineage mismatch")
                existing = c.execute(
                    "SELECT payload FROM learning_context WHERE scope=? AND decision_id=?",
                    (pair, context["routing_decision_id"]),
                ).fetchone()
                if existing and any(
                    json.loads(existing[0])[k] != v
                    for k, v in context.items()
                    if k not in {"local_analysis_enabled", "share_user_wide"}
                ):
                    raise ContractError("import context conflict")
            # Every validated record is ready before permanent deletion and opt-out merge.
            for task, deleted in body["tasks"].items():
                c.execute(
                    "INSERT INTO tasks VALUES (?,?,?) ON CONFLICT(scope,task) DO UPDATE SET deleted=max(deleted,excluded.deleted)",
                    (pair, task, int(deleted)),
                )
            for objective, deleted in body["objectives"].items():
                parent = self._objective_scope(scope)
                c.execute(
                    "INSERT INTO discovery_objectives VALUES (?,?,?) ON CONFLICT(scope,objective) DO UPDATE SET deleted=max(deleted,excluded.deleted)",
                    (parent, objective, int(deleted)),
                )
                if c.execute(
                    "SELECT deleted FROM discovery_objectives WHERE scope=? AND objective=?",
                    (parent, objective),
                ).fetchone()[0]:
                    ids = [
                        r[0]
                        for r in c.execute(
                            "SELECT discovery_id FROM discoveries WHERE objective_scope=? AND objective=?",
                            (parent, objective),
                        )
                    ]
                    for identity in ids:
                        c.execute("DELETE FROM discovery_calls WHERE discovery_id=?", (identity,))
                        c.execute("DELETE FROM discovery_rounds WHERE discovery_id=?", (identity,))
                        c.execute(
                            "UPDATE artifacts SET retention='retired' WHERE scope=? AND artifact_id IN (SELECT artifact_id FROM discovery_content_artifacts WHERE discovery_id=?)",
                            (pair, identity),
                        )
                    c.execute(
                        "UPDATE discoveries SET seed='{}',result=NULL,trace=NULL WHERE objective_scope=? AND objective=?",
                        (parent, objective),
                    )
                    self._invalidate_learning(c, pair, objective=objective, purge=True)
            for task, enabled in body["learning_policy"].items():
                c.execute(
                    "INSERT INTO task_learning_policy VALUES (?,?,?) ON CONFLICT(scope,task) DO UPDATE SET enabled=min(enabled,excluded.enabled)",
                    (pair, task, int(enabled)),
                )
            for task, deleted in c.execute(
                "SELECT task,deleted FROM tasks WHERE scope=?", (pair,)
            ).fetchall():
                if deleted:
                    for table in ("decisions_v1", "events_v1", "retries"):
                        c.execute(
                            f"DELETE FROM {table} WHERE task_scope=? AND task=?", (pair, task)
                        )
                    for table in (
                        "learning_context",
                        "lifecycle_notices",
                        "task_learning_policy",
                        "notices",
                    ):
                        c.execute(f"DELETE FROM {table} WHERE scope=? AND task=?", (pair, task))
                    self._invalidate_learning(c, pair, task, purge=True)
            for record in discoveries.values():
                linkage = record["discovery_ref"]
                objective = linkage["work_objective_id"]
                if c.execute(
                    "SELECT deleted FROM discovery_objectives WHERE scope=? AND objective=?",
                    (self._objective_scope(scope), objective),
                ).fetchone()[0]:
                    continue
                existing = self._discovery_row(
                    c, dict(record["scope"], operation="discover"), linkage["discovery_id"]
                )
                if existing:
                    if (
                        existing[4] is None
                        or json.loads(existing[4])["details"]["trace_digest"]
                        != linkage["trace_digest"]
                    ):
                        raise ContractError("import discovery conflict")
                    continue
                details = dict(
                    linkage,
                    guidance_refs=record["guidance_refs"],
                    revisions=record["revisions"],
                    required_guidance=[],
                    assembled_instructions=[],
                    alternatives=[],
                    uncertainty=["portable metadata only"],
                    termination_reason="portable_recovery",
                )
                result = {"status": record["status"], "details": details}
                c.execute(
                    "INSERT INTO discoveries VALUES (?,?,?,?,?,?,?,?,?,NULL)",
                    (
                        self._scope(dict(record["scope"], operation="discover")),
                        self._objective_scope(scope),
                        objective,
                        "recovery:" + linkage["discovery_id"],
                        canonical_digest(record),
                        linkage["discovery_id"],
                        "{}",
                        "{}",
                        self._encode(result),
                    ),
                )
                c.execute(
                    "INSERT INTO recovered_discovery_metadata VALUES (?,?)",
                    (linkage["discovery_id"], self._encode(record["domains"])),
                )
            for record in decisions.values():
                bundle = record["bundle"]
                task = bundle["task_id"]
                if not self._admit(c, pair, task):
                    continue
                linkage = bundle["decision"]["details"].get("discovery_ref")
                if linkage:
                    deleted = c.execute(
                        "SELECT deleted FROM discovery_objectives WHERE scope=? AND objective=?",
                        (self._objective_scope(scope), linkage["work_objective_id"]),
                    ).fetchone()
                    if not deleted or not deleted[0]:
                        self._check_discovery_link(c, record["scope"], linkage)
                c.execute(
                    "INSERT OR IGNORE INTO decisions_v1 VALUES (?,?,?,?,?)",
                    (
                        self._scope(record["scope"]),
                        pair,
                        task,
                        bundle["routing_decision_id"],
                        self._encode(bundle),
                    ),
                )
            for record in events.values():
                event = record["event"]
                task = event["task_id"]
                if self._admit(c, pair, task):
                    c.execute(
                        "INSERT OR IGNORE INTO events_v1 VALUES (?,?,?,?,?,?,?,?)",
                        (
                            self._scope(record["scope"]),
                            pair,
                            task,
                            event["event_id"],
                            event["execution_run_id"],
                            event["supersedes_event_id"],
                            canonical_digest(event),
                            self._encode(event),
                        ),
                    )
            for context in body["contexts"]:
                if not self._admit(c, pair, context["task_id"]):
                    continue
                linkage = context["discovery_ref"]
                if (
                    linkage
                    and c.execute(
                        "SELECT deleted FROM discovery_objectives WHERE scope=? AND objective=?",
                        (self._objective_scope(scope), linkage["work_objective_id"]),
                    ).fetchone()[0]
                ):
                    continue
                existing = c.execute(
                    "SELECT payload FROM learning_context WHERE scope=? AND decision_id=?",
                    (pair, context["routing_decision_id"]),
                ).fetchone()
                if existing:
                    prior = json.loads(existing[0])
                    context["local_analysis_enabled"] &= prior["local_analysis_enabled"]
                    context["share_user_wide"] &= prior["share_user_wide"]
                policy = c.execute(
                    "SELECT enabled FROM task_learning_policy WHERE scope=? AND task=?",
                    (pair, context["task_id"]),
                ).fetchone()
                if policy and not policy[0]:
                    context.update(local_analysis_enabled=False, share_user_wide=False)
                c.execute(
                    "INSERT OR REPLACE INTO learning_context VALUES (?,?,?,?)",
                    (
                        pair,
                        context["task_id"],
                        context["routing_decision_id"],
                        self._encode(context),
                    ),
                )
            restored = 0
            for artifact in body["artifacts"]:
                task = artifact["task"]
                if not self._admit(c, pair, task):
                    continue
                content = bytes.fromhex(artifact["content"])
                kind = artifact["kind"]
                digest = artifact["digest"]
                identity = hashlib.sha256((pair + task + kind + digest).encode()).hexdigest()
                c.execute(
                    "INSERT OR IGNORE INTO artifacts VALUES (?,?,?,?,?,'active','none',?)",
                    (pair, task, identity, digest, kind, content),
                )
                c.execute(
                    "INSERT OR IGNORE INTO artifact_lifecycle VALUES (?,?,?,NULL,NULL,NULL)",
                    (pair, identity, now),
                )
                restored += 1
            self._invalidate_learning(c, pair, purge=True)
        self.recover_artifacts()
        return restored

    @classmethod
    def _objective_scope(cls, scope: Mapping[str, str]) -> str:
        cls._scope(scope)
        return cls._encode([scope["project_id"], scope["workspace_id"], "discover"])

    def _discovery_row(
        self,
        connection: sqlite3.Connection,
        scope: Mapping[str, str],
        discovery_id: str,
    ) -> tuple[Any, ...] | None:
        if scope["operation"] != "discover":
            raise ContractError("invalid discovery operation")
        row = connection.execute(
            "SELECT d.objective,d.request_digest,d.allowance,d.seed,d.result,d.trace,d.scope,p.deleted FROM discoveries d JOIN discovery_objectives p ON p.scope=d.objective_scope AND p.objective=d.objective WHERE d.discovery_id=? AND d.objective_scope=?",
            (discovery_id, self._objective_scope(scope)),
        ).fetchone()
        if row is None or row[6] != self._scope(scope):
            return None
        if row[7]:
            raise ContractError("discovery objective deleted")
        return tuple(row)

    def reserve_discovery(
        self,
        scope: Mapping[str, str],
        key: str,
        digest: str,
        objective: str,
        allowance: Mapping[str, Any],
        seed: Mapping[str, Any],
    ) -> dict[str, Any]:
        if scope["operation"] != "discover" or not key:
            raise ContractError("invalid discovery reservation")
        parent, encoded = self._objective_scope(scope), self._scope(scope)
        with self._connect(True) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO discovery_objectives VALUES (?,?,0)", (parent, objective)
            )
            if connection.execute(
                "SELECT deleted FROM discovery_objectives WHERE scope=? AND objective=?",
                (parent, objective),
            ).fetchone()[0]:
                raise ContractError("discovery objective deleted")
            row = connection.execute(
                "SELECT discovery_id,request_digest FROM discoveries WHERE scope=? AND request_key=?",
                (encoded, key),
            ).fetchone()
            if row is not None:
                if row[1] != digest:
                    raise ContractError("discovery idempotency conflict")
                return {"discovery_id": row[0], "created": False}
            identity = str(uuid4())
            connection.execute(
                "INSERT INTO discoveries VALUES (?,?,?,?,?,?,?,?,NULL,NULL)",
                (
                    encoded,
                    parent,
                    objective,
                    key,
                    digest,
                    identity,
                    self._encode(allowance),
                    self._encode(seed),
                ),
            )
            return {"discovery_id": identity, "created": True}

    def load_discovery(self, scope: Mapping[str, str], discovery_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = self._discovery_row(connection, scope, discovery_id)
            if row is None:
                return None
            return self._discovery_snapshot(connection, row, discovery_id)

    def _discovery_snapshot(
        self, connection: sqlite3.Connection, row: tuple[Any, ...], discovery_id: str
    ) -> dict[str, Any]:
        rounds = [
            {
                "round_number": item[0],
                "question": json.loads(item[1]),
                "budget_before": json.loads(item[2]),
            }
            for item in connection.execute(
                "SELECT round_number,question,budget_before FROM discovery_rounds WHERE discovery_id=? ORDER BY round_number",
                (discovery_id,),
            )
        ]
        calls = [
            {
                "sequence": item[0],
                "round_number": item[1],
                "option_id": item[2],
                "reservation": json.loads(item[3]),
                "observation": None if item[4] is None else json.loads(item[4]),
            }
            for item in connection.execute(
                "SELECT sequence,round_number,option_id,reservation,observation FROM discovery_calls WHERE discovery_id=? ORDER BY sequence",
                (discovery_id,),
            )
        ]
        return {
            "discovery_id": discovery_id,
            "work_objective_id": row[0],
            "request_digest": row[1],
            "allowance": json.loads(row[2]),
            "seed": json.loads(row[3]),
            "result": None if row[4] is None else json.loads(row[4]),
            "trace": None if row[5] is None else json.loads(row[5]),
            "rounds": rounds,
            "calls": calls,
        }

    def recover_discovery(
        self,
        scope: Mapping[str, str],
        discovery_id: str,
        reducer: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    ) -> dict[str, Any]:
        with self._connect(True) as connection:
            row = self._discovery_row(connection, scope, discovery_id)
            if row is None:
                raise ContractError("discovery unavailable")
            if row[4] is not None:
                return dict(json.loads(row[4]))
            trace = reducer(self._discovery_snapshot(connection, row, discovery_id))
            connection.execute(
                "UPDATE discoveries SET result=?,trace=? WHERE discovery_id=? AND result IS NULL",
                (self._encode(trace["result"]), self._encode(trace), discovery_id),
            )
            return dict(trace["result"])

    def begin_discovery_round(
        self,
        scope: Mapping[str, str],
        discovery_id: str,
        question: Mapping[str, Any],
        budget_before: Mapping[str, Any],
    ) -> int:
        with self._connect(True) as connection:
            row = self._discovery_row(connection, scope, discovery_id)
            if row is None or row[4] is not None:
                raise ContractError("discovery attempt terminal or unavailable")
            allowance = json.loads(row[2])
            count = connection.execute(
                "SELECT COUNT(*) FROM discovery_rounds WHERE discovery_id=?", (discovery_id,)
            ).fetchone()[0]
            if count >= allowance["max_rounds"]:
                raise ContractError("discovery round allowance exhausted")
            connection.execute(
                "INSERT INTO discovery_rounds VALUES (?,?,?,?)",
                (discovery_id, count, self._encode(question), self._encode(budget_before)),
            )
            return int(count)

    def reserve_discovery_call(
        self,
        scope: Mapping[str, str],
        discovery_id: str,
        round_number: int,
        option_id: str,
        reservation: Mapping[str, Any],
    ) -> int:
        with self._connect(True) as connection:
            row = self._discovery_row(connection, scope, discovery_id)
            if row is None or row[4] is not None:
                raise ContractError("discovery attempt terminal or unavailable")
            limits = json.loads(row[2])
            question_row = connection.execute(
                "SELECT question FROM discovery_rounds WHERE discovery_id=? AND round_number=?",
                (discovery_id, round_number),
            ).fetchone()
            if question_row is None:
                raise ContractError("unbound discovery reservation")
            question = json.loads(question_row[0])
            if option_id not in {
                item["option_id"] for item in question["options"] if item["feasible"] is True
            }:
                raise ContractError("unoffered discovery reservation")
            previous = connection.execute(
                "SELECT option_id,reservation FROM discovery_calls WHERE discovery_id=? ORDER BY sequence",
                (discovery_id,),
            ).fetchall()
            if any(item[0] == option_id for item in previous):
                raise ContractError("duplicate discovery reservation")
            reservations = [json.loads(item[1]) for item in previous] + [dict(reservation)]
            if reservation["output_tokens"] != limits["output_planning_reservation"]:
                raise ContractError("discovery output reservation mismatch")
            if (
                len(reservations) > limits["max_calls"]
                or sum(item["input_tokens"] for item in reservations) > limits["max_input_tokens"]
                or any(
                    type(item[key]) is not int or item[key] < 0
                    for item in reservations
                    for key in ("input_tokens", "output_tokens")
                )
            ):
                raise ContractError("discovery call allowance exhausted")
            ceiling = limits["spending_ceiling"]
            if ceiling is not None and (
                any(item["currency"] != ceiling["currency"] for item in reservations)
                or any(item["reserved_spend"] is None for item in reservations)
                or sum(Decimal(item["reserved_spend"]) for item in reservations)
                > Decimal(ceiling["amount"])
            ):
                raise ContractError("discovery spending allowance exhausted")
            sequence = len(previous)
            connection.execute(
                "INSERT INTO discovery_calls VALUES (?,?,?,?,?,NULL)",
                (discovery_id, sequence, round_number, option_id, self._encode(reservation)),
            )
            return sequence

    def observe_discovery_call(
        self,
        scope: Mapping[str, str],
        discovery_id: str,
        sequence: int,
        observation: Mapping[str, Any],
    ) -> bool:
        with self._connect(True) as connection:
            row = self._discovery_row(connection, scope, discovery_id)
            if row is None:
                raise ContractError("discovery unavailable")
            previous = connection.execute(
                "SELECT observation FROM discovery_calls WHERE discovery_id=? AND sequence=?",
                (discovery_id, sequence),
            ).fetchone()
            if previous is None:
                raise ContractError("unreserved discovery observation")
            encoded = self._encode(observation)
            if previous[0] is not None and previous[0] != encoded:
                raise ContractError("immutable discovery observation conflict")
            if previous[0] is None:
                connection.execute(
                    "UPDATE discovery_calls SET observation=? WHERE discovery_id=? AND sequence=?",
                    (encoded, discovery_id, sequence),
                )
            return row[4] is None

    def commit_discovery(
        self,
        scope: Mapping[str, str],
        discovery_id: str,
        trace: Mapping[str, Any],
    ) -> dict[str, Any]:
        with self._connect(True) as connection:
            row = self._discovery_row(connection, scope, discovery_id)
            if row is None:
                raise ContractError("discovery unavailable")
            if row[4] is not None:
                return dict(json.loads(row[4]))
            if (
                trace["result"]["details"]["discovery_id"] != discovery_id
                or trace["result"]["details"]["work_objective_id"] != row[0]
            ):
                raise ContractError("discovery identity mismatch")
            connection.execute(
                "UPDATE discoveries SET result=?,trace=? WHERE discovery_id=? AND result IS NULL",
                (self._encode(trace["result"]), self._encode(trace), discovery_id),
            )
            return dict(trace["result"])

    def delete_discovery(self, scope: Mapping[str, str], objective: str) -> dict[str, Any]:
        if scope["operation"] != "discover":
            raise ContractError("invalid discovery operation")
        with self._connect(True) as connection:
            parent = self._objective_scope(scope)
            connection.execute(
                "INSERT INTO discovery_objectives VALUES (?,?,1) ON CONFLICT(scope,objective) DO UPDATE SET deleted=1",
                (parent, objective),
            )
            identities = [
                row[0]
                for row in connection.execute(
                    "SELECT discovery_id FROM discoveries WHERE objective_scope=? AND objective=?",
                    (parent, objective),
                )
            ]
            for identity in identities:
                connection.execute("DELETE FROM discovery_calls WHERE discovery_id=?", (identity,))
                connection.execute("DELETE FROM discovery_rounds WHERE discovery_id=?", (identity,))
                connection.execute(
                    "UPDATE artifacts SET retention='retired' WHERE scope=? AND artifact_id IN (SELECT artifact_id FROM discovery_content_artifacts WHERE discovery_id=?)",
                    (self._task_scope(scope), identity),
                )
            connection.execute(
                "UPDATE discoveries SET seed='{}',result=NULL,trace=NULL WHERE objective_scope=? AND objective=?",
                (parent, objective),
            )
            self._invalidate_learning(
                connection, self._task_scope(scope), objective=objective, purge=True
            )
        self.recover_artifacts()
        return {"schema_version": "1", "status": "deleted", "work_objective_id": objective}

    @classmethod
    def _scope(cls, scope: Mapping[str, str]) -> str:
        if set(scope) != {"project_id", "workspace_id", "producer", "operation"} or not all(
            isinstance(value, str) and value for value in scope.values()
        ):
            raise ContractError("invalid scope")
        return cls._encode(dict(scope))

    @classmethod
    def _task_scope(cls, scope: Mapping[str, str]) -> str:
        cls._scope(scope)
        return cls._encode([scope["project_id"], scope["workspace_id"]])

    def _artifact_directory(self, pair: str) -> Path:
        directory = self.path.parent / "artifacts" / hashlib.sha256(pair.encode()).hexdigest()
        if os.name != "nt":
            return directory
        absolute = os.path.abspath(directory)
        if absolute.startswith("\\\\?\\"):
            return Path(absolute)
        if absolute.startswith("\\\\"):
            return Path("\\\\?\\UNC\\" + absolute[2:])
        return Path("\\\\?\\" + absolute)

    @staticmethod
    def _admit(connection: sqlite3.Connection, scope: str, task: str) -> bool:
        connection.execute("INSERT OR IGNORE INTO tasks VALUES (?,?,0)", (scope, task))
        return bool(
            connection.execute(
                "SELECT deleted FROM tasks WHERE scope=? AND task=?", (scope, task)
            ).fetchone()[0]
            == 0
        )

    def lookup_retry(
        self,
        scope: Mapping[str, str],
        key: str,
        digest: str,
        discovery_ref: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any] | None:
        with self._connect() as connection:
            if discovery_ref is not None:
                self._check_discovery_link(connection, scope, discovery_ref)
            return self._retry(connection, self._scope(scope), key, digest)

    def _check_discovery_link(
        self, connection: sqlite3.Connection, scope: Mapping[str, str], linkage: Mapping[str, str]
    ) -> None:
        source = self._discovery_row(
            connection, dict(scope, operation="discover"), linkage["discovery_id"]
        )
        if source is None or source[4] is None:
            raise ContractError("linked discovery unavailable")
        result = json.loads(source[4])
        if (
            source[0] != linkage["work_objective_id"]
            or result["status"] not in {"selected_guidance", "no_optional_guidance"}
            or result["details"]["trace_digest"] != linkage["trace_digest"]
        ):
            raise ContractError("linked discovery invalid")

    def is_deleted(self, scope: Mapping[str, str], task: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT deleted FROM tasks WHERE scope=? AND task=?",
                (self._task_scope(scope), task),
            ).fetchone()
        return bool(row is not None and row[0] == 1)

    def lookup_cache(self, scope: Mapping[str, str], digest: str) -> Mapping[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT bundle FROM decisions_v1 WHERE scope=? AND json_extract(bundle,'$.cache_digest')=? ORDER BY decision_id LIMIT 1",
                (self._scope(scope), digest),
            ).fetchone()
        return None if row is None else dict(json.loads(row[0]))

    @staticmethod
    def _retry(
        connection: sqlite3.Connection, scope: str, key: str, digest: str
    ) -> Mapping[str, Any] | None:
        row = connection.execute(
            "SELECT digest,response FROM retries WHERE scope=? AND key=?", (scope, key)
        ).fetchone()
        if row is None:
            return None
        if row[0] != digest:
            raise ContractError("idempotency conflict")
        return dict(json.loads(row[1]))

    def commit_decision(
        self, scope: Mapping[str, str], key: str, digest: str, bundle: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        encoded, pair = self._scope(scope), self._task_scope(scope)
        expected = bundle.get("request_digest", canonical_digest(bundle))
        if (
            not key
            or expected != digest
            or not bundle.get("routing_decision_id")
            or not bundle.get("task_id")
        ):
            raise ContractError("invalid decision digest or identity")
        with self._connect(True) as connection:
            linkage = bundle.get("decision", {}).get("details", {}).get("discovery_ref")
            if linkage is not None:
                self._check_discovery_link(connection, scope, linkage)
            if not self._admit(connection, pair, bundle["task_id"]):
                raise ContractError("task deleted")
            retry = self._retry(connection, encoded, key, digest)
            if retry is not None:
                return dict(retry) | {"status": "duplicate"}
            identity = bundle["routing_decision_id"]
            details = bundle.get("decision", {}).get("details", {})
            if any(
                row["code"] == "learned_policy_ordering" for row in details.get("diagnostics", [])
            ):
                policy = connection.execute(
                    "SELECT status,payload FROM policy_records WHERE scope=? AND revision=?",
                    (pair, details["versions"]["policy_revision"]),
                ).fetchone()
                if policy and (
                    policy[0] != "active"
                    or json.loads(policy[1])["assessment"]["evidence_digest"]
                    not in details["evidence_refs"]
                ):
                    raise ContractError("policy_changed_before_decision_commit")
            existing = connection.execute(
                "SELECT bundle FROM decisions_v1 WHERE task_scope=? AND decision_id=?",
                (pair, identity),
            ).fetchone()
            if existing is not None:
                raise ContractError("immutable decision identity conflict")
            connection.execute(
                "INSERT INTO decisions_v1 VALUES (?,?,?,?,?)",
                (encoded, pair, bundle["task_id"], identity, self._encode(dict(bundle))),
            )
            response = {"status": "committed", "bundle": dict(bundle)}
            connection.execute(
                "INSERT INTO retries VALUES (?,?,?,?,?,?)",
                (encoded, key, digest, pair, bundle["task_id"], self._encode(response)),
            )
        return response

    def ingest_report(
        self, scope: Mapping[str, str], key: str, digest: str, event: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        encoded, pair = self._scope(scope), self._task_scope(scope)
        identity, task = event.get("event_id"), event.get("task_id")
        if not key or not identity or not task or canonical_digest(event) != digest:
            raise ContractError("invalid event digest")

        def ack(status: str, reason: str | None = None) -> dict[str, Any]:
            value: dict[str, Any] = {
                "status": status,
                "event_id": identity,
                "durable": status in {"accepted", "duplicate"},
            }
            if reason is not None:
                value["reason"] = reason
            return value

        with self._connect(True) as connection:
            if not self._admit(connection, pair, task):
                return ack("rejected", "deleted")
            try:
                retry = self._retry(connection, encoded, key, digest)
            except ContractError:
                return ack("conflict", "idempotency_key")
            if retry is not None:
                return ack("duplicate")
            existing = connection.execute(
                "SELECT digest FROM events_v1 WHERE task_scope=? AND event_id=?", (pair, identity)
            ).fetchone()
            if existing:
                if existing[0] != digest:
                    return ack("conflict", "event_id")
                response = ack("duplicate")
                connection.execute(
                    "INSERT INTO retries VALUES (?,?,?,?,?,?)",
                    (encoded, key, digest, pair, task, self._encode(response)),
                )
                return response
            previous = event.get("supersedes_event_id")
            if previous:
                original = connection.execute(
                    "SELECT scope,task,run_id,payload FROM events_v1 WHERE task_scope=? AND event_id=?",
                    (pair, previous),
                ).fetchone()
                if (
                    original is None
                    or original[:3] != (encoded, task, event.get("execution_run_id", ""))
                    or previous == identity
                ):
                    return ack("rejected", "invalid correction reference")
                if connection.execute(
                    "SELECT 1 FROM events_v1 WHERE task_scope=? AND supersedes=?", (pair, previous)
                ).fetchone():
                    return ack("rejected", "correction chain fork")
                original_payload = json.loads(original[3]).get("payload", {})
                replacement = event.get("payload", {})
                terminal = {"completed", "failed", "canceled"}
                if (
                    original_payload.get("event_type") in terminal
                    and replacement.get("event_type") not in terminal
                ):
                    return ack("rejected", "terminal correction regression")
            connection.execute(
                "INSERT INTO events_v1 VALUES (?,?,?,?,?,?,?,?)",
                (
                    encoded,
                    pair,
                    task,
                    identity,
                    event.get("execution_run_id", ""),
                    previous,
                    digest,
                    self._encode(dict(event)),
                ),
            )
            response = ack("accepted")
            self._invalidate_learning(connection, pair, task)
            connection.execute(
                "INSERT INTO retries VALUES (?,?,?,?,?,?)",
                (encoded, key, digest, pair, task, self._encode(response)),
            )
        return response

    def load_replay(self, scope: Mapping[str, str], decision_id: str) -> Mapping[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT bundle FROM decisions_v1 WHERE scope=? AND decision_id=?",
                (self._scope(scope), decision_id),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def project_run(self, scope: Mapping[str, str], run_id: str) -> Mapping[str, Any]:
        pair = self._task_scope(scope)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM events_v1 WHERE task_scope=? AND run_id=?", (pair, run_id)
            ).fetchall()
            known = {
                row[0]
                for row in connection.execute(
                    "SELECT decision_id FROM decisions_v1 WHERE task_scope=?", (pair,)
                )
            }
        events = [json.loads(row[0]) for row in rows]
        superseded = {event.get("supersedes_event_id") for event in events}
        active = [event for event in events if event["event_id"] not in superseded]
        ordered = sorted(
            active,
            key=lambda row: (
                row.get("source_sequence", 0),
                row.get("source_id", ""),
                row["event_id"],
            ),
        )
        progress = {
            "queued": 0,
            "started": 1,
            "plan_applied": 2,
            "completed": 3,
            "failed": 3,
            "canceled": 3,
        }
        lifecycle = [row for row in ordered if row.get("payload", {}).get("event_type") in progress]
        latest = max(
            lifecycle,
            key=lambda row: (
                progress[row["payload"]["event_type"]],
                row.get("source_sequence", 0),
                row["event_id"],
            ),
            default=None,
        )
        return {
            "status": None if latest is None else latest["payload"]["event_type"],
            "events": ordered,
            "unresolved_decisions": sorted(
                {row.get("routing_decision_id", "") for row in active} - known
            ),
        }

    def task_attempts(self, scope: Mapping[str, str], task: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT count(DISTINCT run_id) FROM events_v1 WHERE task_scope=? AND task=? AND json_extract(payload,'$.payload.event_type') IN ('started','plan_applied','completed','failed','canceled')",
                (self._task_scope(scope), task),
            ).fetchone()
        return int(row[0])

    def stage_artifact(
        self,
        scope: Mapping[str, str],
        task: str,
        content: bytes,
        *,
        kind: str,
        retention: str,
        encryption: str,
        retain_raw_tasks: bool = False,
        retain_raw_outputs: bool = False,
        discovery_id: str | None = None,
        created_at: float | None = None,
        archive_source: str | None = None,
        archived_at: float | None = None,
    ) -> str | None:
        if (
            kind == "raw_task"
            and not retain_raw_tasks
            or kind == "raw_output"
            and not retain_raw_outputs
        ):
            return None
        if kind == "archive" and encryption == "none":
            raise ContractError("plaintext archive prohibited")
        pair = self._task_scope(scope)
        digest = hashlib.sha256(content).hexdigest()
        identity = hashlib.sha256((pair + task + kind + digest).encode()).hexdigest()
        with self._connect(True) as connection:
            linked = connection.execute(
                "SELECT discovery_id FROM discovery_content_artifacts WHERE scope=? AND (artifact_id=? OR artifact_id=?)",
                (pair, identity, archive_source),
            ).fetchone()
            discovery_id = discovery_id or (linked[0] if linked else None)
            if discovery_id is not None:
                owner = connection.execute(
                    "SELECT scope FROM discoveries WHERE discovery_id=? AND objective_scope=?",
                    (discovery_id, self._objective_scope(scope)),
                ).fetchone()
                if task != discovery_id or owner is None:
                    raise ContractError("discovery content deleted or unavailable")
                self._discovery_row(connection, json.loads(owner[0]), discovery_id)
            if not self._admit(connection, pair, task):
                raise ContractError("task deleted")
            connection.execute(
                "INSERT OR IGNORE INTO artifacts VALUES (?,?,?,?,?,?,?,?)",
                (pair, task, identity, digest, kind, retention, encryption, content),
            )
            connection.execute(
                "INSERT OR IGNORE INTO artifact_lifecycle VALUES (?,?,?,NULL,?,?)",
                (
                    pair,
                    identity,
                    time() if created_at is None else created_at,
                    archived_at,
                    archive_source,
                ),
            )
            if discovery_id is not None:
                connection.execute(
                    "INSERT OR IGNORE INTO discovery_content_artifacts VALUES (?,?,?)",
                    (pair, discovery_id, identity),
                )
        self.recover_artifacts()
        return identity

    def recover_artifacts(self) -> None:
        # A short write transaction serializes replacement with deletion.
        with self._connect(True) as connection:
            deleted = connection.execute(
                "SELECT artifacts.scope,artifact_id FROM artifacts JOIN tasks ON artifacts.scope=tasks.scope AND artifacts.task=tasks.task WHERE tasks.deleted=1 OR artifacts.retention='retired'"
            ).fetchall()
            for pair, identity in deleted:
                directory = self._artifact_directory(pair)
                (directory / identity).unlink(missing_ok=True)
                (directory / (identity + ".pending")).unlink(missing_ok=True)
                connection.execute(
                    "DELETE FROM artifacts WHERE scope=? AND artifact_id=?", (pair, identity)
                )
                connection.execute(
                    "DELETE FROM artifact_lifecycle WHERE scope=? AND artifact_id=?",
                    (pair, identity),
                )
            rows = connection.execute(
                "SELECT scope,artifact_id,digest,pending FROM artifacts WHERE pending IS NOT NULL"
            ).fetchall()
            for pair, identity, digest, content in rows:
                if hashlib.sha256(content).hexdigest() != digest:
                    raise ContractError("artifact digest mismatch")
                directory = self._artifact_directory(pair)
                directory.mkdir(parents=True, exist_ok=True)
                temporary = directory / (identity + ".pending")
                with temporary.open("wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, directory / identity)
                connection.execute(
                    "UPDATE artifacts SET pending=NULL WHERE scope=? AND artifact_id=?",
                    (pair, identity),
                )

    def archive(
        self,
        scope: Mapping[str, str],
        task: str,
        content: bytes,
        key_provider: Callable[[], bytes | None],
        encrypt: Callable[[bytes, bytes], bytes],
    ) -> str | None:
        key = key_provider()
        if key is None:
            pair = self._task_scope(scope)
            with self._connect(True) as connection:
                if not self._admit(connection, pair, task):
                    raise ContractError("task deleted")
                connection.execute(
                    "INSERT OR IGNORE INTO notices VALUES (?,?,'archive_key_missing')", (pair, task)
                )
            return None
        encrypted = encrypt(content, key)
        if not encrypted or encrypted == content:
            raise ContractError("archive encryption failed")
        return self.stage_artifact(
            scope, task, encrypted, kind="archive", retention="archive", encryption="key_provider"
        )

    def archive_artifact(
        self,
        scope: Mapping[str, str],
        identity: str,
        key_provider: Callable[[], bytes | None],
        encrypt: Callable[[bytes, bytes], bytes],
    ) -> str | None:
        pair = self._task_scope(scope)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT task,digest,pending FROM artifacts WHERE scope=? AND artifact_id=?",
                (pair, identity),
            ).fetchone()
        if row is None or self.is_deleted(scope, row[0]):
            raise ContractError("artifact unavailable")
        path = self._artifact_directory(pair) / identity
        content = row[2] if row[2] is not None else path.read_bytes()
        if hashlib.sha256(content).hexdigest() != row[1]:
            raise ContractError("artifact digest mismatch")
        # The active indexed source remains durable until LEARN's retention policy expires it.
        return self.archive(scope, row[0], content, key_provider, encrypt)

    def load_notices(self, scope: Mapping[str, str]) -> list[dict[str, Any]]:
        pair = self._task_scope(scope)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT notices.task,notices.kind FROM notices JOIN tasks "
                "ON notices.scope=tasks.scope AND notices.task=tasks.task "
                "WHERE notices.scope=? AND tasks.deleted=0 ORDER BY notices.task,notices.kind",
                (pair,),
            ).fetchall()
            lifecycle = connection.execute(
                "SELECT payload FROM lifecycle_notices WHERE scope=? ORDER BY notice_id", (pair,)
            ).fetchall()
        return [
            {
                "notice_id": str(uuid5(NAMESPACE_URL, canonical_digest([pair, task, kind]))),
                "kind": "decision_required" if kind == "archive_key_missing" else "failure",
                "summary": (
                    "Archive key unavailable; content remains local. Configure an archive key "
                    "through the authorized host before retrying archival."
                    if kind == "archive_key_missing"
                    else "Local action failed; review pending host actions."
                ),
                "deadline": None,
                "automatic_action": "none",
            }
            for task, kind in rows
        ] + [json.loads(row[0]) for row in lifecycle]

    def delete_task(self, scope: Mapping[str, str], task_id: str) -> Mapping[str, Any]:
        pair = self._task_scope(scope)
        if not task_id:
            raise ContractError("missing task identity")
        with self._connect(True) as connection:
            connection.execute(
                "INSERT INTO tasks VALUES (?,?,1) ON CONFLICT(scope,task) DO UPDATE SET deleted=1",
                (pair, task_id),
            )
            for table in ("decisions_v1", "events_v1", "retries"):
                connection.execute(
                    f"DELETE FROM {table} WHERE task_scope=? AND task=?", (pair, task_id)
                )
            for table in (
                "notices",
                "learning_context",
                "task_learning_policy",
                "lifecycle_notices",
            ):
                connection.execute(f"DELETE FROM {table} WHERE scope=? AND task=?", (pair, task_id))
            connection.execute(
                "INSERT INTO policy_validation VALUES (?,1) ON CONFLICT(scope) DO UPDATE SET stale=1",
                (pair,),
            )
            self._invalidate_learning(connection, pair, task_id, purge=True)
            identities = [
                row[0]
                for row in connection.execute(
                    "SELECT identity FROM experiment_occurrences WHERE scope=? AND task=?",
                    (pair, task_id),
                )
            ]
            for identity in identities:
                self._cancel_experiment(connection, pair, identity, deleted=True)
                for table in (
                    "experiment_proposals",
                    "experiment_occurrences",
                    "experiment_requests",
                    "experiment_lineage",
                ):
                    connection.execute(
                        f"DELETE FROM {table} WHERE scope=? AND identity=?", (pair, identity)
                    )
            for revision, payload in connection.execute(
                "SELECT revision,payload FROM policy_studies WHERE scope=?", (pair,)
            ).fetchall():
                if any(
                    case["task_id"] == task_id
                    for case in json.loads(payload)["definition"]["cases"]
                ):
                    connection.execute(
                        "DELETE FROM policy_studies WHERE scope=? AND revision=?", (pair, revision)
                    )
        self.recover_artifacts()
        with self._connect() as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return {"status": "deleted", "task_id": task_id}
