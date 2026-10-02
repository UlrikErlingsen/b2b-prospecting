"""Prospect Signal standalone entry point (st.navigation shell; page code lives in prospectsignal.ui.pages).

Signal Hub does not run this file: it imports ``prospectsignal.ui.render``, which draws the same pages behind a
namespaced sidebar radio.
"""

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

from prospectsignal.ui import app as shell, signal_theme as sig
from prospectsignal.ui.common import NS

st.set_page_config(**sig.page_config(NS))
shell.start()
shell.sidebar_top()
shell.dataset_picker()
navigation = st.navigation(
    [
        st.Page(f"pages/{slug}.py", title=title, icon=icon, default=slug == "welcome")
        for title, (_, icon, slug) in shell.PAGES.items()
    ],
    position="sidebar",
)
shell.sidebar_status()
shell.masthead()
shell.run_page(navigation.run)
shell.footer()
