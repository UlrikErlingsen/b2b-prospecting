import pandas as pd
import streamlit as st

from pages import _ui
from prospectsignal import brreg, nace, regions

_ui.header(
    "Sources & boundaries",
    "What ProspectSignal uses, and what it refuses to do",
    "Every external fact below was checked against an official source on the date shown. Open questions are marked "
    "TODO(verify) rather than guessed.",
)

st.markdown("### Data sources")
sources = pd.DataFrame(
    [
        (
            "Company register",
            "Enhetsregisteret bulk CSV + REST API, Brønnøysundregistrene",
            brreg.LICENCE_NAME,
            brreg.DOCS_URL,
        ),
        (
            "Industry code names",
            "SN2025, SSB Klass (classification 6, version 3218)",
            "CC BY 4.0",
            "https://www.ssb.no/klass/klassifikasjoner/6",
        ),
        (
            "County map",
            "Administrative enheter fylker, Kartverket (simplified)",
            "CC BY 4.0",
            "https://kartkatalog.geonorge.no/metadata/6093c8a8-fa80-11e6-bc64-92361f002671",
        ),
        (
            "Outreach checklist",
            "Lovdata, Forbrukertilsynet, Datatilsynet, Brønnøysundregistrene",
            "Summaries with links",
            "see Export page",
        ),
    ],
    columns=["What", "Source", "Licence", "Link"],
)
st.dataframe(sources, hide_index=True, width="stretch")
st.caption(f"{nace.NACE_SOURCE} {regions.MAP_SOURCE}")

st.markdown("### Verified register facts (2026-10-01)")
st.markdown(
    "- Bulk files are produced nightly around 05:00; `etag` and `last-modified` show whether a file changed.\n"
    "- The search API returns at most 10,000 units per query, so the bulk file is the supported way to get the whole register.\n"
    "- Employee counts below five are hidden: `antallAnsatte` is empty and `harRegistrertAntallAnsatte` tells 0 from 1–4.\n"
    "- Units removed from open data (“Fjernet”) must be removed from copies; a full reload does that.\n"
    "- Industry codes follow SN2025 since 1 January 2025; Viken (30) was split into Østfold, Akershus and Buskerud on 1 January 2024.\n"
    "- NLOD § 5 requires attribution and marking of changes; § 3 excludes personal data without a lawful basis."
)
st.markdown("### Open questions — TODO(verify)")
st.markdown(
    "- **Rate limits:** the API documentation publishes none. ProspectSignal calls the API only on request, one call at a time.\n"
    "- **Deleted units in single lookups:** the documented status code for a deleted unit is not stated; 404 and 410 are both treated as “not in open data”.\n"
    "- **Financial statements:** the open accounts API's terms of use are not confirmed, so v1 shows no financials.\n"
    "- **Freddo import:** Freddo's own importer is planned, not built; the CSV targets the CRM Organization fields Freddo defines. "
    "How Frappe's Data Import treats read-only and unmapped columns needs a test once the importer exists.\n"
    "- **ENK and telemarketing:** whether a call to a sole proprietor counts as a call to a consumer is not settled in the sources fetched."
)
st.markdown("### Hard boundaries")
_ui.boundary(
    "No personal data: roles, e-mail addresses and phone numbers are never read, ENK street addresses are never "
    "stored, and ENK is excluded by default. No scraping of websites, LinkedIn or Proff. No telemetry, accounts or "
    "external AI calls. Registry data is never treated as marketing consent. Freddo receives only a file you choose "
    "to import."
)
st.markdown("### Relationship to Freddo CRM")
st.markdown(
    "Freddo's rule is that *NACE counts may size a market; they never become a contact list.* ProspectSignal is the "
    "separate tool where a deliberate shortlist is allowed. The bridge is one-way and manual: export a CSV here, then "
    "decide in Freddo whether to import it. People are never part of the bridge."
)
