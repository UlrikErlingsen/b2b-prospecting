"""The Signal brand: shared theme, display name, synced config and assets, README in the suite template."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from prospectsignal import __version__

ROOT = Path(__file__).parents[1]
APP = str(ROOT / "app.py")
UI = ROOT / "src" / "prospectsignal" / "ui"
OLD_COLOURS = ("#173c3a", "#d95b40", "#83d2b4", "#f2c66d", "#17322e", "#102c2a", "#eef2eb")


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PROSPECTSIGNAL_DATA_DIR", str(tmp_path))
    from prospectsignal.ui import common

    common._open_store.clear()
    yield
    common._open_store.clear()


def test_shell_renders_the_shared_signal_masthead_sidebar_and_footer():
    app = AppTest.from_file(APP, default_timeout=120)
    app.run()
    assert not app.exception, [error.value for error in app.exception]
    body = "\n".join(str(item.value) for item in app.markdown)
    sidebar = "\n".join(str(item.value) for item in app.sidebar.markdown)
    assert "sg-mast" in body and "sg-foot" in body and "sg-hero" in body
    assert "FILTER → SIZE → SHORTLIST → EXPORT" in body
    assert f"Prospect Signal v{__version__}" in body
    assert "Registry data is not marketing consent" in body
    assert "Part of the Signal suite" in body
    assert "sg-side" in sidebar
    assert "Norwegian B2B prospecting from open register data." in sidebar
    assert "ProspectSignal" not in body + sidebar


def test_app_and_pages_use_signal_theme_instead_of_pasted_styles():
    standalone = (ROOT / "app.py").read_text(encoding="utf-8")
    # Page code lives in the ui package (shared with Signal Hub); pages/ only holds thin wrappers.
    ui_sources = [UI / "app.py", UI / "common.py", *sorted((UI / "pages").glob("*.py"))]
    pages = "".join(path.read_text(encoding="utf-8") for path in [*sorted((ROOT / "pages").glob("*.py")), *ui_sources])
    charts = (ROOT / "src" / "prospectsignal" / "market.py").read_text(encoding="utf-8")
    assert "st.set_page_config(**sig.page_config(NS))" in standalone
    assert "sig.apply(NS)" in pages
    assert 'NS = "prospect"' in pages and "KEY = NS" in pages
    assert "from prospectsignal.ui import signal_theme as sig" in pages
    assert "sig.chart(ui.KEY," in pages  # per-app template and theme=None on every market figure
    assert "st.plotly_chart" not in standalone + pages
    assert "<style>" not in standalone + pages
    assert "ps-" not in standalone + pages  # old CSS classes are gone
    for old_colour in OLD_COLOURS:
        assert old_colour not in (standalone + pages + charts).lower(), old_colour
    assert (UI / "__init__.py").exists()
    assert (UI / "assets" / "marks" / "prospectsignal-mark-64.png").exists()


def test_synced_config_uses_the_market_family_colour():
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert 'primaryColor = "#728157"' in config  # Signal Market family, 600 step
    assert "gatherUsageStats = false" in config


def test_pyproject_ships_the_theme_marks():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"prospectsignal.ui" = ["assets/marks/*"]' in pyproject
    assert 'description = "Prospect Signal:' in pyproject


def test_readme_follows_the_signal_template():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    sections = [
        "## Read this first",
        "## Scope",
        "## Try the demo in three minutes",
        "## Data contract",
        "## Analysis contract",
        "## Methods",
        "## Decision statuses",
        "## Exports",
        "## Run locally",
        "## Privacy",
        "## Development",
        "## Where this fits in Signal",
        "## References",
        "## Originality and license",
    ]
    positions = [readme.find(f"\n{heading}\n") for heading in sections]
    assert all(position >= 0 for position in positions), dict(zip(sections, positions))
    assert positions == sorted(positions)
    assert readme.startswith('<p align="center">\n  <img src="assets/prospectsignal-banner.png"')
    assert "banner.svg" not in readme
    assert "Signal-Market-728157" in readme  # family badge in the Market 600 colour
    assert "github.com/UlrikErlingsen/b2b-prospecting/actions" in readme
    assert "**Prospect Signal**" in readme
    assert '<img src="assets/prospectsignal-mark-64.png"' in readme  # suite footer
    assert "Creator Signal" not in readme and "CreatorSignal" not in readme
    # Boundaries and honesty statements survive the restructure.
    assert "companies, never people" in readme
    assert "Registry data never implies marketing consent." in readme
    assert "has not been screened for trademarks" in readme
    assert "not legal advice" in readme
    for path in ("assets/prospectsignal-banner.png", "assets/prospectsignal-mark-64.png", "assets/prospectsignal-social.png"):
        assert (ROOT / path).exists(), path
    assert not (ROOT / "assets" / "prospectsignal-banner.svg").exists()


def test_issue_templates_name_the_product_and_keep_data_safety():
    templates = ROOT / ".github" / "ISSUE_TEMPLATE"
    bug = (templates / "bug_report.yml").read_text(encoding="utf-8")
    feature = (templates / "feature_request.yml").read_text(encoding="utf-8")
    config = (templates / "config.yml").read_text(encoding="utf-8")
    assert "Prospect Signal" in bug and "Prospect Signal" in feature
    assert "Never attach real customer data" in bug
    assert "github.com/UlrikErlingsen/b2b-prospecting/blob/main/SECURITY.md" in config
    assert (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").exists()
