def test_entered_ack_loss_and_cross_producer_deletion(host_conformance):
    rows = [r for r in host_conformance["records"] if "delivery_events" in r]
    assert rows
    for row in rows:
        events = row["delivery_events"]
        assert any(e["status"] == "duplicate" and e["durable"] for e in events)
        assert len({e["event_id"] for e in events}) == row["durable_events"]
        assert row["restart_enqueue_status"] == "deleted"
