import pandas as pd
import streamlit as st

from pages import _ui
from prospectsignal import EMPLOYEE_BANDS, SHORTLIST_STATUSES, FitTargets, FitWeights, nace, regions, score_frame
from prospectsignal.schema import ENK_WARNING

_ui.header(
    "Step 3 · Shortlist",
    "Which ones first?",
    "Set a status and notes for each company. The optional fit score sorts the list with weights you choose; every "
    "component is shown next to the total.",
)
store = _ui.require_data()
frame = store.shortlist_frame()
if frame.empty:
    st.info("The shortlist is empty. Select companies on **ICP filters** and press “Add selected to shortlist”.")
    st.stop()

icp = _ui.current_icp()
defaults = FitTargets.from_icp(icp.validated())
with st.expander("Fit score — weights and targets", expanded=False):
    st.caption(
        "Score = weighted share of four checks, 0–100. Size: band in your target bands. Region: county in your "
        "target counties. NACE: main code matches (secondary code only = half). Age: years since founding in range."
    )
    w1, w2, w3, w4 = st.columns(4)
    weights = FitWeights(
        size=w1.slider("Size weight", 0.0, 5.0, 1.0, 0.5),
        region=w2.slider("Region weight", 0.0, 5.0, 1.0, 0.5),
        nace=w3.slider("NACE weight", 0.0, 5.0, 1.0, 0.5),
        age=w4.slider("Age weight", 0.0, 5.0, 1.0, 0.5),
    )
    t1, t2 = st.columns(2)
    bands = t1.multiselect("Target employee bands", list(EMPLOYEE_BANDS), default=list(defaults.bands))
    fylker = t2.multiselect(
        "Target counties", list(regions.FYLKER), default=list(defaults.fylker), format_func=regions.fylke_name
    )
    t3, t4 = st.columns(2)
    nace_text = t3.text_input("Target NACE prefixes", value=", ".join(defaults.nace_prefixes))
    age_range = t4.slider("Target age (years)", 0, 100, (defaults.age_min_years, defaults.age_max_years))
    try:
        prefixes = tuple(nace.parse_prefixes(nace_text)) if nace_text.strip() else ()
    except ValueError as exc:
        st.error(str(exc))
        prefixes = defaults.nace_prefixes
    targets = FitTargets(
        bands=tuple(bands),
        fylker=tuple(fylker),
        nace_prefixes=prefixes,
        age_min_years=age_range[0],
        age_max_years=age_range[1],
    )
use_score = st.toggle("Sort by fit score", value=True)
scored = score_frame(frame, targets, weights)
if use_score:
    scored = scored.sort_values(["fit_score", "employees"], ascending=[False, False], na_position="last")

counts = scored["status"].value_counts()
cols = st.columns(len(SHORTLIST_STATUSES))
for column, status in zip(cols, SHORTLIST_STATUSES):
    column.metric(status[0].upper() + status[1:], int(counts.get(status, 0)))

gone = scored.loc[~scored["in_register"].astype(bool)]
if not gone.empty:
    st.warning(
        f"{len(gone)} shortlisted unit(s) are no longer in the loaded register (deleted or removed from open data). "
        "They are kept here with your notes but left out of exports."
    )
if scored["org_form"].eq("ENK").any():
    st.warning(ENK_WARNING)

view = scored.copy()
view.insert(0, "⚠", _ui.enk_flag(view.fillna({"org_form": ""})))
view["fylke"] = view["fylke_nr"].map(lambda value: regions.fylke_name(value) if isinstance(value, str) else "")
view["remove"] = False
edited = st.data_editor(
    view,
    hide_index=True,
    width="stretch",
    height=480,
    key="shortlist_editor",
    column_order=[
        "⚠",
        "name",
        "status",
        "notes",
        "fit_score",
        "fit_size",
        "fit_region",
        "fit_nace",
        "fit_age",
        "employee_band",
        "nace1",
        "kommune",
        "fylke",
        "org_nr",
        "remove",
    ],
    disabled=[c for c in view.columns if c not in ("status", "notes", "remove")],
    column_config={
        "name": "Name",
        "kommune": "Kommune",
        "fylke": "Fylke",
        "status": st.column_config.SelectboxColumn("Status", options=list(SHORTLIST_STATUSES), required=True),
        "notes": st.column_config.TextColumn("Notes", width="large"),
        "fit_score": st.column_config.ProgressColumn("Fit", min_value=0, max_value=100, format="%d"),
        "fit_size": "Size",
        "fit_region": "Region",
        "fit_nace": "NACE",
        "fit_age": "Age",
        "employee_band": "Band",
        "nace1": "NACE code",
        "org_nr": st.column_config.TextColumn("Org.nr"),
        "remove": st.column_config.CheckboxColumn("Remove"),
    },
)

save_col, remove_col = st.columns(2)
if save_col.button("Save status and notes", type="primary"):
    original = view.set_index("org_nr")
    changed = 0
    for row in edited.itertuples():
        before = original.loc[row.org_nr]
        notes = "" if pd.isna(row.notes) else str(row.notes)
        if row.status != before["status"] or notes != (before["notes"] or ""):
            store.update_shortlist(row.org_nr, status=row.status, notes=notes)
            changed += 1
    st.toast(f"Saved {changed} change(s).")
    st.rerun()
to_remove = edited.loc[edited["remove"].astype(bool), "org_nr"].tolist()
if remove_col.button(f"Remove {len(to_remove)} marked", disabled=not to_remove):
    store.remove_from_shortlist(to_remove)
    st.rerun()
_ui.consent_note()
