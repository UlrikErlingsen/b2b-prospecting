"""Prospect Signal pages. Each module exposes ``render()``; logic lives in the Streamlit-free core.

The standalone ``app.py`` reaches them through thin ``pages/*.py`` wrappers and ``st.navigation``; Signal Hub reaches
them through ``prospectsignal.ui.render()`` and a namespaced sidebar radio.
"""
