def test_installed_discovery_harness_planning_two_independent_tasks(host_conformance):
    rows = [r for r in host_conformance["records"] if r.get("flow") == "discovery"]
    assert {r["objective"] for r in rows} == {"alpha", "beta"}
    for row in rows:
        assert {"main", "open_application", "discover", "next_question", "route"} <= set(
            row["entered"]
        )
        events = row["construction_events"]
        assert events.index("planning.executor") < next(
            index for index, event in enumerate(events) if event.endswith("route-v2")
        )
        assert len(row["runs"]) >= 2
        assert len({run["task_id"] for run in row["runs"]}) == len(row["runs"])
        assert len({run["model"] for run in row["runs"]}) > 1
        assert len({run["effort"] for run in row["runs"]}) > 1
        assert all(run["execution_run"]["applied_plan_id"] for run in row["runs"])
        assert len({run["discovery_ref"]["discovery_id"] for run in row["runs"]}) == 1


def test_entered_reference_deletion_revision_and_policy_controls(host_conformance):
    rows = [r for r in host_conformance["records"] if r.get("flow") == "discovery-control"]
    assert {r["fault"] for r in rows} == {
        "forged",
        "deleted",
        "stale_catalog",
        "relaxed",
        "decline",
    }
    assert all(r["discovery_id"] and r["task_id"] and r["rejected_before_execution"] for r in rows)
    assert any(
        row["id"].endswith("test_entered_discovery_requires_harness_decomposition")
        and row["outcome"] == "passed"
        for row in host_conformance["assertions"]
    )
