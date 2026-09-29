"""Run local CONTRACT checks and reduce real platform manifests; fail closed."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MATRIX = {("Linux", "3.13"), ("Darwin", "3.13"), ("Windows", "3.13")}
CHECKS = {
    "tests", "generation", "coverage", "vocabulary", "glossary", "imports",
    "lint", "format", "types", "build",
}


def input_digest(root):
    paths = set()
    for pattern in ("src/**/*.py", "src/**/*.pyi", "src/**/*.json", "baml_src/*",
                    "schemas/*.json", "tests/**/*.py", "tests/contracts/fixtures/*.json",
                    "scripts/*.py", "scripts/*.mjs", "docs/vocabulary.*", "pyproject.toml",
                    "uv.lock", "package*.json", "baml.toml", ".python-version",
                    "specs/*.md", ".github/workflows/contracts.yml", "plans/phase-plan-v1-CONTRACT.md",
                    "evidence/CONTRACT/coverage.json", "evidence/CONTRACT/evaluation-protocol.json"):
        paths.update(p for p in root.glob(pattern) if p.is_file())
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda path: path.relative_to(root).as_posix()):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def reduce_manifests(manifests, expected_digest):
    errors, seen = [], set()
    for row in manifests:
        identity = (row.get("os"), row.get("python_minor"))
        if identity not in MATRIX or identity in seen:
            errors.append("unexpected or duplicate platform")
        seen.add(identity)
        if row.get("input_digest") != expected_digest:
            errors.append("stale input digest")
        if row.get("bridge_version") != "0.20.1" or row.get("compiler_version") != "baml-cli 0.20.1":
            errors.append("tool pin mismatch")
        if row.get("schema_version") != 1 or row.get("execution_kind") != "native":
            errors.append("unsupported evidence")
        if not row.get("runner_identity") or not row.get("architecture"):
            errors.append("missing runner identity")
        checks = row.get("checks", [])
        required = CHECKS | ({"catalog"} if row.get("os") == "Linux" else set())
        if {check.get("name") for check in checks} != required or len(checks) != len(required):
            errors.append("missing or duplicate checks")
        if any(check.get("exit_code") != 0 or not check.get("command") for check in checks):
            errors.append("failed check")
        if row.get("tests", {}).get("skipped") != 0 or row.get("tests", {}).get("total", 0) <= 0:
            errors.append("missing assertions or skipped tests")
    errors.extend(f"missing {os_name}/Python {minor}" for os_name, minor in sorted(MATRIX - seen))
    return errors


def collect(root):
    py = sys.executable
    with tempfile.TemporaryDirectory(prefix="jevdrill-verification-") as temporary:
        junit = Path(temporary) / "tests.xml"
        commands = {
            "tests": [py, "-m", "pytest", "tests/contracts", "tests/evaluation", "-q", f"--junitxml={junit}", f"--basetemp={Path(temporary) / 'pytest'}"],
            "generation": [py, "scripts/check_generated_contracts.py"],
            "coverage": [py, "scripts/check_contract_coverage.py"],
            "vocabulary": [py, "scripts/lint_vocabulary.py"],
            "glossary": [py, "scripts/render_vocabulary.py", "--check"],
            "imports": [py, "scripts/check_import_boundaries.py"],
            "lint": [py, "-m", "ruff", "check", "src", "tests/contracts", "tests/evaluation"],
            "format": [py, "-m", "ruff", "format", "--check", "src", "tests/contracts", "tests/evaluation"],
            "types": [py, "-m", "mypy", "src/jevdrill"],
            "build": ["uv", "build"],
            "catalog": [py, "-m", "unittest", "discover", "-s", "tests", "-p", "test_catalog*.py"],
        }
        checks = []
        if platform.system() != "Linux":
            del commands["catalog"]  # Historical research imports Unix-only fcntl.
        for name, command in commands.items():
            try:
                result = subprocess.run(command, cwd=root, capture_output=True, timeout=300, check=False)
                code, output = result.returncode, result.stdout + result.stderr
            except (OSError, subprocess.TimeoutExpired) as error:
                code, output = 125, type(error).__name__.encode()
            checks.append({"name": name, "command": command, "exit_code": code,
                           "output_sha256": hashlib.sha256(output).hexdigest()})
            print(f"{name}: {'passed' if code == 0 else 'FAILED'}", flush=True)
            if code:
                print(output.decode(errors="replace")[-6000:], flush=True)
        tests = {"total": 0, "skipped": None}
        if junit.exists():
            suites = ET.parse(junit).getroot().findall("testsuite")
            tests = {"total": sum(int(s.get("tests", 0)) for s in suites),
                     "skipped": sum(int(s.get("skipped", 0)) for s in suites)}
    try:
        compiler = subprocess.run([os.environ.get("BAML_CLI", "baml-cli"), "--version"],
                                  capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        compiler = "unavailable"
    return {"schema_version": 1, "execution_kind": "native", "os": platform.system(),
            "architecture": platform.machine(), "python_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
            "python_version": platform.python_version(), "bridge_version": importlib.metadata.version("baml-bridge"),
            "compiler_version": compiler, "runner_identity": os.environ.get("GITHUB_RUN_ID", platform.node()),
            "timestamp": datetime.now(timezone.utc).isoformat(), "input_digest": input_digest(root),
            "checks": checks, "tests": tests}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--reduce-only", action="store_true")
    args = parser.parse_args()
    directory = ROOT / "evidence/CONTRACT/platforms"
    directory.mkdir(parents=True, exist_ok=True)
    current = None
    if not args.reduce_only:
        current = collect(ROOT)
        path = directory / f"{current['os']}-{current['python_minor']}.json"
        path.write_text(json.dumps(current, indent=2) + "\n")
    manifests = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))]
    errors = reduce_manifests(manifests, input_digest(ROOT))
    report = {"schema_version": 1, "phase": "CONTRACT", "status": "blocked" if errors else "passed",
              "errors": errors, "platforms": [row["os"] for row in manifests], "input_digest": input_digest(ROOT)}
    (ROOT / "evidence/CONTRACT/verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if args.local_only and current:
        local_errors = reduce_manifests([current], input_digest(ROOT))
        absent_platforms = {f"missing {os_name}/Python {minor}" for os_name, minor in MATRIX}
        return int(any(error not in absent_platforms for error in local_errors))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
