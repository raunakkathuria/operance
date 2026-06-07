import pytest


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"status": "success", "text": "Opened default browser"}, "Opened default browser"),
        ({"status": "no_transcript", "text": "I did not catch a command."}, "Sorry, I did not hear that."),
        (
            {"status": "unmatched", "text": "I did not understand that command."},
            "Sorry, I do not know how to do that yet.",
        ),
        (
            {"status": "awaiting_confirmation", "text": "Command requires confirmation."},
            "Please confirm before I continue.",
        ),
        ({"status": "failed", "text": "gtk-launch failed"}, "Sorry, gtk-launch failed"),
        ({"status": "denied", "text": ""}, "Sorry, that did not work."),
    ],
)
def test_build_spoken_response_text_formats_short_assistant_replies(
    response: dict[str, object],
    expected: str,
) -> None:
    from operance.spoken_response import build_spoken_response_text

    assert build_spoken_response_text(response) == expected


def test_build_spoken_response_text_shortens_long_multiline_replies() -> None:
    from operance.spoken_response import build_spoken_response_text

    response = {
        "status": "success",
        "text": f"{'x' * 140}\nsecond line",
    }

    spoken = build_spoken_response_text(response)

    assert spoken == f"{'x' * 117}..."
