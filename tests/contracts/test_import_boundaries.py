import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "imports", ROOT / "scripts/check_import_boundaries.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_repository_imports():
    assert checker.check(ROOT) == []


def test_forbidden_relative_and_absolute_imports(tmp_path):
    (tmp_path / "docs").mkdir()
    shutil.copyfile(ROOT / "docs/vocabulary.yaml", tmp_path / "docs/vocabulary.yaml")
    package = tmp_path / "src/jevdrill"
    package.mkdir(parents=True)
    (package / "routing.py").write_text("from . import storage\nimport jevdrill.integrations\n")
    (package / "storage.py").write_text("from jevdrill import routing\n")
    errors = checker.check(tmp_path)
    assert any("routing -> storage" in e for e in errors)
    assert any("routing -> integrations" in e for e in errors)
    assert any("import cycle" in e for e in errors)


def test_unknown_module(tmp_path):
    (tmp_path / "docs").mkdir()
    shutil.copyfile(ROOT / "docs/vocabulary.yaml", tmp_path / "docs/vocabulary.yaml")
    package = tmp_path / "src/jevdrill"
    package.mkdir(parents=True)
    (package / "helpers.py").write_text("pass\n")
    assert checker.check(tmp_path) == ["unowned module: helpers.py"]
