def test_real_main_delegated_lane_constructors(host_conformance):
    rows = [r for r in host_conformance["records"] if "entrypoint" in r and "damaged" in r]
    assert {r["entrypoint"] for r in rows} == {"main", "delegated", "lane"}
    assert all(r["construction_events"] and r["execution_run"]["applied_plan_id"] for r in rows)


def test_entered_permission_expansion_denials(host_conformance):
    rows = [r for r in host_conformance["records"] if r.get("control") == "permission_denial"]
    assert {r["entrypoint"] for r in rows} == {"main", "delegated", "lane"}
    assert all(r["entered"] and not r["launched"] for r in rows)


def test_independent_checks_reject_entered_routed_artifacts(host_conformance):
    records = host_conformance["records"]
    damaged = [row for row in records if row.get("damaged")]
    assert {row["task_family"] for row in damaged} == {"implementation", "review", "documentation"}
    assert all(not all(row["objective_checks"].values()) for row in damaged)
    controls = [row for row in records if row.get("control") in ("privacy_leak", "swapped_split")]
    assert {row["control"] for row in controls} == {"privacy_leak", "swapped_split"}
    assert all(not all(row["objective_checks"].values()) for row in controls)
    baselines = [row for row in records if "baseline" in row and "control" not in row]
    assert {row["baseline"] for row in baselines} == {
        "fixed_default",
        "cheapest_feasible",
        "no_optional_guidance",
    }
    assert all(all(row["objective_checks"].values()) for row in baselines)
    # Every baseline of every case, each with its measured overhead (EC-HOST-3).
    assert sorted((row["baseline"], row["case_index"]) for row in baselines) == sorted(
        (baseline, index)
        for baseline in ("fixed_default", "cheapest_feasible", "no_optional_guidance")
        for index in range(6)
    )
    bound = host_conformance["probes_watchdog_seconds"] * 1000
    for row in baselines:
        for timing in ("routing_ms", "execution_ms", "reporting_and_bridge_ms"):
            value = row[timing]
            assert isinstance(value, (int, float)) and not isinstance(value, bool)
            assert 0 <= value < bound
