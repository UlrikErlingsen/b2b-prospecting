"""Shared Streamlit helpers for the Prospect Signal pages.

Streamlit lives only in app.py, pages/ and src/prospectsignal/ui/ (the synced Signal theme)."""

from __future__ import annotations

import os
from pathlib import Path
import traceback

import pandas as pd
import streamlit as st

from prospectsignal import (
    ATTRIBUTION,
    CONSENT_NOTE,
    DEMO_ATTRIBUTION,
    ICP,
    LICENCE_URL,
    DataProblem,
    RegisterUnavailable,
    Store,
    demo_icp,
    friendly_message,
    load_demo,
)
from prospectsignal.demo import DEMO_SEED, DEMO_SIZE
from prospectsignal.schema import PERSON_NAME_FORMS, UNKNOWN_FORM
from prospectsignal.ui import signal_theme as sig

ROOT = Path(__file__).resolve().parents[1]
KEY = "prospect"  # signal_theme app key (Market family)
DATASETS = {"demo": "Offline demo (fictional)", "register": "Real register (Brønnøysund)"}


def data_dir() -> Path:
    return Path(os.environ.get("PROSPECTSIGNAL_DATA_DIR") or ROOT / "data")


@st.cache_resource(show_spinner=False)
def _open_store(path: str) -> Store:
    return Store(path)


def demo_store() -> Store:
    store = _open_store(str(data_dir() / "demo.duckdb"))
    if store.unit_count() == 0 or store.get_meta("demo_version") != f"{DEMO_SIZE}-{DEMO_SEED}":
        load_demo(store)
    return store


def register_store() -> Store:
    return _open_store(str(data_dir() / "register.duckdb"))


def dataset() -> str:
    """The active dataset. A first launch opens the offline demo; once the register is loaded, new sessions use it."""
    if "dataset" not in st.session_state:
        requested = st.query_params.get("dataset")
        if requested in DATASETS:
            st.session_state["dataset"] = requested
        else:
            st.session_state["dataset"] = "register" if register_store().unit_count() > 0 else "demo"
    return st.session_state["dataset"]


def store() -> Store:
    return register_store() if dataset() == "register" else demo_store()


def require_data() -> Store:
    """The active store, or a friendly stop when the real register has not been loaded yet."""
    current = store()
    if current.unit_count() == 0:
        st.info(
            "The real register is not loaded on this computer yet. Open **Data & register** and choose "
            "**Load real register**, or switch back to the offline demo in the sidebar."
        )
        st.stop()
    return current


def current_icp() -> ICP:
    key = f"icp_{dataset()}"
    if key not in st.session_state:
        st.session_state[key] = demo_icp()
    return st.session_state[key]


def set_icp(icp: ICP) -> None:
    st.session_state[f"icp_{dataset()}"] = icp


def header(kicker: str, title: str, subtitle: str) -> None:
    sig.header(kicker, title, subtitle)


def consent_note() -> None:
    sig.note("warn", f"**Not consent.** {CONSENT_NOTE}")


def boundary(text: str) -> None:
    """A boundary note. Supports **bold**, `code` and [links](https://...); no raw HTML."""
    sig.note("boundary", text)


def attribution_text(current: Store) -> str:
    if current.get_meta("dataset") == "demo":
        return DEMO_ATTRIBUTION
    downloaded = current.get_meta("downloaded_at", "")
    return f"{ATTRIBUTION} Downloaded {downloaded}. Licence: {LICENCE_URL}"


def show_error(exc: Exception) -> None:
    st.error(friendly_message(exc))
    if not isinstance(exc, (DataProblem, RegisterUnavailable, ValueError)) and os.getenv("PROSPECTSIGNAL_DEBUG") == "1":
        with st.expander("Technical details"):
            st.code("".join(traceback.format_exception(exc)))


def enk_flag(frame: pd.DataFrame) -> pd.Series:
    labels = {"ENK": "⚠ ENK: person name", UNKNOWN_FORM: "⚠ legal form unknown"}
    return frame["org_form"].map(lambda form: labels.get(form, ""))


def date_text(value: object) -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return "—"
    return pd.Timestamp(value).date().isoformat()


def has_person_name_forms(frame: pd.DataFrame) -> bool:
    return bool(frame["org_form"].isin(PERSON_NAME_FORMS).any())
