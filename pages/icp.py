from dataclasses import replace
from datetime import date
import time

import pandas as pd
import streamlit as st

from pages import _ui
from prospectsignal import demo_icp, nace, regions
from prospectsignal.errors import DataProblem
from prospectsignal.schema import ENK_WARNING, ORG_FORMS

TABLE_LIMIT = 2000

_ui.header(
    "Step 1 · ICP filters",
    "Describe your ideal customer",
    "Combine industry, region, size, age, legal form and status. Empty fields mean “any”. Inactive companies "
    "(bankrupt, in liquidation) and sole proprietorships (ENK) are excluded unless you include them.",
)
store = _ui.require_data()
icp = _ui.current_icp()

saved = store.list_icps()
with st.expander(f"Saved ICPs ({len(saved)})", expanded=False):
    if saved:
        chosen = st.selectbox("Load a saved ICP", saved)
        load_col, delete_col = st.columns(2)
        if load_col.button("Load"):
            _ui.set_icp(store.load_icp(chosen))
            st.rerun()
        if delete_col.button("Delete"):
            store.delete_icp(chosen)
            st.rerun()
    else:
        st.caption("No saved ICPs yet. Name the filter below and press “Save ICP”.")
    if st.button("Reset to the demo ICP (Fjellbrus)"):
        _ui.set_icp(demo_icp())
        st.rerun()

region_options = list(regions.REGION_ALIASES) + list(regions.FYLKER) + list(regions.OTHER_AREAS)
selected_regions = list(icp.fylker)
alias_numbers = regions.REGION_ALIASES["Viken (former, 2020-2023)"]
if set(alias_numbers) <= set(selected_regions):
    selected_regions = ["Viken (former, 2020-2023)"] + [f for f in selected_regions if f not in alias_numbers]
kommuner = store.kommuner_present()
kommune_labels = {row.kommune_nr: f"{row.kommune_nr} {str(row.kommune).title()}" for row in kommuner.itertuples()}

with st.form("icp_form"):
    name = st.text_input("ICP name", value=icp.name)
    st.markdown("**Industry (NACE / SN2025)**")
    division_choices = [code for code, _ in nace.divisions()]
    selected_divisions = [p for p in icp.nace_prefixes if len(p) == 2]
    detailed = [p for p in icp.nace_prefixes if len(p) > 2]
    divisions_picked = st.multiselect(
        "Divisions",
        division_choices,
        default=[d for d in selected_divisions if d in division_choices],
        format_func=nace.label,
        help="A division includes every group, class and subclass below it (10 → 10.1 → 10.11 → 10.110).",
    )
    detail_text = st.text_input(
        "More specific codes (comma-separated)",
        value=", ".join(detailed),
        placeholder="e.g. 46.34, 47.25, 56.1",
        help="Any level works: group (10.1), class (10.11) or subclass (10.110). Section letters (C) also work.",
    )
    any_code = st.checkbox("Also match secondary industry codes", value=icp.nace_any_code)

    st.markdown("**Region**")
    region_col, kommune_col = st.columns(2)
    regions_picked = region_col.multiselect(
        "Fylke",
        region_options,
        default=[r for r in selected_regions if r in region_options],
        format_func=lambda key: key if key in regions.REGION_ALIASES else regions.fylke_name(key),
        help="Viken was split on 1 January 2024 into Østfold, Akershus and Buskerud; the alias selects all three.",
    )
    kommuner_picked = kommune_col.multiselect(
        "Kommune (optional)",
        list(kommune_labels),
        default=[k for k in icp.kommuner if k in kommune_labels],
        format_func=lambda key: kommune_labels.get(key, key),
    )

    st.markdown("**Size and age**")
    size_a, size_b, size_c = st.columns(3)
    employees_min = size_a.number_input("Employees, minimum", min_value=0, value=icp.employees_min or 0, step=1)
    no_max = size_c.checkbox("No maximum", value=icp.employees_max is None)
    employees_max = size_b.number_input(
        "Employees, maximum", min_value=0, value=icp.employees_max if icp.employees_max is not None else 100, step=1
    )
    st.caption(
        "The register hides counts below five: units with 1–4 employees are included only when the whole 1–4 range "
        "fits your limits; units with none registered count as 0."
    )
    age_a, age_b = st.columns(2)
    use_from = age_a.checkbox("Founded on or after", value=icp.founded_from is not None)
    founded_from = age_a.date_input(
        "From", value=icp.founded_from or date(2018, 1, 1), min_value=date(1800, 1, 1), label_visibility="collapsed"
    )
    use_to = age_b.checkbox("Founded on or before", value=icp.founded_to is not None)
    founded_to = age_b.date_input(
        "To", value=icp.founded_to or date.today(), min_value=date(1800, 1, 1), label_visibility="collapsed"
    )

    st.markdown("**Form and status**")
    form_a, form_b = st.columns(2)
    forms_picked = form_a.multiselect(
        "Organisation form (empty = any)",
        list(ORG_FORMS),
        default=[f for f in icp.org_forms if f in ORG_FORMS],
        format_func=lambda code: f"{code} — {ORG_FORMS[code]}",
    )
    vat_choice = form_b.radio(
        "VAT-registered (MVA)",
        ["Any", "Yes", "No"],
        index={None: 0, True: 1, False: 2}[icp.vat_registered],
        horizontal=True,
    )
    flag_a, flag_b, flag_c = st.columns(3)
    exclude_inactive = flag_a.checkbox("Exclude bankrupt / in liquidation", value=icp.exclude_inactive)
    include_enk = flag_b.checkbox("Include ENK (sole proprietors)", value=icp.include_enk, help=ENK_WARNING)
    entity_kind = flag_c.radio(
        "Unit level",
        ["hovedenhet", "underenhet", "both"],
        index=["hovedenhet", "underenhet", "both"].index(icp.entity_kind),
        format_func={"hovedenhet": "Companies", "underenhet": "Locations (sub-units)", "both": "Both"}.get,
    )
    apply_col, save_col = st.columns(2)
    applied = apply_col.form_submit_button("Apply filters", type="primary")
    save = save_col.form_submit_button("Apply and save ICP")

if applied or save:
    try:
        prefixes = list(divisions_picked) + (nace.parse_prefixes(detail_text) if detail_text.strip() else [])
        new_icp = replace(
            icp,
            name=name,
            nace_prefixes=tuple(prefixes),
            nace_any_code=any_code,
            fylker=tuple(regions.expand_regions(regions_picked)),
            kommuner=tuple(kommuner_picked),
            employees_min=int(employees_min) or None,
            employees_max=None if no_max else int(employees_max),
            founded_from=founded_from if use_from else None,
            founded_to=founded_to if use_to else None,
            org_forms=tuple(forms_picked),
            include_enk=include_enk,
            vat_registered={"Any": None, "Yes": True, "No": False}[vat_choice],
            exclude_inactive=exclude_inactive,
            entity_kind=entity_kind,
        ).validated()
        _ui.set_icp(new_icp)
        if save:
            store.save_icp(new_icp)
            st.toast(f"Saved “{new_icp.name}”.")
        st.rerun()
    except (DataProblem, ValueError) as exc:
        st.error(str(exc))

icp = _ui.current_icp()
started = time.perf_counter()
matches = store.count(icp)
results = store.query(icp, limit=TABLE_LIMIT)
elapsed = time.perf_counter() - started

metric_a, metric_b, metric_c = st.columns(3)
metric_a.metric("Matching units", f"{matches:,}")
metric_b.metric("Already shortlisted", f"{int(results['shortlist_status'].notna().sum()):,}")
metric_c.metric("Query time", f"{elapsed:.2f} s")
st.caption(" · ".join(icp.describe()))
if icp.include_enk:
    st.warning(ENK_WARNING)

if results.empty:
    st.info("No units match. Widen the industry, region or size limits.")
    st.stop()

view = results.copy()
view.insert(0, "⚠", _ui.enk_flag(view))
view["fylke"] = view["fylke_nr"].map(regions.fylke_name)
view["in shortlist"] = view["shortlist_status"].fillna("")
if len(results) < matches:
    st.caption(f"Showing the {TABLE_LIMIT:,} largest of {matches:,} matches (by employee count).")
selection = st.dataframe(
    view,
    hide_index=True,
    width="stretch",
    height=440,
    on_select="rerun",
    selection_mode="multi-row",
    key="icp_results",
    column_order=[
        "⚠",
        "name",
        "org_nr",
        "org_form",
        "nace1",
        "nace1_desc",
        "employee_band",
        "employees",
        "founded",
        "kommune",
        "fylke",
        "postcode",
        "website",
        "entity_kind",
        "in shortlist",
    ],
    column_config={
        "name": "Name",
        "org_nr": st.column_config.TextColumn("Org.nr"),
        "org_form": "Form",
        "kommune": "Kommune",
        "fylke": "Fylke",
        "in shortlist": "Shortlist",
        "nace1": "NACE",
        "nace1_desc": "Industry",
        "employee_band": "Band",
        "employees": st.column_config.NumberColumn("Employees", help="Blank when 0–4 (hidden by the register)"),
        "founded": st.column_config.DateColumn("Founded"),
        "postcode": st.column_config.TextColumn("Postcode"),
        "website": st.column_config.TextColumn("Website"),
        "entity_kind": "Level",
    },
)
picked = [view.iloc[i]["org_nr"] for i in selection.selection.rows] if selection and selection.selection else []
add_selected, add_top = st.columns(2)
if add_selected.button(f"Add {len(picked)} selected to shortlist", disabled=not picked, type="primary"):
    added = store.add_to_shortlist(picked, icp.name)
    st.toast(f"Added {added} to the shortlist.")
    st.rerun()
top_n = min(50, len(results))
if add_top.button(f"Add the top {top_n} to shortlist"):
    added = store.add_to_shortlist(results["org_nr"].head(top_n).tolist(), icp.name)
    st.toast(f"Added {added} to the shortlist.")
    st.rerun()
_ui.consent_note()

with st.expander("Industry breakdown of the matches"):
    breakdown = store.counts_by(icp, "nace1")
    breakdown["industry"] = breakdown["key"].map(nace.label)
    st.dataframe(pd.DataFrame(breakdown[["industry", "units"]]), hide_index=True, width="stretch")
