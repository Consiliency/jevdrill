"""Throwaway timing probe for S5a. It lives only on a probe branch and is never merged.

It times what DevelopmentJudge does before it dispatches (render the request, commit a
reservation, start a child process) and its construction, then runs the judge tests
several times in a row. Usage: python probe/s5a_probe.py [runs]
"""

import json
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from baml_sdk import development_task_request_shape
from jevdrill.integrations.development import DevelopmentJudge

RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 10


def timed(action, count=30):
    seconds = []
    for _ in range(count):
        started = time.perf_counter()
        action()
        seconds.append(time.perf_counter() - started)
    seconds.sort()
    return {
        "n": count,
        "median": round(statistics.median(seconds), 3),
        "max": round(seconds[-1], 3),
        "min": round(seconds[0], 3),
    }


report = {"platform": sys.platform, "python": sys.version.split()[0]}
report["render_request_seconds"] = timed(
    lambda: development_task_request_shape("task", '{"candidate_id": "one"}', "jev-1.13.0")
)
report["child_start_seconds"] = timed(
    lambda: subprocess.run([sys.executable, "-I", "-S", "-c", "pass"], check=True)
)
with tempfile.TemporaryDirectory() as directory:
    names = iter(range(1000))

    def reserve():
        with closing(sqlite3.connect(Path(directory) / f"{next(names)}.db", timeout=1)) as db, db:
            db.execute("CREATE TABLE calls (identity TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO calls VALUES('one', 'payload')")

    report["new_database_commit_seconds"] = timed(reserve)

    def construct():
        DevelopmentJudge(
            Path(directory) / f"judge-{next(names)}.db",
            scope={
                "project_id": str(uuid4()),
                "workspace_id": str(uuid4()),
                "producer": "probe",
                "operation": "discover",
            },
            authorization_revision="probe",
            max_calls=2,
            total_spend_microusd=5506,
            deadline_ms=int(time.time() * 1000) + 60000,
            credential=lambda: "synthetic-secret",
            authorize=lambda scope: True,
            base_url="http://127.0.0.1:9/v1",
        )

    report["construct_judge_seconds"] = timed(construct)
print(json.dumps(report, indent=2), flush=True)

results = []
for number in range(1, RUNS + 1):
    started = time.perf_counter()
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/experiments/test_development_judge.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "--durations=3",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    summary = run.stdout.strip().splitlines()[-1] if run.stdout.strip() else "no output"
    results.append(run.returncode)
    print(f"run {number}: exit {run.returncode}, {time.perf_counter() - started:.0f} s, {summary}")
    if run.returncode:
        print(run.stdout[-6000:], flush=True)
print("judge runs passed:", results.count(0), "of", RUNS, flush=True)
sys.exit(1 if any(results) else 0)
