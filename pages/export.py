from datetime import date

import streamlit as st

from pages import _ui
from prospectsignal import SHORTLIST_STATUSES, freddo_csv_bytes, freddo_frame, load_checklist, xlsx_bytes
from prospectsignal.errors import DataProblem

_ui.header(
    "Step 4 · Export",
    "Hand the shortlist to Freddo CRM",
    "Read the outreach checklist first. Then download a CSV in Freddo's company-import format, or an XLSX workbook "
    "with the source, licence and checklist. ProspectSignal never writes into Freddo; you choose what to import.",
)
store = _ui.require_data()
frame = store.shortlist_frame()
if frame.empty:
    st.info("The shortlist is empty. Add companies on **ICP filters** first.")
    st.stop()

_ui.consent_note()

try:
    checklist = load_checklist()
except DataProblem as exc:
    st.error(str(exc))
    st.stop()
st.markdown("### Outreach checklist")
st.markdown(
    f'<div class="ps-warning"><strong>Not legal advice.</strong> {checklist.disclaimer}</div>', unsafe_allow_html=True
)
for item in checklist.items:
    badge = "✅ verified" if not item.needs_verification else "⚠️ TODO(verify)"
    with st.expander(f"{item.title} · {item.applies_to} · {badge}"):
        st.markdown(item.rule)
        st.markdown(f"**What to do:** {item.action}")
        for source in item.sources:
            st.caption(
                f"{source.publisher}: [{source.title}]({source.url}) — {source.reference} (retrieved {source.retrieved})"
            )
st.caption(f"Checklist version {checklist.version}. Edit a copy and set PROSPECTSIGNAL_CHECKLIST to use your own.")

st.markdown("### Choose rows")
statuses = st.multiselect(
    "Include statuses", list(SHORTLIST_STATUSES), default=[s for s in SHORTLIST_STATUSES if s != "not a fit"]
)
selected = frame.loc[frame["status"].isin(statuses)]
exportable = selected.loc[selected["in_register"].astype(bool)]
st.caption(
    f"{len(exportable)} of {len(frame)} shortlisted companies will be exported"
    + (
        f" ({len(selected) - len(exportable)} no longer in the register are left out)."
        if len(exportable) < len(selected)
        else "."
    )
)
if exportable["org_form"].eq("ENK").any():
    st.warning("The export contains ENK rows. Their names identify people; handle them as personal data.")
if store.get_meta("dataset") == "demo":
    st.info("Demo export: the organisation numbers fail MOD11 on purpose, so Freddo's validator will reject them.")
st.dataframe(freddo_frame(exportable), hide_index=True, width="stretch", height=260)

acknowledged = st.checkbox(
    "I have read the outreach checklist and understand that registry data is not marketing consent."
)
today = date.today().isoformat()
csv_col, xlsx_col = st.columns(2)
csv_col.download_button(
    "Download Freddo CSV",
    data=freddo_csv_bytes(exportable) if acknowledged else b"",
    file_name=f"prospectsignal-freddo-{today}.csv",
    mime="text/csv",
    disabled=not acknowledged or exportable.empty,
    type="primary",
)
xlsx_col.download_button(
    "Download XLSX workbook",
    data=(
        xlsx_bytes(
            exportable,
            meta=store.meta(),
            checklist_rows=checklist.rows(),
            icp_lines=[_ui.current_icp().name, *_ui.current_icp().describe()],
        )
        if acknowledged
        else b""
    ),
    file_name=f"prospectsignal-shortlist-{today}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    disabled=not acknowledged or exportable.empty,
)
st.caption(
    "Freddo CSV: header on the first line, UTF-8, org.nr and postcodes as quoted text, attribution and download date "
    "in the brreg_source and brreg_refreshed_at columns of every row."
)
if st.button("Mark exported rows as “sent to CRM”", disabled=not acknowledged or exportable.empty):
    for org_nr in exportable["org_nr"]:
        store.update_shortlist(org_nr, status="sent to CRM")
    st.toast(f"Marked {len(exportable)} as sent to CRM.")
    st.rerun()
st.markdown(f"<small>{_ui.attribution_text(store)}</small>", unsafe_allow_html=True)
