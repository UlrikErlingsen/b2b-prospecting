"""Shared Streamlit helpers for the Prospect Signal pages (Streamlit allowed here: this is the ui package).

Every session-state key and explicit widget key goes through :func:`k`, so Prospect Signal can share one Streamlit
session with the other Signal apps inside Signal Hub.

Hub mode (``SIGNAL_HUB=1``): the app keeps everything in an in-memory DuckDB held in ``st.session_state`` and
preloaded with the fictional offline demo. It never opens a database file, never reads an earlier local workspace and
never calls Brønnøysundregistrene. Standalone behaviour is unchanged.
"""

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
    checklist,
    demo_icp,
    friendly_message,
    load_demo,
)
from prospectsignal.demo import DEMO_SEED, DEMO_SIZE
from prospectsignal.schema import PERSON_NAME_FORMS, UNKNOWN_FORM
from prospectsignal.ui import signal_theme as sig

NS = "prospect"
KEY = NS  # signal_theme app key (Market family)
DATASETS = {"demo": "Offline demo (fictional)", "register": "Real register (Brønnøysund)"}
HUB_OFF_NOTE = (
    "**Loading the real register is off in Signal Hub.** The Hub runs the fictional offline demo in memory for this "
    "session only: nothing is downloaded from Brønnøysundregistrene and nothing is saved on the server. Run Prospect "
    "Signal locally to load and keep the real register."
)
# A source checkout keeps its databases in <repo>/data, as before; an installed package uses ./data.
_CHECKOUT = Path(__file__).resolve().parents[3]


def k(name: str) -> str:
    """Namespace a session-state or widget key with the app slug, so apps can share one Hub session."""
    return f"{NS}:{name}"


def hub_mode() -> bool:
    """True inside Signal Hub: in-memory demo only, no files, no network."""
    return os.environ.get("SIGNAL_HUB") == "1"


def data_dir() -> Path:
    if hub_mode():
        raise DataProblem("Prospect Signal stores no files in Signal Hub.")
    configured = os.environ.get("PROSPECTSIGNAL_DATA_DIR")
    if configured:
        return Path(configured)
    if (_CHECKOUT / "pyproject.toml").exists() and (_CHECKOUT / "src" / "prospectsignal").is_dir():
        return _CHECKOUT / "data"
    return Path.cwd() / "data"


@st.cache_resource(show_spinner=False)
def _open_store(path: str) -> Store:
    return Store(path)


def _hub_demo_store() -> Store:
    # One in-memory database per browser session, preloaded with the fictional demo on first use.
    current = st.session_state.get(k("hub_store"))
    if current is None:
        current = Store(":memory:")
        load_demo(current)
        st.session_state[k("hub_store")] = current
    return current


def demo_store() -> Store:
    if hub_mode():
        return _hub_demo_store()
    current = _open_store(str(data_dir() / "demo.duckdb"))
    if current.unit_count() == 0 or current.get_meta("demo_version") != f"{DEMO_SIZE}-{DEMO_SEED}":
        load_demo(current)
    return current


def register_store() -> Store:
    if hub_mode():
        raise DataProblem("The real register is off in Signal Hub. Run Prospect Signal locally to load it.")
    return _open_store(str(data_dir() / "register.duckdb"))


def datasets() -> dict[str, str]:
    """The datasets this session may choose from (only the offline demo inside Signal Hub)."""
    return {"demo": DATASETS["demo"]} if hub_mode() else dict(DATASETS)


def dataset() -> str:
    """The active dataset. A first launch opens the offline demo; once the register is loaded, new sessions use it."""
    if hub_mode():
        return "demo"
    key = k("dataset")
    if key not in st.session_state:
        requested = st.query_params.get("dataset")
        if requested in DATASETS:
            st.session_state[key] = requested
        else:
            st.session_state[key] = "register" if register_store().unit_count() > 0 else "demo"
    return st.session_state[key]


def request_dataset(name: str) -> None:
    """Switch dataset on the next rerun (the sidebar radio owns the key, so it cannot change mid-run)."""
    st.session_state[k("dataset_next")] = name


def apply_requested_dataset() -> None:
    """Call before the sidebar radio is drawn."""
    pending = st.session_state.pop(k("dataset_next"), None)
    if pending in datasets():
        st.session_state[k("dataset")] = pending


def store() -> Store:
    return register_store() if dataset() == "register" else demo_store()


def require_data() -> Store | None:
    """The active store, or None after a friendly note when the real register has not been loaded yet."""
    current = store()
    if current.unit_count() == 0:
        st.info(
            "The real register is not loaded on this computer yet. Open **Data & register** and choose "
            "**Load real register**, or switch back to the offline demo in the sidebar."
        )
        return None
    return current


def current_icp() -> ICP:
    key = k(f"icp_{dataset()}")
    if key not in st.session_state:
        st.session_state[key] = demo_icp()
    return st.session_state[key]


def icp_revision() -> int:
    """Bumped whenever the ICP is replaced, so the keyed filter widgets start again from the new ICP."""
    return int(st.session_state.get(k("icp_rev"), 0))


def set_icp(icp: ICP) -> None:
    st.session_state[k(f"icp_{dataset()}")] = icp
    st.session_state[k("icp_rev")] = icp_revision() + 1


def load_checklist() -> checklist.Checklist:
    """The outreach checklist: the bundled one inside Signal Hub, otherwise the configurable local one."""
    return checklist.bundled() if hub_mode() else checklist.load()


def header(kicker: str, title: str, subtitle: str) -> None:
    sig.header(kicker, title, subtitle)


def consent_note() -> None:
    sig.note("warn", f"**Not consent.** {CONSENT_NOTE}")


def boundary(text: str) -> None:
    """A boundary note. Supports **bold**, `code`, [links](https://...) and blank-line paragraphs; no raw HTML."""
    sig.note("boundary", text)


def hub_note() -> None:
    sig.note("muted", HUB_OFF_NOTE)


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
