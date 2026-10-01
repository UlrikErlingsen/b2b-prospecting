from dataclasses import replace

import streamlit as st

from pages import _ui
from prospectsignal import market, nace, regions
from prospectsignal.ui import signal_theme as sig


def _themed(figure):
    """Give each figure the per-app Signal template (the process-wide default is shared across Hub sessions)."""
    return figure.update_layout(template=sig.template(_ui.KEY))


_ui.header(
    "Step 2 · Market size",
    "How big is the market?",
    "Counts for the current ICP by county, industry, size band and registration year. Counts size a market; "
    "they never become a contact list.",
)
store = _ui.require_data()
icp = _ui.current_icp()
st.caption("ICP: " + icp.name + " · " + " · ".join(icp.describe()))
include_enk = st.toggle(
    "Count sole proprietorships (ENK) too",
    value=icp.include_enk,
    help="Counts only — no ENK names are shown on this page.",
)
counted = replace(icp, include_enk=include_enk)
tables = market.market_tables(store, counted)

total = int(tables["fylke"]["units"].sum())
with_staff = int(tables["employee_band"].loc[~tables["employee_band"]["key"].isin(["0"]), "units"].sum())
a, b, c = st.columns(3)
a.metric("Units in this market", f"{total:,}")
b.metric("With registered employees", f"{with_staff:,}")
c.metric("Counties represented", f"{tables['fylke']['key'].notna().sum():,}")

st.plotly_chart(
    _themed(market.fylke_map(tables["fylke"], colorscale=sig.sequential(_ui.KEY), line_color=sig.CORE["paper"])),
    width="stretch",
)
st.caption(regions.MAP_SOURCE)

left, right = st.columns(2)
with left:
    st.plotly_chart(
        _themed(market.bar(tables["nace_division"], "industry", "Units by industry division")), width="stretch"
    )
    st.caption(nace.NACE_SOURCE)
with right:
    st.plotly_chart(
        _themed(market.bar(tables["employee_band"], "key", "Units by employee band", horizontal=False)), width="stretch"
    )
    st.caption("“0” = no employees registered; “1-4” = employees registered but the count is hidden below five.")

st.plotly_chart(_themed(market.registrations_chart(tables["registered_year"])), width="stretch")
st.caption(
    "Registration year in Enhetsregisteret for units that are still registered (the bulk file lists current units "
    "only, so earlier years are undercounted by later deletions). Enhetsregisteret started in 1995; older companies "
    "show their transfer date."
)

with st.expander("Tables"):
    fylke_table = tables["fylke"][["fylke", "units"]]
    st.dataframe(fylke_table, hide_index=True, width="stretch")
    st.dataframe(tables["org_form"].rename(columns={"key": "org_form"}), hide_index=True, width="stretch")
_ui.boundary(
    "**Counts, not contacts.** This page shows aggregate counts only. Selecting individual companies "
    "happens deliberately on the ICP and Shortlist pages, and Freddo CRM receives only what you export."
)
