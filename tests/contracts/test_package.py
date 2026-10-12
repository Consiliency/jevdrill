import importlib.metadata
import json
import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import jsonschema


def test_package_import_outside_checkout(tmp_path):
    subprocess.run(
        [sys.executable, "-c", "import jevdrill; import jevdrill.contracts"],
        cwd=tmp_path,
        check=True,
    )


def test_bridge_matches_contract_pin():
    from jevdrill.contracts import schema_bundle

    assert (
        importlib.metadata.version("baml-bridge")
        == schema_bundle()["boundary.json"]["compiler_version"]
    )


def test_distribution_contains_only_application_files(tmp_path):
    subprocess.run(["uv", "build", "--out-dir", str(tmp_path)], check=True)
    with zipfile.ZipFile(next(tmp_path.glob("*.whl"))) as archive:
        paths = archive.namelist()
        assert "baml_sdk/_boundary_schemas.json" in paths
        assert "baml_sdk/vendor/typesafeai/__init__.py" in paths
        assert all(
            path.startswith(("jevdrill/", "baml_sdk/", "jevdrill-0.1.0.dev0.dist-info/"))
            for path in paths
        )
        assert not any("__pycache__" in path or ".baml-generator" in path for path in paths)
    with tarfile.open(next(tmp_path.glob("*.tar.gz"))) as archive:
        paths = [path.split("/", 1)[1] for path in archive.getnames() if "/" in path]
        assert all(
            path.startswith("src/")
            or path in {"pyproject.toml", "README.md", "PKG-INFO", ".gitignore"}
            for path in paths
        )


def test_installed_wheel_cli_outside_checkout(tmp_path):
    root = Path(__file__).resolve().parents[2]
    dist = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--out-dir", str(dist)], cwd=root, check=True, capture_output=True
    )
    environment = tmp_path / "environment"
    subprocess.run(
        ["uv", "venv", "--python", sys.executable, str(environment)],
        check=True,
        capture_output=True,
    )
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--no-deps",
            str(next(dist.glob("*.whl"))),
        ],
        check=True,
        capture_output=True,
    )
    # Reuse locked third-party dependencies without processing editable .pth files.
    env = dict(os.environ, PYTHONPATH=str(Path(jsonschema.__file__).resolve().parent.parent))
    located = subprocess.run(
        [str(python), "-c", "import jevdrill; print(jevdrill.__file__)"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert Path(located.stdout.strip()).is_relative_to(environment)
    payload = json.loads((root / "tests/contracts/fixtures/route-application.json").read_text())[0][
        "payload"
    ]
    cli = environment / ("Scripts/jevdrill.exe" if os.name == "nt" else "bin/jevdrill")
    argv = [str(python), "-m", "jevdrill.cli"] if os.name == "nt" else [str(cli)]
    result = subprocess.run(
        [*argv, "--storage", str(tmp_path / "route.db"), "route"],
        cwd=tmp_path,
        env=env,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "ready"
