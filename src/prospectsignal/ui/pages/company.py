"""Company card: registry facts for one unit, official register link, registered website."""

from __future__ import annotations

import streamlit as st

from prospectsignal import brreg, nace, orgnr, regions
from prospectsignal.errors import RegisterUnavailable
from prospectsignal.schema import ENK_WARNING, PERSON_NAME_FORMS
from prospectsignal.ui import common as ui
from prospectsignal.ui.common import k


def render() -> None:
    ui.header(
        "Company card",
        "Registry facts for one company",
        "Everything here comes from Enhetsregisteret. Financial statements are not shown in v1: the terms of the open "
        "accounts API (Regnskapsregisteret) are not yet verified.",
    )
    store = ui.require_data()
    if store is None:
        return
    query = st.text_input(
        "Search by name or organisation number",
        value=st.session_state.get(k("company_query"), ""),
        key=k("company_search"),
    )
    if not query.strip():
        st.caption("Type part of a company name, or a nine-digit organisation number.")
        return
    st.session_state[k("company_query")] = query
    hits = store.find_units(orgnr.normalise(query) if orgnr.normalise(query).isdigit() else query)
    if hits.empty:
        st.info("No unit in the loaded data matches that search.")
        return
    labels = {
        row.org_nr: f"{row.name} · {orgnr.format_display(row.org_nr)} · {row.org_form} · {row.kommune or ''}"
        for row in hits.itertuples()
    }
    chosen = st.selectbox("Matches", list(labels), format_func=labels.get, key=k("company_match"))
    unit = store.get_unit(chosen)

    st.markdown(f"## {unit['name']}")
    if unit["is_demo"]:
        st.info(
            "Fictional DEMO company. Its organisation number fails MOD11 on purpose and does not exist in the register."
        )
    if unit["org_form"] in PERSON_NAME_FORMS:
        st.warning(ENK_WARNING)
    flags = [
        label
        for key, label in (
            ("bankrupt", "Bankrupt (konkurs)"),
            ("winding_up", "Under liquidation (under avvikling)"),
            ("forced_winding_up", "Forced liquidation or dissolution"),
            ("closed", "Closed sub-unit (nedlagt)"),
        )
        if unit.get(key)
    ]
    if flags:
        st.error("Status: " + ", ".join(flags))

    left, right = st.columns(2)
    with left:
        st.markdown(
            f"**Organisation number:** {orgnr.format_display(unit['org_nr'])}  \n"
            f"**Level:** {unit['entity_kind']}"
            + (f" (parent {orgnr.format_display(unit['parent_org_nr'])})" if unit.get("parent_org_nr") else "")
            + f"  \n**Legal form:** {unit['org_form']} — {unit['org_form_desc'] or ''}  \n"
            f"**Founded:** {ui.date_text(unit['founded'])}  \n"
            f"**Registered in Enhetsregisteret:** {ui.date_text(unit['registered'])}  \n"
            f"**VAT-registered:** {'yes' if unit['vat_registered'] else 'no'}  \n"
            f"**In Foretaksregisteret:** {'yes' if unit['in_business_register'] else 'no'}"
        )
    with right:
        employees = unit["employees"]
        st.markdown(
            f"**Employees:** {employees if employees is not None else ('1–4' if unit['has_employees'] else '0')} "
            f"(band {unit['employee_band']})  \n"
            f"**Address:** {unit['address'] or '—'}  \n"
            f"**Postcode / place:** {unit['postcode'] or ''} {unit['poststed'] or ''}  \n"
            f"**Kommune / fylke:** {(unit['kommune'] or '').title()} · {regions.fylke_name(unit['fylke_nr'])}"
        )
    codes = [(unit[f"nace{i}"], unit[f"nace{i}_desc"]) for i in (1, 2, 3) if unit[f"nace{i}"]]
    st.markdown("**Industry codes:** " + "; ".join(f"{code} {desc or nace.name(code)}" for code, desc in codes))
    if unit.get("activity"):
        st.markdown(f"**Registered activity:** {unit['activity']}")

    links = []
    if not unit["is_demo"]:
        links.append(f"[Official register page]({brreg.register_url(unit['org_nr'], unit['entity_kind'])})")
    if unit.get("website") and not unit["is_demo"]:
        site = unit["website"] if unit["website"].startswith(("http://", "https://")) else f"https://{unit['website']}"
        links.append(f"[Website (as registered)]({site})")
    if links:
        st.markdown(" · ".join(links))
    st.caption(f"Source: {unit['source']} · downloaded {ui.date_text(unit['downloaded_at'])}")

    a, b = st.columns(2)
    if a.button("Add to shortlist", type="primary", key=k("card_add")):
        added = store.add_to_shortlist([unit["org_nr"]], "company card")
        st.toast("Added to the shortlist." if added else "Already on the shortlist.")
    if b.button(
        "Refresh from Brønnøysundregistrene",
        disabled=ui.hub_mode() or ui.dataset() != "register",
        help="Off in Signal Hub; run Prospect Signal locally." if ui.hub_mode() else None,
        key=k("card_refresh"),
    ):
        try:
            record = brreg.refresh_unit(store, unit["org_nr"])
            st.toast("Updated from the API." if record else "No longer in open data; removed locally.")
            st.rerun()
        except RegisterUnavailable as exc:
            st.error(str(exc))
    ui.consent_note()
