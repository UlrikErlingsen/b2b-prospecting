import streamlit as st

from pages import _ui

st.markdown(
    """
    <section class="ps-hero">
      <div class="ps-eyebrow">NORWEGIAN B2B PROSPECTING · OPEN REGISTER DATA</div>
      <h1>Which companies fit your ICP — and <em>which first?</em></h1>
      <p>Filter Enhetsregisteret by industry, county, size and age; see how big the market is; shortlist the
      companies worth a closer look; and hand the shortlist to Freddo CRM. Everything runs on your computer.</p>
      <div class="ps-pills"><span class="ps-pill">NACE hierarchy (SN2025)</span>
      <span class="ps-pill">fylke &amp; kommune</span><span class="ps-pill">employee bands</span>
      <span class="ps-pill">market counts &amp; map</span><span class="ps-pill">shortlist with notes</span>
      <span class="ps-pill">visible fit weights</span><span class="ps-pill">Freddo CSV export</span></div>
    </section>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="ps-grid">
      <div class="ps-card"><b>01 · FILTER</b><h3>Describe your ideal customer</h3><p>Industry codes with their
      hierarchy (10 → 10.1 → 10.11), county or kommune, employee range, founding dates, legal form, VAT status.
      Inactive companies and sole proprietorships are excluded by default.</p></div>
      <div class="ps-card"><b>02 · SIZE</b><h3>See the market before the names</h3><p>Counts by county, industry,
      size band and registration year, with a county map. Counts size a market; they are not a contact list.</p></div>
      <div class="ps-card"><b>03 · SHORTLIST</b><h3>Choose deliberately, then export</h3><p>Pick companies, set a
      status and notes, sort by a fit score whose weights you can see, read the outreach checklist, and export a
      CSV in Freddo CRM's import format.</p></div>
    </div>
    """,
    unsafe_allow_html=True,
)

if _ui.dataset() == "demo":
    st.info(
        "You are looking at the **offline demo**: about 2,000 fictional companies, labelled DEMO, with organisation "
        "numbers that fail the MOD11 check on purpose. The demo ICP is “Fjellbrus — food & beverage producers, "
        "former Viken, 10–100 employees”. Load the real register on **Data & register**."
    )

st.markdown("### Workflow")
st.markdown(
    "1. **ICP filters** — adjust or save the ideal customer profile and read the matching count.\n"
    "2. **Market size** — counts by county, industry, size and year.\n"
    "3. **Shortlist** — select companies, set status and notes, weigh the fit score.\n"
    "4. **Export** — read the outreach checklist, then download the Freddo CSV or the XLSX workbook."
)
_ui.boundary(
    "<strong>Hard boundaries.</strong> ProspectSignal reads only Brønnøysundregistrene's open Enhetsregisteret data. "
    "It never imports roles (board members, CEO, contact persons), e-mail addresses or phone numbers; never "
    "scrapes websites, LinkedIn or Proff; and has no telemetry, accounts or external AI calls. Export to Freddo is "
    "a file you choose to import — ProspectSignal never writes into the CRM."
)
_ui.consent_note()
