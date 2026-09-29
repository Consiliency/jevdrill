import importlib.metadata
import subprocess
import sys
import tarfile
import zipfile


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
