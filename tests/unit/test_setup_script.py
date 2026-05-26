import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "setup.sh"


def _run_setup_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_setup_script_dry_run_guides_packaged_install(tmp_path: Path) -> None:
    package_path = tmp_path / "operance-1.2.3-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")
    bundle_path = tmp_path / "support.tar.gz"

    result = _run_setup_script(
        "--package",
        str(package_path),
        "--support-bundle-out",
        str(bundle_path),
        "--dry-run",
    )

    assert result.stderr == ""
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    assert result.stdout.splitlines() == [
        "+ systemctl --user disable --now operance-tray.service",
        f"+ rm -f {unit_dir / 'operance-tray.service'}",
        "+ systemctl --user disable --now operance-voice-loop.service",
        f"+ rm -f {unit_dir / 'operance-voice-loop.service'}",
        "+ systemctl --user daemon-reload",
        "+ sudo dnf remove -y operance",
        f"+ sudo dnf install -y {package_path}",
        "+ systemctl --user enable --now operance-tray.service",
        "+ operance --installed-smoke",
        "+ operance --supported-commands --supported-commands-available-only",
        f"+ operance --support-bundle --support-bundle-out {bundle_path}",
        "Manual click-to-talk checks:",
        "- Click the tray icon and say: open browser",
        "- Click the tray icon and say: open google.com",
        "- Click the tray icon and say: open firefox",
        "- Click the tray icon and say: open firefox and notify me",
        "- Click the tray icon and say: what time is it",
        "If anything fails:",
        "- Run: operance --issue-report",
        "- Attach the support bundle to a GitHub issue.",
    ]


def test_setup_script_dry_run_supports_no_sudo(tmp_path: Path) -> None:
    package_path = tmp_path / "operance-1.2.3-1.noarch.rpm"
    package_path.write_text("rpm", encoding="utf-8")

    result = _run_setup_script(
        "--package",
        str(package_path),
        "--no-sudo",
        "--dry-run",
    )

    assert result.stderr == ""
    assert (
        f"+ dnf install -y {package_path}"
        in result.stdout.splitlines()
    )


def test_setup_script_is_standalone_release_asset() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "install_package_artifact.sh" not in script


def test_user_facing_script_names_do_not_encode_release_phase() -> None:
    forbidden_terms = ("alpha", "beta")
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "scripts").iterdir()
        if path.is_file() and any(term in path.name.lower() for term in forbidden_terms)
    ]

    assert offenders == []
