import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def generator():
    spec = importlib.util.spec_from_file_location(
        "generator", ROOT / "scripts/check_generated_contracts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def artifact(payload):
    fingerprint = b"synthetic"
    version = (8).to_bytes(4, "little")
    header = (
        len(fingerprint).to_bytes(4, "little")
        + fingerprint
        + b"\0"
        + len(payload).to_bytes(8, "little")
    )
    header += hashlib.sha256(version + header + payload).digest()
    return b"BAMLART\0" + version + len(header).to_bytes(8, "little") + header + payload


def test_normalization_checks_hash_and_only_declared_paths():
    module = generator()
    path = b"baml_src/jev.baml"
    prefix = len(path).to_bytes(4, "little")
    linux = artifact(prefix + path + b"instruction")
    windows = artifact(prefix + path.replace(b"/", b"\\") + b"instruction")
    assert module.normalize_artifact(linux, [path.decode()]) == module.normalize_artifact(
        windows, [path.decode()]
    )
    assert module.normalize_artifact(linux, []) != module.normalize_artifact(windows, [])
    changed = artifact(prefix + path + b"different instruction")
    assert module.normalize_artifact(linux, [path.decode()]) != module.normalize_artifact(
        changed, [path.decode()]
    )
    with pytest.raises(ValueError, match="checksum mismatch"):
        module.normalize_artifact(linux[:-1] + b"X", [path.decode()])
    with pytest.raises(ValueError, match="unsupported"):
        module.normalize_artifact(b"corrupted" + linux[9:], [path.decode()])


def test_generation_is_reproducible():
    subprocess.run([sys.executable, "scripts/check_generated_contracts.py"], cwd=ROOT, check=True)


def test_wrong_compiler_fails_closed(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "generator", ROOT / "scripts/check_generated_contracts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="baml-cli 0.0.0"),
    )
    with pytest.raises(ValueError, match="compiler version mismatch"):
        module.generate()
