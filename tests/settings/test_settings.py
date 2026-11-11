from jevdrill.settings import effective_permissions, resolve_settings


def test_settings_keep_winning_sources_and_intersect_permissions():
    settings = resolve_settings(
        [("product", {"routing_deadline_ms": 5000}), ("project", {"routing_deadline_ms": 1000})]
    )
    assert settings["routing_deadline_ms"] == 1000
    assert settings["setting_sources"]["routing_deadline_ms"] == "project"
    assert effective_permissions(["route", "report"], ["report", "inspect"]) == ["report"]


def test_layer_order_is_declared_and_restrictions_cannot_be_widened():
    layers = [
        ("request", {"retain_raw_tasks": True, "excluded_paths": ["/b"]}),
        ("product", {"retain_raw_tasks": False, "excluded_paths": ["/a"]}),
    ]
    result = resolve_settings(layers)
    assert not result["retain_raw_tasks"]
    assert result["excluded_paths"] == ["/a", "/b"]
    assert result == resolve_settings(list(reversed(layers)))
