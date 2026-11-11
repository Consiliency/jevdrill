import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "development_runtime_checks",
    Path(__file__).resolve().parents[2] / "scripts/verify_development_runtime.py",
)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


@pytest.mark.parametrize(
    "defect",
    [None, "missing", "duplicate", "skipped", "failure", "error", "wrong_class", "exit_code"],
)
def test_runtime_evidence_requires_every_test_successfully(tmp_path, defect):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    for name in runtime.RUNTIME_TESTS:
        ET.SubElement(suite, "testcase", name=name, classname="tests.experiments.test_development")
    if defect == "missing":
        suite.remove(suite[0])
    elif defect == "duplicate":
        suite.append(suite[0])
    elif defect in {"skipped", "failure", "error"}:
        ET.SubElement(suite[0], defect)
    elif defect == "wrong_class":
        suite[0].set("classname", "fixture_only")
    path = tmp_path / "tests.xml"
    ET.ElementTree(root).write(path)
    assert runtime.runtime_tests_passed(path, int(defect == "exit_code")) is (defect is None)


def test_runtime_evidence_rejects_missing_or_malformed_xml(tmp_path):
    path = tmp_path / "tests.xml"
    assert not runtime.runtime_tests_passed(path, 0)
    path.write_text("<broken")
    assert not runtime.runtime_tests_passed(path, 0)


def test_recorded_runtime_evidence_requires_both_controls(tmp_path):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    path = tmp_path / "recorded.xml"
    for name, classname in runtime.RECORDED_TESTS.items():
        ET.SubElement(suite, "testcase", name=name, classname=classname)
    ET.ElementTree(root).write(path)
    assert runtime.runtime_tests_passed(path, 0, runtime.RECORDED_TESTS)
    assert not runtime.runtime_tests_passed(path, 0)
    suite.remove(suite[0])
    ET.ElementTree(root).write(path)
    assert not runtime.runtime_tests_passed(path, 0, runtime.RECORDED_TESTS)
