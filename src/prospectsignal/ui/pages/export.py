"""Step 4 · Export: outreach checklist, then the Freddo CSV or the XLSX workbook (built in memory)."""

from __future__ import annotations

from datetime import date

import streamlit as st

from prospectsignal import SHORTLIST_STATUSES, freddo_csv_bytes, freddo_frame, xlsx_bytes
from prospectsignal.errors import DataProblem
from prospectsignal.ui import common as ui
from prospectsignal.ui import signal_theme as sig
from prospectsignal.ui.common import k


def render() -> None:
    ui.header(
        "Step 4 · Export",
        "Hand the shortlist to Freddo CRM",
        "Read the outreach checklist first. Then download a CSV in Freddo's company-import format, or an XLSX "
        "workbook with the source, licence and checklist. Prospect Signal never writes into Freddo; you choose what "
        "to import.",
    )
    store = ui.require_data()
    if store is None:
        return
    frame = store.shortlist_frame()
    if frame.empty:
        st.info("The shortlist is empty. Add companies on **ICP filters** first.")
        return

    ui.consent_note()

    try:
        checklist = ui.load_checklist()
    except DataProblem as exc:
        st.error(str(exc))
        return
    st.markdown("### Outreach checklist")
    sig.note("warn", f"**Not legal advice.** {checklist.disclaimer}")
    for item in checklist.items:
        badge = "✅ verified" if not item.needs_verification else "⚠️ TODO(verify)"
        with st.expander(f"{item.title} · {item.applies_to} · {badge}"):
            st.markdown(item.rule)
            st.markdown(f"**What to do:** {item.action}")
            for source in item.sources:
                st.caption(
                    f"{source.publisher}: [{source.title}]({source.url}) — {source.reference} "
                    f"(retrieved {source.retrieved})"
                )
    if ui.hub_mode():
        st.caption(f"Checklist version {checklist.version} (the bundled checklist; custom checklists run locally).")
    else:
        st.caption(
            f"Checklist version {checklist.version}. Edit a copy and set PROSPECTSIGNAL_CHECKLIST to use your own."
        )

    st.markdown("### Choose rows")
    statuses = st.multiselect(
        "Include statuses",
        list(SHORTLIST_STATUSES),
        default=[s for s in SHORTLIST_STATUSES if s != "not a fit"],
        key=k("export_statuses"),
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
    if ui.has_person_name_forms(exportable):
        st.warning(
            "The export contains ENK rows (or sub-units with an unknown legal form). Their names can identify people; "
            "handle them as personal data."
        )
    if store.get_meta("dataset") == "demo":
        st.info("Demo export: the organisation numbers fail MOD11 on purpose, so Freddo's validator will reject them.")
    st.dataframe(freddo_frame(exportable), hide_index=True, width="stretch", height=260)

    acknowledged = st.checkbox(
        "I have read the outreach checklist and understand that registry data is not marketing consent.",
        key=k("export_ack"),
    )
    today = date.today().isoformat()
    icp = ui.current_icp()
    csv_col, xlsx_col = st.columns(2)
    csv_col.download_button(
        "Download Freddo CSV",
        data=freddo_csv_bytes(exportable) if acknowledged else b"",
        file_name=f"prospectsignal-freddo-{today}.csv",
        mime="text/csv",
        disabled=not acknowledged or exportable.empty,
        type="primary",
        key=k("download_csv"),
    )
    xlsx_col.download_button(
        "Download XLSX workbook",
        data=(
            xlsx_bytes(
                exportable,
                meta=store.meta(),
                checklist_rows=checklist.rows(),
                icp_lines=[icp.name, *icp.describe()],
            )
            if acknowledged
            else b""
        ),
        file_name=f"prospectsignal-shortlist-{today}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        disabled=not acknowledged or exportable.empty,
        key=k("download_xlsx"),
    )
    st.caption(
        "Freddo CSV: header on the first line, UTF-8, org.nr and postcodes as quoted text, attribution and download "
        "date in the brreg_source and brreg_refreshed_at columns of every row."
    )
    if st.button(
        "Mark exported rows as “sent to CRM”", disabled=not acknowledged or exportable.empty, key=k("mark_sent")
    ):
        for org_nr in exportable["org_nr"]:
            store.update_shortlist(org_nr, status="sent to CRM")
        st.toast(f"Marked {len(exportable)} as sent to CRM.")
        st.rerun()
    sig.note("muted", ui.attribution_text(store))
