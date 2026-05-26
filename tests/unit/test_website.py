from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_INDEX = REPO_ROOT / "site" / "index.html"
SITE_STYLES = REPO_ROOT / "site" / "styles.css"
GITHUB_DOC_BASE = "https://github.com/raunakkathuria/operance/blob/main/"


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: set[str] = set()
        self.link_attrs: dict[str, dict[str, str]] = {}
        self.images: set[str] = set()
        self.stylesheets: set[str] = set()
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value for key, value in attrs if value is not None}
        if value := values.get("id"):
            self.ids.add(value)
        if tag == "a" and (href := values.get("href")):
            self.links.add(href)
            self.link_attrs[href] = values
        if tag == "img" and (src := values.get("src")):
            self.images.add(src)
        if tag == "link" and values.get("rel") == "stylesheet" and (href := values.get("href")):
            self.stylesheets.add(href)

    def handle_data(self, data: str) -> None:
        if stripped := data.strip():
            self.text_parts.append(stripped)

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.text_parts))


def _parse_site() -> SiteParser:
    parser = SiteParser()
    parser.feed(SITE_INDEX.read_text(encoding="utf-8"))
    return parser


def test_static_website_reuses_operance_brand_asset_and_palette() -> None:
    parser = _parse_site()
    styles = SITE_STYLES.read_text(encoding="utf-8")

    assert "../assets/icons/operance.svg" in parser.images
    assert "styles.css" in parser.stylesheets
    assert "#14b8a6" in styles
    assert "#0f766e" in styles
    assert "#111827" in styles


def test_static_website_is_product_first_and_mentions_current_scope() -> None:
    parser = _parse_site()
    text = parser.text

    assert "Turn intent into safe desktop action." in text
    assert "local-first ai desktop action layer" in text.lower()
    assert "Fedora KDE Plasma Wayland first" in text
    assert "Windows and macOS are architecture targets" in text
    assert "No raw shell commands. No model required." in text
    assert "local-first desktop action runtime" not in text.lower()


def test_static_website_has_demo_and_beta_install_path() -> None:
    parser = _parse_site()
    text = parser.text

    assert {"top", "demo", "try", "developers"} <= parser.ids
    assert "open browser" in text
    assert "apps.launch" in text
    assert "bash ./setup.sh --package ./operance-0.1.0-1.noarch.rpm" in text
    assert "operance --installed-smoke" in text
    assert "operance --supported-commands --supported-commands-available-only" in text


def test_developer_section_links_to_existing_markdown_docs() -> None:
    parser = _parse_site()

    expected_links = {
        f"{GITHUB_DOC_BASE}README.md",
        f"{GITHUB_DOC_BASE}docs/release/public-beta.md",
        f"{GITHUB_DOC_BASE}docs/architecture/overview.md",
        f"{GITHUB_DOC_BASE}docs/architecture/adapter-authoring.md",
        f"{GITHUB_DOC_BASE}docs/contributing/command-authoring.md",
        f"{GITHUB_DOC_BASE}docs/requirements/linux.md",
        f"{GITHUB_DOC_BASE}CONTRIBUTING.md",
    }

    assert expected_links <= parser.links
    for href in expected_links:
        repo_path = href.removeprefix(GITHUB_DOC_BASE)
        assert href != repo_path
        assert (REPO_ROOT / repo_path).exists()

    assert not any(href.startswith("../") and href.endswith(".md") for href in parser.links)


def test_github_links_open_in_new_tabs_safely() -> None:
    parser = _parse_site()

    github_links = [href for href in parser.links if href.startswith("https://github.com/")]
    assert github_links
    for href in github_links:
        attrs = parser.link_attrs[href]
        assert attrs["target"] == "_blank"
        rel_tokens = set(attrs["rel"].split())
        assert {"noopener", "noreferrer"} <= rel_tokens
