from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_shared_doctor_does_not_own_linux_host_probes() -> None:
    doctor_source = (REPO_ROOT / "src" / "operance" / "doctor.py").read_text(encoding="utf-8")

    assert "_probe_wayland_session_access" not in doctor_source
    assert "_probe_text_input_backend" not in doctor_source
    assert "_probe_systemctl_user_service_state" not in doctor_source
    assert "_user_service_candidate_paths" not in doctor_source


def test_shared_setup_metadata_does_not_own_linux_host_checks() -> None:
    setup_source = (REPO_ROOT / "src" / "operance" / "ui" / "setup.py").read_text(encoding="utf-8")

    assert '"kde_wayland_target"' not in setup_source
    assert '"wayland_session_accessible"' not in setup_source
    assert '"systemctl_user_available"' not in setup_source
    assert '"voice_loop_user_service_installed"' not in setup_source
