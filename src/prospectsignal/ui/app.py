"""Prospect Signal Streamlit shell.

``render()`` draws the whole app on the current page for Signal Hub (and any script without ``st.navigation``):
theme, sidebar lockup, dataset choice, a namespaced page radio over the same page functions the standalone app uses,
masthead, the selected page and the footer. It never calls ``st.set_page_config`` or ``st.navigation``.

The standalone ``app.py`` keeps its ``st.navigation`` + ``pages/`` layout and reuses the shell pieces below.
Module-level code only defines constants and functions; everything that draws runs inside a function.
"""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from prospectsignal import __version__
from prospectsignal.ui import common as ui
from prospectsignal.ui import signal_theme as sig
from prospectsignal.ui.common import NS, k
from prospectsignal.ui.pages import about, company, data, export, icp, market, shortlist, welcome

SIDEBAR_TAGLINE = "Norwegian B2B prospecting from open register data."
MASTHEAD_KICKER = "FILTER → SIZE → SHORTLIST → EXPORT"
MASTHEAD_PROMISES = ["Open register data", "No person data", "Runs locally"]
HUB_PROMISES = ["Open register data", "No person data", "Demo in memory"]
FOOTER_LINE = "Registry data is not marketing consent"

# title -> (page function, Material icon, URL path used by the standalone pages/ wrappers)
PAGES: dict[str, tuple[Callable[[], None], str, str]] = {
    "Welcome": (welcome.render, ":material/home:", "welcome"),
    "Data & register": (data.render, ":material/database:", "data"),
    "1 · ICP filters": (icp.render, ":material/filter_alt:", "icp"),
    "2 · Market size": (market.render, ":material/map:", "market"),
    "3 · Shortlist": (shortlist.render, ":material/checklist:", "shortlist"),
    "Company card": (company.render, ":material/apartment:", "company"),
    "4 · Export": (export.render, ":material/download:", "export"),
    "Sources & boundaries": (about.render, ":material/gavel:", "about"),
}


def start() -> None:
    """Theme and per-rerun state. Runs before anything else is drawn."""
    sig.apply(NS)
    ui.apply_requested_dataset()
    ui.dataset()


def sidebar_top() -> None:
    """Lockup and version."""
    sig.sidebar_brand(NS, SIDEBAR_TAGLINE)
    with st.sidebar:
        st.caption(f"Norwegian B2B prospecting · v{__version__}")


def dataset_picker() -> None:
    """The dataset choice (only the offline demo inside Signal Hub)."""
    with st.sidebar:
        options = ui.datasets()
        if len(options) > 1:
            st.radio("Dataset", list(options), format_func=options.get, key=k("dataset"))
        else:
            st.caption("Dataset: offline demo (fictional), in memory for this session.")


def sidebar_status() -> None:
    with st.sidebar:
        st.markdown("---")
        try:
            active = ui.store()
            units = active.unit_count()
            if ui.dataset() == "demo":
                st.caption(f"Demo: {units:,} fictional units (org.nr fail MOD11 on purpose).")
            elif units:
                st.caption(f"Register: {units:,} units · downloaded {active.get_meta('downloaded_at', '?')}")
            else:
                st.caption("Register: not loaded yet — see Data & register.")
        except Exception as exc:  # pragma: no cover - surfaced in the page body as well
            st.caption(f"Data store unavailable: {exc}")
        if ui.hub_mode():
            st.caption("Signal Hub mode · demo in memory · no downloads · nothing saved")
        else:
            st.caption("Local mode · no telemetry · no accounts · no external AI calls")


def masthead() -> None:
    sig.masthead(NS, HUB_PROMISES if ui.hub_mode() else MASTHEAD_PROMISES, kicker=MASTHEAD_KICKER)


def footer() -> None:
    try:
        attribution = ui.attribution_text(ui.store())
    except Exception:  # pragma: no cover
        attribution = ""
    sig.footer(NS, __version__, FOOTER_LINE)
    if attribution:
        sig.note("muted", attribution)


def run_page(page: Callable[[], None]) -> None:
    try:
        page()
    except Exception as exc:
        ui.show_error(exc)


def render() -> None:
    """Draw the whole Prospect Signal app on the current page. Never calls st.set_page_config or st.navigation."""
    start()
    sidebar_top()
    with st.sidebar:
        title = st.radio("Page", list(PAGES), key=k("page"))
    dataset_picker()
    sidebar_status()
    masthead()
    run_page(PAGES[title][0])
    footer()
