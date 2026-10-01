"""ProspectSignal: open, local-first B2B prospecting from Norway's Enhetsregisteret.

Public API (stable for the Signal suite; nothing here imports Streamlit)::

    from prospectsignal import Store, ICP, load_demo, load_register
    store = Store("data/demo.duckdb")
    load_demo(store)
    store.count(demo_icp())
"""

__version__ = "1.0.0"

from .brreg import (  # noqa: E402
    ATTRIBUTION,
    ATTRIBUTION_EN,
    CONSENT_NOTE,
    DEMO_ATTRIBUTION,
    LICENCE_NAME,
    LICENCE_URL,
    fetch_unit,
    load_register,
    refresh_unit,
    register_url,
)
from .checklist import Checklist, load as load_checklist  # noqa: E402
from .demo import load_demo, make_demo_units  # noqa: E402
from .errors import DataProblem, RegisterUnavailable, friendly_message  # noqa: E402
from .export import FREDDO_COLUMNS, freddo_csv_bytes, freddo_frame, xlsx_bytes  # noqa: E402
from .icp import ICP, demo_icp  # noqa: E402
from .market import market_tables  # noqa: E402
from .orgnr import is_valid as is_valid_orgnr  # noqa: E402
from .schema import EMPLOYEE_BANDS, ENK_WARNING, SHORTLIST_STATUSES, UNIT_COLUMNS  # noqa: E402
from .shortlist import FitTargets, FitWeights, score_frame  # noqa: E402
from .storage import Store  # noqa: E402

__all__ = [
    "ATTRIBUTION",
    "ATTRIBUTION_EN",
    "CONSENT_NOTE",
    "DEMO_ATTRIBUTION",
    "EMPLOYEE_BANDS",
    "ENK_WARNING",
    "FREDDO_COLUMNS",
    "LICENCE_NAME",
    "LICENCE_URL",
    "SHORTLIST_STATUSES",
    "UNIT_COLUMNS",
    "Checklist",
    "DataProblem",
    "FitTargets",
    "FitWeights",
    "ICP",
    "RegisterUnavailable",
    "Store",
    "demo_icp",
    "fetch_unit",
    "freddo_csv_bytes",
    "freddo_frame",
    "friendly_message",
    "is_valid_orgnr",
    "load_checklist",
    "load_demo",
    "load_register",
    "make_demo_units",
    "market_tables",
    "refresh_unit",
    "register_url",
    "score_frame",
    "xlsx_bytes",
    "__version__",
]
