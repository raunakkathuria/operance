from __future__ import annotations

import ast
from pathlib import Path


PORTABLE_CORE_PATHS = (
    "src/operance/models",
    "src/operance/intent",
    "src/operance/planner",
    "src/operance/runtime",
    "src/operance/mcp",
    "src/operance/voice",
    "src/operance/policy.py",
    "src/operance/validator.py",
    "src/operance/executor.py",
    "src/operance/daemon.py",
    "src/operance/registry.py",
    "src/operance/supported_commands.py",
)

FORBIDDEN_CONCRETE_ADAPTER_IMPORTS = {
    "operance.adapters.linux",
    "operance.adapters.windows",
    "operance.adapters.macos",
    "operance.adapters.darwin",
}


def test_shared_doctor_does_not_own_linux_host_probes() -> None:
    root = Path(__file__).resolve().parents[2]
    doctor_source = (root / "src" / "operance" / "doctor.py").read_text(encoding="utf-8")

    assert "_probe_wayland_session_access" not in doctor_source
    assert "_probe_text_input_backend" not in doctor_source
    assert "_probe_systemctl_user_service_state" not in doctor_source
    assert "_user_service_candidate_paths" not in doctor_source


def test_shared_setup_metadata_does_not_own_linux_host_checks() -> None:
    root = Path(__file__).resolve().parents[2]
    setup_source = (root / "src" / "operance" / "ui" / "setup.py").read_text(encoding="utf-8")

    assert '"kde_wayland_target"' not in setup_source
    assert '"wayland_session_accessible"' not in setup_source
    assert '"systemctl_user_available"' not in setup_source
    assert '"voice_loop_user_service_installed"' not in setup_source


def test_portable_core_does_not_import_concrete_os_adapters() -> None:
    root = Path(__file__).resolve().parents[2]
    offenders: list[str] = []

    for relative_path in PORTABLE_CORE_PATHS:
        path = root / relative_path
        source_files = [path] if path.is_file() else sorted(path.rglob("*.py"))
        for source_file in source_files:
            tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
            for node in ast.walk(tree):
                imported_module = _imported_module_name(node)
                if imported_module in FORBIDDEN_CONCRETE_ADAPTER_IMPORTS:
                    offenders.append(f"{source_file.relative_to(root)}:{node.lineno} imports {imported_module}")

    assert offenders == []


def _imported_module_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        return next(
            (
                alias.name
                for alias in node.names
                if alias.name in FORBIDDEN_CONCRETE_ADAPTER_IMPORTS
            ),
            None,
        )
    if isinstance(node, ast.ImportFrom) and node.module:
        return node.module
    return None
