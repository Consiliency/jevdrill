from jevdrill.context import collect_context


def test_excluded_and_unauthorized_attachments_are_not_collected():
    result = collect_context(
        "synthetic task",
        [
            {"reference": "/private/secret.txt", "authorized": True},
            {"reference": "/allowed/note.txt", "authorized": False},
            {"reference": "/allowed/image.png", "authorized": True, "modality": "image"},
        ],
        ["/private/secret.txt"],
    )
    assert result["attachments"] == [
        {"reference": "/allowed/image.png", "authorized": True, "modality": "image"}
    ]
