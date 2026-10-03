"""Welcome page."""

from __future__ import annotations

import streamlit as st

from prospectsignal.ui import common as ui
from prospectsignal.ui import signal_theme as sig


def render() -> None:
    sig.hero(
        ui.KEY,
        eyebrow="NORWEGIAN B2B PROSPECTING · OPEN REGISTER DATA",
        title="Which companies fit your ICP — and",
        em="which first?",
        body=(
            "Filter Enhetsregisteret (Norway's central register of legal entities) by industry, county, size and age; see how big the market is; shortlist the "
            "companies worth a closer look; and hand the shortlist to Freddo CRM. Everything runs on your computer."
        ),
        pills=[
            "NACE hierarchy (SN2025)",
            "county & municipality",
            "employee bands",
            "market counts & map",
            "shortlist with notes",
            "visible fit weights",
            "Freddo CSV export",
        ],
    )
    sig.cards(
        [
            (
                "01 · FILTER",
                "Describe your ideal customer",
                "Industry codes with their hierarchy (10 → 10.1 → 10.11), county or municipality, employee range, founding "
                "dates, legal form, VAT status. Inactive companies and sole proprietorships are excluded by default.",
            ),
            (
                "02 · SIZE",
                "See the market before the names",
                "Counts by county, industry, size band and registration year, with a county map. Counts size a "
                "market; they are not a contact list.",
            ),
            (
                "03 · SHORTLIST",
                "Choose deliberately, then export",
                "Pick companies, set a status and notes, sort by a fit score whose weights you can see, read the "
                "outreach checklist, and export a CSV in Freddo CRM's import format.",
            ),
        ]
    )

    if ui.dataset() == "demo":
        st.info(
            "You are looking at the **offline demo**: about 2,000 fictional companies, labelled DEMO, with "
            "organisation numbers that fail the MOD11 check on purpose. The demo ICP is “Fjellbrus — food & beverage "
            "producers, former Viken, 10–100 employees”."
            + ("" if ui.hub_mode() else " Load the real register on **Data & register**.")
            + " "
            + ui.DEMO_LANGUAGE_NOTE
        )
    if ui.hub_mode():
        ui.hub_note()

    st.markdown("### Workflow")
    st.markdown(
        "1. **ICP filters** — adjust or save the ideal customer profile and read the matching count.\n"
        "2. **Market size** — counts by county, industry, size and year.\n"
        "3. **Shortlist** — select companies, set status and notes, weigh the fit score.\n"
        "4. **Export** — read the outreach checklist, then download the Freddo CSV or the XLSX workbook."
    )
    ui.boundary(
        "**Hard boundaries.** Prospect Signal reads only Brønnøysundregistrene's open Enhetsregisteret data. "
        "It never imports roles (board members, CEO, contact persons), e-mail addresses or phone numbers; never "
        "scrapes websites, LinkedIn or Proff; and has no telemetry, accounts or external AI calls. Export to Freddo "
        "is a file you choose to import — Prospect Signal never writes into the CRM."
    )
    ui.consent_note()
