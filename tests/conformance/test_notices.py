def test_every_report_connection_queries_notices(host_conformance):
    rows = [r for r in host_conformance["records"] if "connections" in r]
    assert rows
    for row in rows:
        for index, name in enumerate(row["connections"]):
            if name == "report":
                assert index > 0 and row["connections"][index - 1] == "notices"
