import json

from operance import project_info


def test_build_project_identity_uses_packaged_build_info(monkeypatch, tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "operance"\nversion = "9.9.9"\n',
        encoding="utf-8",
    )
    (tmp_path / "build-info.json").write_text(
        json.dumps(
            {
                "build_time": "2026-05-17T00:00:00Z",
                "entrypoint": "/usr/bin/operance",
                "git_branch": "main",
                "git_commit": "abcdef123456",
                "git_commit_short": "abcdef1",
                "git_dirty": False,
                "git_tag": "v9.9.9",
                "install_root": "/usr/lib/operance",
                "package_profile": "mvp",
                "package_version": "9.9.9",
                "python_bin": "/usr/bin/python3",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(project_info, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        project_info.importlib.metadata,
        "version",
        lambda name: (_ for _ in ()).throw(project_info.importlib.metadata.PackageNotFoundError()),
    )
    project_info.build_project_identity.cache_clear()
    project_info.project_version.cache_clear()

    identity = project_info.build_project_identity()

    assert identity["version"] == "9.9.9"
    assert identity["install_mode"] == "packaged"
    assert identity["build_git_commit"] == "abcdef123456"
    assert identity["build_git_commit_short"] == "abcdef1"
    assert identity["build_git_tag"] == "v9.9.9"
    assert identity["package_profile"] == "mvp"
    assert identity["install_root"] == "/usr/lib/operance"

    project_info.build_project_identity.cache_clear()
    project_info.project_version.cache_clear()
