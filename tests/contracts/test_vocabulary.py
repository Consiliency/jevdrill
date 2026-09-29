import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("vocabulary", ROOT / "scripts/lint_vocabulary.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_owned_usage():
    assert checker.check(ROOT) == []


def test_glossary_is_current():
    subprocess.run(
        [sys.executable, "scripts/render_vocabulary.py", "--check"], cwd=ROOT, check=True
    )


def test_forbidden_public_fields_and_historical_exemption(tmp_path):
    (tmp_path / "docs").mkdir()
    shutil.copyfile(ROOT / "docs/vocabulary.yaml", tmp_path / "docs/vocabulary.yaml")
    (tmp_path / "baml_src").mkdir()
    (tmp_path / "baml_src/contracts.baml").write_text(
        "class Bad { configuration: string, badField: int }"
    )
    (tmp_path / "docs/jevdrill-spec.md").write_text("execution_configuration")
    errors = checker.check(tmp_path)
    assert len(errors) == 2


def test_stale_glossary_rejected(tmp_path):
    # Run the actual renderer against its root discovery, with copied source inputs.
    for directory in ("scripts", "docs", "specs"):
        (tmp_path / directory).mkdir()
    for relative in (
        "scripts/render_vocabulary.py",
        "docs/vocabulary.yaml",
        "specs/jevdrill-design-input.md",
    ):
        shutil.copyfile(ROOT / relative, tmp_path / relative)
    (tmp_path / "docs/vocabulary.md").write_text("stale")
    result = subprocess.run(
        [sys.executable, "scripts/render_vocabulary.py", "--check"], cwd=tmp_path, check=False
    )
    assert result.returncode != 0
