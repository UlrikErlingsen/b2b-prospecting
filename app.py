"""Prospect Signal Streamlit application (navigation shell; pages live in pages/)."""

from __future__ import annotations

import os

# Keep Arrow serialization stable on macOS. This must be set before Streamlit imports Arrow.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
for path in (SRC, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from prospectsignal import __version__
from prospectsignal.ui import signal_theme as sig
from pages import _ui

st.set_page_config(**sig.page_config(_ui.KEY))
sig.apply(_ui.KEY)

PAGES = [
    st.Page("pages/welcome.py", title="Welcome", icon=":material/home:", default=True),
    st.Page("pages/data.py", title="Data & register", icon=":material/database:"),
    st.Page("pages/icp.py", title="1 · ICP filters", icon=":material/filter_alt:"),
    st.Page("pages/market.py", title="2 · Market size", icon=":material/map:"),
    st.Page("pages/shortlist.py", title="3 · Shortlist", icon=":material/checklist:"),
    st.Page("pages/company.py", title="Company card", icon=":material/apartment:"),
    st.Page("pages/export.py", title="4 · Export", icon=":material/download:"),
    st.Page("pages/about.py", title="Sources & boundaries", icon=":material/gavel:"),
]

sig.sidebar_brand(_ui.KEY, "Norwegian B2B prospecting from open register data.")

with st.sidebar:
    st.caption(f"Norwegian B2B prospecting · v{__version__}")
    choice = st.radio(
        "Dataset",
        list(_ui.DATASETS),
        format_func=_ui.DATASETS.get,
        index=list(_ui.DATASETS).index(_ui.dataset()),
    )
    st.session_state["dataset"] = choice

navigation = st.navigation(PAGES, position="sidebar")

with st.sidebar:
    st.markdown("---")
    try:
        active = _ui.store()
        units = active.unit_count()
        if _ui.dataset() == "demo":
            st.caption(f"Demo: {units:,} fictional units (org.nr fail MOD11 on purpose).")
        elif units:
            st.caption(f"Register: {units:,} units · downloaded {active.get_meta('downloaded_at', '?')}")
        else:
            st.caption("Register: not loaded yet — see Data & register.")
    except Exception as exc:  # pragma: no cover - surfaced in the page body as well
        st.caption(f"Data store unavailable: {exc}")
    st.caption("Local mode · no telemetry · no accounts · no external AI calls")

sig.masthead(
    _ui.KEY,
    ["Open register data", "No person data", "Runs locally"],
    kicker="FILTER → SIZE → SHORTLIST → EXPORT",
)

try:
    navigation.run()
except Exception as exc:
    _ui.show_error(exc)

try:
    attribution = _ui.attribution_text(_ui.store())
except Exception:  # pragma: no cover
    attribution = ""
sig.footer(_ui.KEY, __version__, "Registry data is not marketing consent")
if attribution:
    sig.note("muted", attribution)
