from operance.release_channel import build_release_update_status


def test_build_release_update_status_reports_current_packaged_release() -> None:
    status = build_release_update_status(
        identity={
            "install_mode": "packaged",
            "build_git_tag": "v0.1.0-beta.4",
            "build_git_commit_short": "c748396",
            "package_version": "0.1.0",
        },
        check_remote=False,
    )

    assert status == {
        "channel": "prerelease",
        "check_remote": False,
        "installed_commit": "c748396",
        "installed_tag": "v0.1.0-beta.4",
        "install_mode": "packaged",
        "latest_tag": None,
        "message": "Remote release check was not requested.",
        "release_url": None,
        "repository": "raunakkathuria/operance",
        "status": "unknown",
        "suggested_command": "operance --check-updates",
        "update_available": None,
    }


def test_build_release_update_status_detects_newer_prerelease() -> None:
    status = build_release_update_status(
        identity={
            "install_mode": "packaged",
            "build_git_tag": "v0.1.0-beta.4",
            "build_git_commit_short": "c748396",
        },
        fetch_latest_release=lambda repo, channel, timeout_seconds: {
            "tag_name": "v0.1.0-beta.5",
            "html_url": "https://github.example/releases/v0.1.0-beta.5",
            "prerelease": True,
        },
    )

    assert status["status"] == "ok"
    assert status["channel"] == "prerelease"
    assert status["latest_tag"] == "v0.1.0-beta.5"
    assert status["update_available"] is True
    assert status["release_url"] == "https://github.example/releases/v0.1.0-beta.5"
    assert status["message"] == "Update available: v0.1.0-beta.5."
    assert status["suggested_command"] == (
        "Download and install the latest RPM from https://github.example/releases/v0.1.0-beta.5"
    )


def test_build_release_update_status_handles_current_release() -> None:
    status = build_release_update_status(
        identity={"install_mode": "packaged", "build_git_tag": "v0.1.0-beta.5"},
        fetch_latest_release=lambda repo, channel, timeout_seconds: {
            "tag_name": "v0.1.0-beta.5",
            "html_url": "https://github.example/releases/v0.1.0-beta.5",
        },
    )

    assert status["status"] == "ok"
    assert status["update_available"] is False
    assert status["message"] == "Installed release is current for the prerelease channel."
    assert status["suggested_command"] is None


def test_build_release_update_status_reports_source_checkout_scope() -> None:
    status = build_release_update_status(
        identity={"install_mode": "source_checkout", "git_commit": "abc1234"},
        fetch_latest_release=lambda repo, channel, timeout_seconds: {
            "tag_name": "v0.1.0-beta.5",
            "html_url": "https://github.example/releases/v0.1.0-beta.5",
        },
    )

    assert status["status"] == "ok"
    assert status["install_mode"] == "source_checkout"
    assert status["update_available"] is None
    assert status["message"] == "Latest prerelease release is v0.1.0-beta.5; source checkouts should update through git."
    assert status["suggested_command"] == "git pull --ff-only"


def test_build_release_update_status_reports_fetch_failure() -> None:
    def _raise(_repo: str, _channel: str, _timeout_seconds: float) -> dict[str, object]:
        raise RuntimeError("network unavailable")

    status = build_release_update_status(
        identity={"install_mode": "packaged", "build_git_tag": "v0.1.0-beta.5"},
        fetch_latest_release=_raise,
    )

    assert status["status"] == "failed"
    assert status["update_available"] is None
    assert status["message"] == "Could not check GitHub releases: network unavailable"
    assert status["suggested_command"] == "Retry operance --check-updates when network access is available."
