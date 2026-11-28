"""Item 3: explicit reports through the run-bound hook enter the run's one queue (HOST SL-7).

The probe `test_explicit_reports_share_the_run_queue` writes the record; every assertion is
here. Rows are what a separate process read from the queue's file, matched by each report's
content; the hook's answers and counts are compared with them and never replace them.
"""

IDENTITY = ("execution_run_id", "task_id", "routing_decision_id")


def explicit_record(host_conformance):
    (record,) = [
        row["explicit_reports"] for row in host_conformance["records"] if "explicit_reports" in row
    ]
    return record


def started_row(rows, run_id):
    (row,) = [r for r in rows if r["execution_run_id"] == run_id and r["event_type"] == "started"]
    return row


def test_accepted_report_is_queued_in_sequence_and_counted(host_conformance):
    record = explicit_record(host_conformance)
    rows, runs = record["first_read"]["rows"], record["runs"]
    assert record["first_read"]["host_importable"] is False
    assert record["active"] == {"A": [runs["A"]], "B": [runs["B"]]}
    assert len(rows) == record["status_first"]["records"]
    assert [report["label"] for report in record["sent"]] == ["E1", "E2", "E3", "E4"]
    labels = {}
    for report in record["sent"]:
        assert report["answer"] == "queued"
        (row,) = [r for r in rows if r["content"] == report["content"]]
        labels[report["content"]] = report["label"]
        assert row["source_sequence"] == report["sequence_before"]
        before, after = report["counts_before"], report["counts_after"]
        assert after["queued"] == before["queued"] + 1
        assert after["losses"] == before["losses"]
    for run_id in runs.values():
        sequences = [r["source_sequence"] for r in rows if r["execution_run_id"] == run_id]
        assert len(sequences) == len(set(sequences))
    started = started_row(rows, runs["A"])
    of_a = sorted(
        (r for r in rows if r["execution_run_id"] == runs["A"]),
        key=lambda r: r["source_sequence"],
    )
    assert all(r["source_id"] == started["source_id"] for r in of_a if r["content"])
    order = [
        "started" if r is started else labels.get(r["content"], "host" if not r["content"] else "?")
        for r in of_a
    ]
    hosts = len(order) - 4
    assert hosts >= 0 and order == ["started", "E1", *["host"] * hosts, "E2", "E3"]


def test_report_stays_with_its_run(host_conformance):
    """Security (a): a report sent under a returned run while another is active stays with it."""
    record = explicit_record(host_conformance)
    rows, runs = record["first_read"]["rows"], record["runs"]
    started = {name: started_row(rows, run_id) for name, run_id in runs.items()}
    assert all(started["A"][key] != started["B"][key] for key in IDENTITY)
    contents = {"A": set(), "B": set()}
    for report in record["sent"]:
        name = "B" if report["label"] == "E4" else "A"
        assert report["run"] == runs[name]
        contents[name].add(report["content"])
        matching = [r for r in rows if r["content"] == report["content"]]
        assert matching
        assert all(r[key] == started[name][key] for r in matching for key in IDENTITY)
        before, after = report["other_sequences"]
        assert before == after
    assert [len(report["other_sequences"][0]) for report in record["sent"]] == [0, 0, 1, 1]
    for name, other in (("A", "B"), ("B", "A")):
        stored = {r["content"] for r in rows if r["execution_run_id"] == runs[other]}
        assert not contents[name] & stored


def test_loss_is_counted(host_conformance):
    record = explicit_record(host_conformance)
    first, second = record["first_read"]["rows"], record["second_read"]["rows"]
    task = record["deleted_task"]
    assert task == started_row(first, record["runs"]["A"])["task_id"]
    removed = [r for r in first if r["task_id"] == task]
    assert len([r for r in removed if r["content"]]) == 3

    def deleted(status):
        return status["dispositions"].get("deleted", 0)

    assert deleted(record["status_second"]) - deleted(record["status_first"]) == len(removed)
    assert not [r for r in second if r["task_id"] == task]
    kept = [r for r in first if r["task_id"] != task]
    assert kept and all(r in second for r in kept)
    assert len(second) == record["status_second"]["records"]
