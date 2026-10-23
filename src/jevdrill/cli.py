"""Portable bounded JSON transport. The timer precedes heavyweight imports."""

from time import monotonic

_STARTED = monotonic()

import argparse
import json
import os
import queue
import sqlite3
import sys
import threading
from pathlib import Path
from typing import Any, Never

MAX_INPUT_BYTES = 1_000_000
MAX_OUTPUT_BYTES = 1_000_000


class JsonParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ValueError("invalid command arguments")


def _default_storage() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "jevdrill" / "route.sqlite3"


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _input(deadline: float) -> dict[str, Any]:
    result: queue.Queue[bytes | Exception] = queue.Queue()

    def read() -> None:
        try:
            chunks: list[bytes] = []
            length = 0
            while length <= MAX_INPUT_BYTES:
                chunk = os.read(sys.stdin.fileno(), min(65536, MAX_INPUT_BYTES + 1 - length))
                if not chunk:
                    break
                length += len(chunk)
                chunks.append(chunk)
            result.put(b"".join(chunks))
        except (OSError, ValueError) as error:
            result.put(error)

    threading.Thread(target=read, daemon=True).start()
    try:
        raw = result.get(timeout=max(0, deadline - monotonic()))
    except queue.Empty as error:
        raise TimeoutError("input deadline expired") from error
    if isinstance(raw, Exception):
        raise raw
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input too large")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object)
    if not isinstance(value, dict):
        raise TypeError("JSON object required")
    return value


def main(argv: list[str] | None = None) -> int:
    try:
        parser = JsonParser(prog="jevdrill")
        parser.add_argument("--storage", type=Path, default=_default_storage())
        parser.add_argument("--remaining-budget-ms", type=int, default=5000)
        parser.add_argument("--request-file", type=Path)
        commands = parser.add_subparsers(dest="command", required=True)
        commands.add_parser("route")
        commands.add_parser("discover")
        commands.add_parser("report")
        commands.add_parser("notices")
        commands.add_parser("analyze")
        commands.add_parser("maintenance")
        commands.add_parser("recovery")
        commands.add_parser("experiment")
        commands.add_parser("experiment-execution")
        commands.add_parser("policy")
        commands.add_parser("policy-lifecycle")
        inspect = commands.add_parser("inspect")
        inspect.add_argument("--decision-id", required=True)
        inspect.add_argument("--scope", required=True)
        inspect.add_argument("--replay", action="store_true")
        delete = commands.add_parser("delete")
        delete.add_argument("--task-id", required=True)
        delete.add_argument("--scope", required=True)
        inspect_discovery = commands.add_parser("inspect-discovery")
        inspect_discovery.add_argument("--discovery-id", required=True)
        inspect_discovery.add_argument("--scope", required=True)
        inspect_discovery.add_argument("--replay", action="store_true")
        delete_discovery = commands.add_parser("delete-discovery")
        delete_discovery.add_argument("--work-objective-id", required=True)
        delete_discovery.add_argument("--scope", required=True)
        args = parser.parse_args(argv)
        if args.remaining_budget_ms <= 0:
            raise ValueError("invalid deadline")
        deadline = _STARTED + min(5000, args.remaining_budget_ms) / 1000
        if args.request_file is not None:
            if args.command != "maintenance":
                raise ValueError("request file requires maintenance")
            raw = args.request_file.read_bytes()
            if len(raw) > MAX_INPUT_BYTES:
                raise ValueError("input too large")
            payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_object)
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
        else:
            payload = (
                _input(deadline)
                if args.command
                in {
                    "route",
                    "report",
                    "discover",
                    "notices",
                    "analyze",
                    "maintenance",
                    "recovery",
                    "experiment",
                    "experiment-execution",
                    "policy",
                    "policy-lifecycle",
                }
                else None
            )
        from .application import open_application
        from .contracts import ContractError

        if monotonic() >= deadline:
            raise TimeoutError("startup deadline expired")
        app = open_application(args.storage, deadline)
        try:
            if args.command == "route":
                assert payload is not None
                response = app.route(payload, deadline)
            elif args.command == "discover":
                assert payload is not None
                response = app.discover(payload, deadline)
            elif args.command == "report":
                assert payload is not None
                response = app.report(payload)
            elif args.command == "notices":
                assert payload is not None
                response = app.notices(payload)
            elif args.command == "analyze":
                assert payload is not None
                response = app.analyze(payload)
            elif args.command == "maintenance":
                assert payload is not None
                response = app.maintain(payload)
            elif args.command == "recovery":
                assert payload is not None
                response = app.recover(payload)
            elif args.command == "experiment":
                assert payload is not None
                response = app.experiment(payload)
            elif args.command == "experiment-execution":
                assert payload is not None
                response = app.execute_experiment(payload)
            elif args.command == "policy":
                assert payload is not None
                response = app.policy(payload)
            elif args.command == "policy-lifecycle":
                assert payload is not None
                response = app.manage_policy(payload)
            else:
                scope = json.loads(args.scope, object_pairs_hook=_object)
                if not isinstance(scope, dict):
                    raise ValueError("invalid scope")
                if args.command == "inspect-discovery":
                    result = app.inspect_discovery(scope, args.discovery_id, args.replay)
                    response = (
                        {"schema_version": "1", "status": "not_found"} if result is None else result
                    )
                elif args.command == "delete-discovery":
                    response = app.delete_discovery(scope, args.work_objective_id)
                elif args.command == "inspect":
                    replay = app.replay(scope, args.decision_id)
                    response = (
                        {"schema_version": "1", "status": "not_found"} if replay is None else replay
                    )
                else:
                    response = app.delete_task(scope, args.task_id)
        except ContractError as error:
            if "conflict" in str(error):
                print(json.dumps({"schema_version": "1", "status": "conflict", "durable": False}))
                return 3
            raise
        if monotonic() >= deadline:
            raise TimeoutError("commit deadline expired")
        output = json.dumps(response, separators=(",", ":"), allow_nan=False)
        if len(output.encode()) > MAX_OUTPUT_BYTES:
            raise OSError("response too large")
        print(output)
        return 3 if response.get("status") == "conflict" else 0
    except (ValueError, TypeError, UnicodeError):
        print(json.dumps({"schema_version": "1", "status": "invalid", "code": "invalid_input"}))
        return 2
    except (OSError, sqlite3.Error):
        print(
            json.dumps(
                {
                    "schema_version": "1",
                    "status": "storage_failure",
                    "code": "infrastructure_failure",
                }
            )
        )
        return 4
    except KeyboardInterrupt:
        print(json.dumps({"schema_version": "1", "status": "canceled"}))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
