"""Data & register page: offline demo, bulk load of the real register, single-unit refresh, licence."""

from __future__ import annotations

import streamlit as st

from prospectsignal import brreg, load_demo, orgnr
from prospectsignal.errors import DataProblem, RegisterUnavailable
from prospectsignal.ui import common as ui
from prospectsignal.ui.common import k


def _load_register_section() -> None:
    st.markdown("### Load the real register")
    st.markdown(
        "Prospect Signal downloads the official bulk CSV of **Enhetsregisteret** (about 150 MB compressed, produced "
        "every night around 05:00), then indexes it locally in DuckDB. The download date is stored on every row. "
        "Optionally it also loads **underenheter** (sub-units such as branches and plants) so you can filter on "
        "where work actually happens. Nothing about people is read: no roles, e-mail addresses or phone numbers."
    )
    include_sub = st.checkbox(
        "Also load underenheter (sub-units / locations, about 60 MB more)", value=False, key=k("include_sub")
    )
    check_col, load_col = st.columns([1, 1])
    if check_col.button("Check today's file", key=k("check_file")):
        try:
            headers = brreg.bulk_headers("enheter")
            size = int(headers.get("content-length", 0)) / 1_000_000
            st.success(f"Enheter file: {size:,.0f} MB, published {headers.get('last-modified', 'unknown')}.")
        except RegisterUnavailable as exc:
            st.error(str(exc))

    if load_col.button("Load real register", type="primary", key=k("load_register")):
        bar = st.progress(0.0, text="Starting download…")
        status = st.empty()

        def progress(kind: str, done: int, total: int | None) -> None:
            if total:
                bar.progress(
                    min(done / total, 1.0), text=f"Downloading {kind}: {done / 1e6:,.0f} of {total / 1e6:,.0f} MB"
                )
            else:
                bar.progress(0.5, text=f"Downloading {kind}: {done / 1e6:,.0f} MB")

        try:
            with st.spinner("Downloading and indexing…"):
                summary = brreg.load_register(
                    ui.register_store(),
                    ui.data_dir(),
                    include_underenheter=include_sub,
                    progress=progress,
                    on_indexing=lambda message: status.info(message),
                )
            bar.progress(1.0, text="Done")
            counts = summary["counts"]
            st.session_state[k("flash")] = (
                f"Indexed {counts['hovedenheter']:,} hovedenheter"
                + (f" and {counts['underenheter']:,} underenheter" if counts["underenheter"] else "")
                + f" (downloaded {summary['downloaded_at']}). Switched to the real register."
            )
            ui.request_dataset("register")
            st.rerun()
        except (RegisterUnavailable, DataProblem) as exc:
            bar.empty()
            status.error(str(exc))

    st.markdown("### Refresh one company from the API")
    st.caption(
        "Fetches a single unit from data.brreg.no and updates the local copy (real register only). If the unit is no "
        "longer in open data, the local copy is removed, as the API documentation requires."
    )
    with st.form(key=k("refresh_one")):
        number = st.text_input("Organisation number", placeholder="974 760 673", key=k("refresh_orgnr"))
        submitted = st.form_submit_button("Refresh from Brønnøysundregistrene", key=k("refresh_submit"))
    if submitted:
        if ui.dataset() != "register":
            st.warning("Switch to the real register first; demo companies are fictional and not in the API.")
        elif not orgnr.is_valid(number):
            st.error("That is not a valid organisation number (nine digits with a MOD11 check digit).")
        else:
            try:
                record = brreg.refresh_unit(ui.register_store(), number)
                if record is None:
                    st.warning("Not found in open data; any local copy was removed.")
                else:
                    st.success(f"Updated {record['name']} ({record['entity_kind']}).")
            except RegisterUnavailable as exc:
                st.error(str(exc))


def render() -> None:
    ui.header(
        "Data & register",
        "Where the data comes from",
        "The offline demo works without network. The real register comes from Brønnøysundregistrene's nightly bulk "
        "file (open data, NLOD licence) and is indexed into a local database on this computer.",
    )

    if k("flash") in st.session_state:
        st.success(st.session_state.pop(k("flash")))

    current = ui.store()
    meta = current.meta()
    left, middle, right = st.columns(3)
    left.metric("Active dataset", "Demo" if ui.dataset() == "demo" else "Real register")
    middle.metric("Units stored", f"{current.unit_count():,}")
    right.metric("Downloaded", meta.get("downloaded_at") or "—")
    st.caption(ui.attribution_text(current))

    if ui.hub_mode():
        st.markdown("### Load the real register")
        ui.hub_note()
    else:
        _load_register_section()

    st.markdown("### Licence and attribution")
    ui.boundary(
        f"{brreg.ATTRIBUTION}\n\n{brreg.ATTRIBUTION_EN}\n\nLicence: [{brreg.LICENCE_NAME}]({brreg.LICENCE_URL}) · "
        f"Documentation: [data.brreg.no]({brreg.DOCS_URL})"
    )
    st.markdown(
        "**Stored per unit:** name, organisation number (as text), legal form, industry codes, employee count and "
        "band, founding and registration dates, VAT and business-register flags, bankruptcy/liquidation flags, "
        "business address (street address blank for ENK), postcode, kommune, fylke, website, download date.\n\n"
        "**Never stored:** roles (board, CEO, contact persons), e-mail addresses, phone and mobile numbers, birth "
        "numbers, annotations. Financial statements are not included in v1 (the terms of the open accounts API are "
        "not yet verified)."
    )

    with st.expander("Reset the offline demo"):
        st.caption("Rebuilds the fictional demo data. The demo shortlist and saved demo ICPs are kept.")
        if st.button("Rebuild demo data", key=k("rebuild_demo")):
            load_demo(ui.demo_store())
            st.success("Demo data rebuilt.")
