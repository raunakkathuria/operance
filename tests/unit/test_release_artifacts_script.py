import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_release_artifacts.sh"


def _run_release_artifacts_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        check=True,
        cwd=REPO_ROOT,
        text=True,
    )


def test_release_artifacts_dry_run_prints_default_steps() -> None:
    result = _run_release_artifacts_script("--dry-run")

    root_dir = REPO_ROOT / "dist/package-artifacts"
    output_dir = REPO_ROOT / "dist/release"
    rpm_path = root_dir / "rpm/operance-0.1.0-1.noarch.rpm"
    public_rpm_path = output_dir / "operance-0.1.0-1.noarch.rpm"
    checksums_path = output_dir / "SHA256SUMS"
    manifest_path = output_dir / "release-artifacts-manifest.json"

    assert result.stdout.splitlines() == [
        "+ ./scripts/build_package_artifacts.sh --rpm --root-dir "
        f"{root_dir} --version 0.1.0 --bundle-profile mvp --bundle-python .venv/bin/python --dry-run",
        f"+ rpm -Kv {rpm_path}",
        f"+ mkdir -p {output_dir}",
        f"+ cp {rpm_path} {public_rpm_path}",
        f"+ cd {output_dir} && sha256sum operance-0.1.0-1.noarch.rpm > SHA256SUMS",
        f"+ render release artifact manifest -> {manifest_path}",
        "Release artifacts:",
        f"- {public_rpm_path}",
        f"- {checksums_path}",
        f"- {manifest_path}",
    ]
    assert result.stderr == ""


def test_release_artifacts_forwards_options_in_dry_run(tmp_path: Path) -> None:
    root_dir = tmp_path / "packages"
    output_dir = tmp_path / "public"

    result = _run_release_artifacts_script(
        "--root-dir",
        str(root_dir),
        "--output-dir",
        str(output_dir),
        "--version",
        "2.3.4",
        "--bundle-python",
        "/tmp/python",
        "--bundle-source-site-packages",
        "/tmp/site-packages",
        "--dry-run",
    )

    rpm_path = root_dir / "rpm/operance-2.3.4-1.noarch.rpm"
    public_rpm_path = output_dir / "operance-2.3.4-1.noarch.rpm"
    checksums_path = output_dir / "SHA256SUMS"
    manifest_path = output_dir / "release-artifacts-manifest.json"

    assert result.stdout.splitlines() == [
        "+ ./scripts/build_package_artifacts.sh --rpm --root-dir "
        f"{root_dir} --version 2.3.4 --bundle-profile mvp --bundle-python /tmp/python "
        "--bundle-source-site-packages /tmp/site-packages --dry-run",
        f"+ rpm -Kv {rpm_path}",
        f"+ mkdir -p {output_dir}",
        f"+ cp {rpm_path} {public_rpm_path}",
        f"+ cd {output_dir} && sha256sum operance-2.3.4-1.noarch.rpm > SHA256SUMS",
        f"+ render release artifact manifest -> {manifest_path}",
        "Release artifacts:",
        f"- {public_rpm_path}",
        f"- {checksums_path}",
        f"- {manifest_path}",
    ]
    assert result.stderr == ""
