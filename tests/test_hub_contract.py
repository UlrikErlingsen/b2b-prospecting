"""Signal Hub contract: importable UI entry point, Streamlit only under ui/, slug-namespaced state, and hub mode
(SIGNAL_HUB=1): in-memory demo per session, no files written, no network calls."""

from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import urllib.request

import duckdb
import pytest
from streamlit.testing.v1 import AppTest

from prospectsignal import __version__, brreg
from prospectsignal.storage import Store, assert_no_person_columns

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "src" / "prospectsignal"
UI = PACKAGE / "ui"
CORE_MODULES = (
    "prospectsignal", "prospectsignal.brreg", "prospectsignal.checklist", "prospectsignal.demo",
    "prospectsignal.errors", "prospectsignal.export", "prospectsignal.http", "prospectsignal.icp",
    "prospectsignal.market", "prospectsignal.nace", "prospectsignal.orgnr", "prospectsignal.regions",
    "prospectsignal.schema", "prospectsignal.shortlist", "prospectsignal.storage",
)
# Every Streamlit call that creates a stateful widget (or a keyed chart) must pass an explicit key.
KEYED_CALLS = {
    "button", "checkbox", "data_editor", "date_input", "download_button", "file_uploader", "form",
    "form_submit_button", "multiselect", "number_input", "chart", "plotly_chart", "radio", "selectbox", "slider",
    "text_input", "toggle",
}
PAGES = [
    "Welcome",
    "Data & register",
    "1 · ICP filters",
    "2 · Market size",
    "3 · Shortlist",
    "Company card",
    "4 · Export",
    "Sources & boundaries",
]
RENDER_SCRIPT = """
from prospectsignal.ui import render

render()
"""
HUB_ENV_DIRS = ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME")


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _ui_sources() -> list[Path]:
    return [path for path in UI.rglob("*.py") if path.name not in {"signal_theme.py", "signal_font.py"}]


def _page_radio(app: AppTest):
    return next(radio for radio in app.sidebar.radio if radio.key == "prospect:page")


def _text(app: AppTest) -> str:
    parts = [str(item.value) for item in app.markdown] + [str(item.value) for item in app.caption]
    parts += [str(item.value) for item in app.info] + [str(item.value) for item in app.warning]
    return "\n".join(parts)


def _shortlist_top(app: AppTest) -> None:
    _page_radio(app).set_value("1 · ICP filters").run()
    next(button for button in app.button if button.key == "prospect:add_top").click().run()
    assert not app.exception, [error.value for error in app.exception]


@pytest.fixture
def standalone_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PROSPECTSIGNAL_DATA_DIR", str(tmp_path / "standalone-data"))
    from prospectsignal.ui import common

    common._open_store.clear()
    yield tmp_path / "standalone-data"
    common._open_store.clear()


# -- contract -------------------------------------------------------------------------------------------------


def test_ui_entry_point_matches_the_hub_contract() -> None:
    from prospectsignal.ui import APP_INFO, render

    assert callable(render)
    assert APP_INFO == {
        "product": "Prospect Signal",
        "version": __version__,
        "repo": "b2b-prospecting",
        "slug": "prospect",
    }


def test_only_the_ui_package_imports_streamlit() -> None:
    # plotly stays a core dependency here: prospectsignal.market builds the figures without Streamlit.
    offenders = [
        str(path.relative_to(PACKAGE))
        for path in PACKAGE.rglob("*.py")
        if UI not in path.parents and "streamlit" in _imported_roots(path)
    ]
    assert not offenders, offenders


def test_core_package_imports_without_streamlit() -> None:
    # A fresh interpreter, so modules already imported by other tests cannot hide a stray import.
    code = (
        f"import sys\nsys.path.insert(0, {str(ROOT / 'src')!r})\n"
        f"import importlib\nfor name in {CORE_MODULES!r}:\n    importlib.import_module(name)\n"
        "loaded = sorted(name for name in ('streamlit', 'prospectsignal.ui') if name in sys.modules)\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr


def test_page_code_ships_in_the_package_and_pages_dir_only_wraps_it() -> None:
    for slug in ("welcome", "data", "icp", "market", "shortlist", "company", "export", "about"):
        assert (UI / "pages" / f"{slug}.py").exists(), slug
        wrapper = (ROOT / "pages" / f"{slug}.py").read_text(encoding="utf-8")
        assert f"from prospectsignal.ui.pages import {slug}\n\n{slug}.render()" in wrapper, slug
        assert "streamlit" not in _imported_roots(ROOT / "pages" / f"{slug}.py"), slug
    assert not (ROOT / "pages" / "_ui.py").exists()


def test_render_never_sets_page_config_navigation_or_stops_the_script() -> None:
    # st.stop() would also stop the Hub's own chrome drawn after render(); pages return early instead.
    for path in _ui_sources():
        source = path.read_text(encoding="utf-8")
        for call in ("st.set_page_config(", "st.navigation(", "st.Page(", "st.stop(", "switch_page("):
            assert call not in source, (path.name, call)


def test_render_works_from_the_packaged_files_alone(tmp_path: Path) -> None:
    # Signal Hub installs the release as a normal package: only src/prospectsignal/**/*.py and the declared package
    # data exist there, so render() must not read pages/, assets/ or data/ at the repo root. Run it in hub mode in a
    # clean working directory and check that nothing is written next to it.
    package_data = {Path("data"): {".csv", ".geojson", ".yaml"}, Path("ui", "assets", "marks"): None}
    for path in PACKAGE.rglob("*"):
        relative = path.relative_to(PACKAGE)
        suffixes = package_data.get(relative.parent, set())
        packaged = path.suffix == ".py" or suffixes is None or path.suffix in suffixes
        if path.is_file() and packaged and "__pycache__" not in relative.parts:
            target = tmp_path / "site" / "prospectsignal" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    site = str(tmp_path / "site")
    work = tmp_path / "work"
    work.mkdir()
    script = f"import sys\nsys.path.insert(0, {site!r})\nfrom prospectsignal.ui import render\nrender()\n"
    code = (
        f"import sys\nsys.path.insert(0, {site!r})\n"
        "from pathlib import Path\n"
        "from streamlit.testing.v1 import AppTest\n"
        "import prospectsignal\n"
        f"assert Path(prospectsignal.__file__).is_relative_to({site!r}), prospectsignal.__file__\n"
        "from prospectsignal.ui import signal_theme as sig\n"
        "assert Path(sig.page_config('prospect')['page_icon']).exists()\n"
        f"app = AppTest.from_string({script!r}, default_timeout=180)\n"
        "app.run()\n"
        "assert not app.exception, [error.value for error in app.exception]\n"
        f"for page in {PAGES!r}:\n"
        "    app.sidebar.radio[0].set_value(page).run()\n"
        "    assert not app.exception, (page, [error.value for error in app.exception])\n"
        "    assert not app.error, (page, [error.value for error in app.error])\n"
    )
    env = {**os.environ, "SIGNAL_HUB": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("PROSPECTSIGNAL_DATA_DIR", None)
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=300, cwd=work, env=env
    )
    assert result.returncode == 0, result.stderr
    assert list(work.iterdir()) == []


def test_render_runs_from_a_script_without_set_page_config(standalone_data_dir) -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()

    assert not app.exception, [error.value for error in app.exception]
    assert app.sidebar.radio[0].key == "prospect:page"
    assert "prospect:dataset" in app.session_state
    assert "dataset" not in app.session_state
    body = "\n".join(str(item.value) for item in app.markdown)
    assert "NORWEGIAN B2B PROSPECTING" in body
    assert "FILTER → SIZE → SHORTLIST → EXPORT" in body
    assert f"Prospect Signal v{__version__}" in body


@pytest.mark.parametrize("page", PAGES)
def test_every_widget_key_is_namespaced(page: str, standalone_data_dir) -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()
    _shortlist_top(app)  # so the shortlist and export pages draw their widgets
    _page_radio(app).set_value(page).run()

    assert not app.exception, [error.value for error in app.exception]
    widgets = [
        *app.radio, *app.selectbox, *app.checkbox, *app.toggle, *app.button, *app.number_input,
        *app.multiselect, *app.slider, *app.date_input, *app.text_input,
    ]
    assert widgets
    unkeyed = [(type(widget).__name__, widget.label) for widget in widgets if widget.key is None]
    assert not unkeyed, unkeyed
    assert all(widget.key.startswith("prospect:") for widget in widgets), [w.key for w in widgets]
    assert all(key.startswith("prospect:") for key in app.session_state), list(app.session_state)


def test_every_widget_call_passes_an_explicit_key() -> None:
    # Some widgets only appear after a click or on the real register; check the source too.
    unkeyed = []
    for path in _ui_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        unkeyed += [
            (path.name, node.lineno, node.func.attr)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in KEYED_CALLS
            and not any(keyword.arg == "key" for keyword in node.keywords)
        ]
    assert not unkeyed, unkeyed


def test_session_state_and_widget_keys_go_through_the_namespace_helper() -> None:
    state_keys: list[str] = []
    widget_keys: list[str] = []
    for path in _ui_sources():
        source = path.read_text(encoding="utf-8")
        state_keys += re.findall(r"session_state(?:\[|\.get\(|\.pop\()\s*([^,\])]+)", source)
        widget_keys += re.findall(r"\bkey=([^,)\n]+)", source)
    assert state_keys and widget_keys
    assert all(key.startswith(("k(", "key")) for key in state_keys), state_keys
    # The ICP form and fit targets build their keys with fk(), a k() wrapper that adds the ICP revision.
    assert all(key.startswith(("k(", "fk(")) for key in widget_keys), widget_keys
    assert 'NS = "prospect"' in (UI / "common.py").read_text(encoding="utf-8")


# -- hub mode -------------------------------------------------------------------------------------------------


@pytest.fixture
def hub(tmp_path, monkeypatch):
    """SIGNAL_HUB=1 in a clean cwd with home and app-data folders pointed at empty temp dirs; every way out to the
    network raises, and every database file Prospect Signal could open is recorded."""
    watched = {name: tmp_path / name.lower() for name in HUB_ENV_DIRS}
    watched["PROSPECTSIGNAL_DATA_DIR"] = tmp_path / "data"
    for name, folder in watched.items():
        folder.mkdir()
        monkeypatch.setenv(name, str(folder))
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("SIGNAL_HUB", "1")

    def refuse(*args, **kwargs):
        raise AssertionError("network call attempted in Signal Hub mode")

    real_socket_connect = socket.socket.connect
    real_create_connection = socket.create_connection

    def _external(address) -> bool:
        # asyncio on Windows builds its self-pipe from a loopback socket pair; only the outside world is refused.
        return not (isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1", "localhost"})

    def guarded_connect(self, address):
        if _external(address):
            refuse()
        return real_socket_connect(self, address)

    def guarded_create_connection(address, *args, **kwargs):
        if _external(address):
            refuse()
        return real_create_connection(address, *args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    monkeypatch.setattr(socket, "create_connection", guarded_create_connection)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    for name in ("bulk_headers", "download_bulk", "load_register", "fetch_unit", "refresh_unit"):
        monkeypatch.setattr(brreg, name, refuse)

    opened: list[str] = []
    real_connect = duckdb.connect
    real_init = Store.__init__

    def record_connect(database=":memory:", *args, **kwargs):
        opened.append(str(database))
        return real_connect(database, *args, **kwargs)

    def record_init(self, path=":memory:"):
        opened.append(str(path))
        real_init(self, path)

    monkeypatch.setattr(duckdb, "connect", record_connect)
    monkeypatch.setattr(Store, "__init__", record_init)
    from prospectsignal.ui import common

    common._open_store.clear()
    yield {"dirs": [*watched.values(), cwd], "opened": opened}
    common._open_store.clear()


def _assert_nothing_written(hub_env) -> None:
    written = [str(path) for folder in hub_env["dirs"] for path in folder.rglob("*")]
    assert written == [], written
    assert hub_env["opened"] and set(hub_env["opened"]) == {":memory:"}, hub_env["opened"]


def test_hub_mode_renders_every_page_from_the_in_memory_demo(hub) -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()
    assert not app.exception, [error.value for error in app.exception]
    assert [radio.key for radio in app.sidebar.radio] == ["prospect:page"]  # no dataset choice in the Hub
    assert "in memory for this session" in "\n".join(str(c.value) for c in app.sidebar.caption)
    for page in PAGES:
        _page_radio(app).set_value(page).run()
        assert not app.exception, (page, [error.value for error in app.exception])
        assert not app.error, (page, [error.value for error in app.error])
    store = app.session_state["prospect:hub_store"]
    assert store.path == ":memory:"
    assert store.get_meta("dataset") == "demo" and store.unit_count() > 1000
    _assert_nothing_written(hub)


def test_hub_mode_explains_the_disabled_register_and_offers_no_download(hub) -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()
    _page_radio(app).set_value("Data & register").run()
    assert not app.exception, [error.value for error in app.exception]
    labels = {button.label for button in app.button}
    assert "Load real register" not in labels and "Check today's file" not in labels
    assert not [box for box in app.checkbox if box.label.startswith("Also load underenheter")]
    assert not app.text_input  # no single-unit refresh form
    assert "Loading the real register is off in Signal Hub" in _text(app)
    next(button for button in app.button if button.key == "prospect:rebuild_demo").click().run()
    assert not app.exception, [error.value for error in app.exception]
    _assert_nothing_written(hub)


def test_hub_mode_full_workflow_writes_nothing_and_calls_no_network(hub) -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()
    _shortlist_top(app)
    form_name = next(t for t in app.text_input if t.label == "ICP name")
    form_name.set_value("Hub ICP")  # submitted with the button below (a separate run drops pending form values)
    next(button for button in app.button if button.label == "Apply and save ICP").click().run()
    assert not app.exception, [error.value for error in app.exception]
    store = app.session_state["prospect:hub_store"]
    assert "Hub ICP" in store.list_icps()

    _page_radio(app).set_value("3 · Shortlist").run()
    assert not app.exception
    assert "never implies marketing consent" in _text(app)

    _page_radio(app).set_value("Company card").run()
    next(t for t in app.text_input if t.key == "prospect:company_search").set_value("DEMO").run()
    assert not app.exception, [error.value for error in app.exception]
    refresh = next(button for button in app.button if button.key == "prospect:card_refresh")
    assert refresh.disabled

    _page_radio(app).set_value("4 · Export").run()
    assert not app.exception
    assert "Not legal advice" in _text(app)
    next(box for box in app.checkbox if box.key == "prospect:export_ack").check().run()
    assert not app.exception, [error.value for error in app.exception]
    next(button for button in app.button if button.key == "prospect:mark_sent").click().run()
    assert not app.exception, [error.value for error in app.exception]
    assert set(store.shortlist_frame()["status"]) == {"sent to CRM"}

    # Never people: the in-memory database has the same person-free schema as the local one.
    for table in ("units", "shortlist", "icps", "meta"):
        assert_no_person_columns(store.table_columns(table))
    _assert_nothing_written(hub)


def test_hub_mode_keeps_one_database_per_session(hub) -> None:
    first = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    first.run()
    _shortlist_top(first)
    second = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    second.run()
    one, two = first.session_state["prospect:hub_store"], second.session_state["prospect:hub_store"]
    assert one is not two
    assert len(one.shortlist_frame()) > 0
    assert two.shortlist_frame().empty


def test_hub_mode_ignores_a_custom_checklist_file(hub, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PROSPECTSIGNAL_CHECKLIST", str(tmp_path / "missing-local-checklist.yaml"))
    from prospectsignal.ui import common

    assert common.load_checklist().items  # bundled checklist, the local file is never read


def test_standalone_mode_still_offers_the_register_download(standalone_data_dir) -> None:
    app = AppTest.from_string(RENDER_SCRIPT, default_timeout=120)
    app.run()
    assert [radio.key for radio in app.sidebar.radio] == ["prospect:page", "prospect:dataset"]
    _page_radio(app).set_value("Data & register").run()
    assert not app.exception, [error.value for error in app.exception]
    assert {"Load real register", "Check today's file"} <= {button.label for button in app.button}
    assert (standalone_data_dir / "demo.duckdb").exists()
