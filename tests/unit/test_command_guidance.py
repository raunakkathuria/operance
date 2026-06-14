from operance.command_guidance import COMMAND_RECOVERY_EXAMPLES, unmatched_command_response, unmatched_spoken_response


def test_unmatched_command_response_gives_safe_user_examples() -> None:
    response = unmatched_command_response()

    assert response.startswith("I did not understand that command yet. Try: ")
    assert "open browser" in response
    assert "open google.com" in response
    assert "search google for linux automation" in response
    assert "what time is it" in response
    assert "install updates" not in response
    assert COMMAND_RECOVERY_EXAMPLES == (
        "open browser",
        "open google.com",
        "search google for linux automation",
        "what time is it",
    )


def test_unmatched_spoken_response_stays_short() -> None:
    assert unmatched_spoken_response() == (
        "Sorry, I did not understand that yet. Try open browser or what time is it."
    )
