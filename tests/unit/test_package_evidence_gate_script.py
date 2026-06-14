import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_package_evidence_gate.sh"


def _run_package_evidence_gate_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_package_evidence_gate_dry_run_prints_default_steps() -> None:
    result = _run_package_evidence_gate_script("--dry-run")

    assert result.stdout.splitlines() == [
        "+ ./scripts/build_package_artifacts.sh --rpm --root-dir "
        f"{REPO_ROOT / 'dist/package-artifacts'} --version 0.1.0 --bundle-profile mvp --dry-run",
        f"+ rpm -Kv {REPO_ROOT / 'dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm'}",
        "+ ./scripts/install_package_artifact.sh --package "
        f"{REPO_ROOT / 'dist/package-artifacts/rpm/operance-0.1.0-1.noarch.rpm'} "
        "--installer dnf --replace-existing --reset-user-services",
        "+ ./scripts/run_installed_desktop_smoke.sh",
        "+ operance --about",
        "+ operance --installed-smoke",
        "+ operance --public-beta-checklist",
        "+ operance --command-coach",
        "+ operance --local-ai-coach",
        "+ operance --supported-commands --supported-commands-available-only",
        "+ operance --support-bundle",
        "Manual packaged evidence checks:",
        "- Click the tray icon and say: open firefox",
        "- Click the tray icon and say: open localhost:3000",
        "- Click the tray icon and say: open firefox and notify me",
        "- Click the tray icon and say: search google for linux automation",
        "- Open the tray menu and inspect: Try commands",
        "- Open the tray menu and inspect: Local AI setup",
        "- Click the tray icon and say: let me know when this is done",
        "- Attach the installed support bundle if any check fails",
    ]
    assert result.stderr == ""


def test_package_evidence_gate_forwards_options_in_dry_run(tmp_path: Path) -> None:
    root_dir = tmp_path / "packages"
    support_bundle = tmp_path / "support.tar.gz"
    evidence_dir = tmp_path / "evidence"

    result = _run_package_evidence_gate_script(
        "--root-dir",
        str(root_dir),
        "--version",
        "2.3.4",
        "--bundle-profile",
        "base",
        "--bundle-python",
        "/tmp/python",
        "--bundle-source-site-packages",
        "/tmp/site-packages",
        "--support-bundle-out",
        str(support_bundle),
        "--evidence-dir",
        str(evidence_dir),
        "--no-sudo",
        "--no-reset-user-services",
        "--dry-run",
    )

    assert result.stdout.splitlines() == [
        "+ ./scripts/build_package_artifacts.sh --rpm --root-dir "
        f"{root_dir} --version 2.3.4 --bundle-profile base "
        "--bundle-python /tmp/python --bundle-source-site-packages /tmp/site-packages --dry-run",
        f"+ rpm -Kv {root_dir / 'rpm/operance-2.3.4-1.noarch.rpm'}",
        "+ ./scripts/install_package_artifact.sh --package "
        f"{root_dir / 'rpm/operance-2.3.4-1.noarch.rpm'} "
        "--installer dnf --replace-existing --no-sudo",
        "+ ./scripts/run_installed_desktop_smoke.sh",
        "+ operance --about",
        "+ operance --installed-smoke",
        "+ operance --public-beta-checklist",
        "+ operance --command-coach",
        "+ operance --local-ai-coach",
        "+ operance --supported-commands --supported-commands-available-only",
        f"+ operance --support-bundle --support-bundle-out {support_bundle}",
        "Manual packaged evidence checks:",
        "- Click the tray icon and say: open firefox",
        "- Click the tray icon and say: open localhost:3000",
        "- Click the tray icon and say: open firefox and notify me",
        "- Click the tray icon and say: search google for linux automation",
        "- Open the tray menu and inspect: Try commands",
        "- Open the tray menu and inspect: Local AI setup",
        "- Click the tray icon and say: let me know when this is done",
        "- Attach the installed support bundle if any check fails",
    ]
    assert result.stderr == ""


def test_package_evidence_gate_evidence_dir_defaults_support_bundle_path(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"

    result = _run_package_evidence_gate_script(
        "--evidence-dir",
        str(evidence_dir),
        "--dry-run",
    )

    assert f"+ operance --support-bundle --support-bundle-out {evidence_dir / 'operance-installed-support.tar.gz'}" in result.stdout
    assert "+ operance --command-coach" in result.stdout
    assert "+ operance --local-ai-coach" in result.stdout
