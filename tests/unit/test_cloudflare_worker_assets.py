from __future__ import annotations

from pathlib import Path
import tomllib


REPO_ROOT = Path(__file__).resolve().parents[2]
WRANGLER_CONFIG = REPO_ROOT / "wrangler.toml"


def test_cloudflare_worker_static_assets_config_is_asset_only() -> None:
    config = tomllib.loads(WRANGLER_CONFIG.read_text(encoding="utf-8"))

    assert config["name"] == "operance"
    assert config["compatibility_date"] == "2026-06-02"
    assert config["assets"]["directory"] == "./dist/pages"
    assert "main" not in config
    assert "binding" not in config["assets"]
    assert not (REPO_ROOT / "worker.js").exists()
