def test_every_report_connection_queries_notices(host_conformance):
    rows = [r for r in host_conformance["records"] if "connections" in r]
    assert rows
    for row in rows:
        for index, name in enumerate(row["connections"]):
            if name == "report":
                assert index > 0 and row["connections"][index - 1] == "notices"


def test_pending_notice_reaches_the_notice_sink(host_conformance):
    rows = [r for r in host_conformance["records"] if "pending_notices" in r]
    assert {r["entrypoint"] for r in rows} == {"main", "delegated", "lane"}
    for row in rows:
        assert len(row["pending_notices"]) == 1
        queries = row["connections"].count("notices")
        assert queries > 0
        # The seeded notice reaches the sink once for every notices query in this run.
        assert row["notices_delivered"].count(row["pending_notices"][0]) == queries
