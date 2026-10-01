from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parents[1]
APP = str(ROOT / "app.py")
PAGES = [
    "pages/welcome.py",
    "pages/data.py",
    "pages/icp.py",
    "pages/market.py",
    "pages/shortlist.py",
    "pages/company.py",
    "pages/export.py",
    "pages/about.py",
]


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PROSPECTSIGNAL_DATA_DIR", str(tmp_path))
    from pages import _ui

    _ui._open_store.clear()
    yield
    _ui._open_store.clear()


def _text(app: AppTest) -> str:
    parts = [str(item.value) for item in app.markdown] + [str(item.value) for item in app.caption]
    parts += [str(item.value) for item in app.info] + [str(item.value) for item in app.warning]
    return "\n".join(parts)


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_with_offline_demo(page):
    app = AppTest.from_file(APP, default_timeout=120)
    app.run()
    app.switch_page(page).run()
    assert not app.exception, [error.value for error in app.exception]
    assert not app.error, [error.value for error in app.error]


def test_demo_icp_shows_matches_and_consent_note():
    app = AppTest.from_file(APP, default_timeout=120)
    app.run()
    app.switch_page("pages/icp.py").run()
    matches = next(metric for metric in app.metric if metric.label == "Matching units")
    assert int(matches.value.replace(",", "")) > 0
    assert "never implies marketing consent" in _text(app)


def test_shortlist_and_export_flow():
    app = AppTest.from_file(APP, default_timeout=120)
    app.run()
    app.switch_page("pages/icp.py").run()
    next(button for button in app.button if button.label.startswith("Add the top")).click().run()
    assert not app.exception

    app.switch_page("pages/shortlist.py").run()
    assert not app.exception
    assert "never implies marketing consent" in _text(app)

    app.switch_page("pages/export.py").run()
    assert not app.exception
    text = _text(app)
    assert "Not legal advice" in text
    assert "never implies marketing consent" in text
    checkbox = next(box for box in app.checkbox if box.label.startswith("I have read the outreach checklist"))
    assert checkbox.value is False
    checkbox.check().run()
    assert not app.exception


def test_real_register_not_loaded_is_explained():
    app = AppTest.from_file(APP, default_timeout=120)
    app.session_state["dataset"] = "register"
    app.run()
    app.switch_page("pages/icp.py").run()
    assert not app.exception
    assert any("not loaded" in str(info.value) for info in app.info)
