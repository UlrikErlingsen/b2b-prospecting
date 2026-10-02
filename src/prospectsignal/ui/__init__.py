"""Prospect Signal user interface: the Signal Hub entry point.

The only package under ``prospectsignal`` that imports Streamlit. ``render()`` draws the whole app on the current
page and never calls ``st.set_page_config`` or ``st.navigation``; the standalone ``app.py`` or Signal Hub owns the
page config and navigation. With ``SIGNAL_HUB=1`` the app runs the fictional demo in an in-memory DuckDB per session,
writes no files and makes no network calls.
"""

from prospectsignal import __version__
from prospectsignal.ui import signal_theme
from prospectsignal.ui.app import render

APP_INFO = {"product": "Prospect Signal", "version": __version__, "repo": "b2b-prospecting", "slug": "prospect"}

__all__ = ["APP_INFO", "render", "signal_theme"]
