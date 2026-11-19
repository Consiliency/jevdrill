from types import SimpleNamespace

import pytest

from jevdrill.contracts import ContractError
from jevdrill.integrations import development
from jevdrill.integrations.archive import maintenance_lock
from jevdrill.integrations.development import IndependentDevelopmentGrader
from jevdrill.integrations.experiments import RestrictedContainerRunner


class Container(RestrictedContainerRunner):
    def __init__(self):
        super().__init__("sha256:" + "1" * 64)
        self.results = [
            {"status": "completed", "answers": [1, 2], "inputs_unchanged": False},
            {"status": "completed", "answers": [1, 0], "inputs_unchanged": True},
        ]
        self.calls = []
        self.after = lambda: None

    def evaluate(self, source, inputs, deadline, *, run_id=None, custody_fd=None):
        self.calls.append((source, inputs, run_id, custody_fd))
        inputs.clear()
        self.after()
        return self.results.pop(0)


@pytest.fixture
def grader(tmp_path, monkeypatch):
    monkeypatch.setattr(development, "sys", SimpleNamespace(platform="linux"))
    cases = {"opaque-key": {"inputs": [[1], [2]], "expected_answers": [1, 2]}}
    container = Container()
    service = IndependentDevelopmentGrader(
        cases,
        container=container,
        lock_path=tmp_path / "worker.lock",
        duration_ms=5000,
        authorize=lambda key: key == "opaque-key",
    )
    return service, container, cases


def test_independent_answer_grades_ignore_candidate_integrity_claims(grader):
    service, container, cases = grader
    cases["opaque-key"]["expected_answers"].clear()
    assert service.grade("opaque-key", ["first", "second"]) == [
        {"quality": 1.0, "critical": {"answers_match": True}},
        {"quality": 0.5, "critical": {"answers_match": False}},
    ]
    assert len({c[2] for c in container.calls}) == 2
    assert all(c[3] is not None for c in container.calls)
    assert service.cases["opaque-key"]["inputs"] == [[1], [2]]


def test_missing_and_timeout_grades_stay_unknown(grader):
    service, container, _ = grader
    container.results = [{"status": "timeout", "answers": None}]
    assert service.grade("opaque-key", [None, "second"]) == [
        {"quality": None, "critical": {}},
        {"quality": None, "critical": {}},
    ]
    assert len(container.calls) == 1


def test_grader_cannot_run_without_authority_or_under_worker_contention(grader):
    service, container, _ = grader
    with pytest.raises(ContractError, match="policy_grading_not_authorized"):
        service.grade("other-key", ["one", "two"])
    with maintenance_lock(service.lock_path) as held:
        assert held
        with pytest.raises(ContractError, match="policy_grading_worker_busy"):
            service.grade("opaque-key", ["one", "two"])
    assert container.calls == []


def test_grader_rechecks_authority_and_releases_custody(grader):
    service, container, _ = grader
    container.after = lambda: setattr(service, "authorize", lambda _: False)
    with pytest.raises(ContractError, match="policy_grading_not_authorized"):
        service.grade("opaque-key", ["one", "two"])
    assert len(container.calls) == 1
    with maintenance_lock(service.lock_path) as acquired:
        assert acquired


def test_changed_grading_recipe_cannot_return_scores(grader):
    service, container, _ = grader
    container.after = lambda: service.cases["opaque-key"]["expected_answers"].append(99)
    with pytest.raises(ContractError, match="policy_grading_recipe_changed"):
        service.grade("opaque-key", ["one", "two"])


def test_authority_revoked_during_last_grade_discards_results(grader):
    service, container, _ = grader

    def revoke_last():
        if len(container.calls) == 2:
            service.authorize = lambda _: False

    container.after = revoke_last
    with pytest.raises(ContractError, match="policy_grading_not_authorized"):
        service.grade("opaque-key", ["one", "two"])


def test_native_macos_or_windows_requires_linux_grading_worker(grader, monkeypatch):
    service, container, _ = grader
    monkeypatch.setattr(development, "sys", SimpleNamespace(platform="darwin"))
    with pytest.raises(ContractError, match="policy_grading_linux_worker_required"):
        service.grade("opaque-key", ["one", "two"])
    assert container.calls == []


@pytest.mark.parametrize("duration", [0, -1, 120001])
def test_grading_duration_is_explicit_and_bounded(tmp_path, duration):
    with pytest.raises(ContractError, match="policy_grading_duration_invalid"):
        IndependentDevelopmentGrader(
            {},
            container=Container(),
            lock_path=tmp_path / "lock",
            duration_ms=duration,
            authorize=lambda _: True,
        )


@pytest.mark.parametrize(
    "case",
    [
        {"inputs": [], "expected_answers": []},
        {"inputs": [[1]], "expected_answers": []},
        {"inputs": [[1]], "expected_answers": [1], "extra": True},
    ],
)
def test_grading_recipes_require_matching_input_and_answer_counts(tmp_path, case):
    with pytest.raises(ContractError, match="policy_grading_case_invalid"):
        IndependentDevelopmentGrader(
            {"key": case},
            container=Container(),
            lock_path=tmp_path / "lock",
            duration_ms=5000,
            authorize=lambda _: True,
        )
