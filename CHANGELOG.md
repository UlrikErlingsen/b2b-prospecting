# Changelog

## 1.0.0 — 2026-10-01

First release of **ProspectSignal**, the Signal suite's prospecting tool for the Norwegian market.

### Application

- Offline demo with about 2,000 fictional companies (plus sub-units): names labelled DEMO, organisation numbers that start with 0 and fail MOD11 on purpose, `.example` websites. Demo ICP “Fjellbrus — food & beverage producers, former Viken, 10–100 employees”.
- **Load real register**: streams Brønnøysundregistrene's nightly Enhetsregisteret bulk CSV (optionally underenheter) with a progress bar and indexes it into a local DuckDB file; download date and file publication time stored on every row; atomic swap keeps old data if a load fails or the format changes.
- Single-unit refresh from the REST API; units no longer in open data are removed locally.
- ICP filters: SN2025 industry codes at any hierarchy level (sections expand to divisions), secondary-code matching, fylke (with a former-Viken alias) and kommune, employee range that respects the register's hidden 1–4 counts, founding dates, organisation form, VAT status, inactive-unit exclusion, unit level. Named ICPs are saved locally.
- Market view: counts by county (bundled Kartverket map), industry division, employee band, organisation form and registration year. Counts only.
- Shortlist with status and notes, and an optional fit score whose four weights and components are visible.
- Company card with registry facts, official register link and registered website.
- Exports: Freddo CRM CSV (header-first, org.nr and postcodes as text, attribution and download date in every row) and an XLSX workbook with source, licence, ICP and checklist sheets. Formula-injection-safe.
- Outreach checklist (YAML, configurable, not legal advice) seeded only from Lovdata, Forbrukertilsynet, Datatilsynet and Brønnøysundregistrene, with URLs, retrieval dates and `TODO(verify)` markers; shown and acknowledged before export.

### Boundaries

- No person data: roles, e-mail addresses and phone numbers are never read; ENK excluded by default, flagged, and stored without street address.
- Registry data is described as not marketing consent on the shortlist and export screens.
- No scraping, telemetry, accounts or external AI calls. Network calls only to Brønnøysundregistrene, on request, with TLS verified against the OS trust store.

### Architecture

- All logic under `src/prospectsignal/` without Streamlit; Streamlit only in `app.py` and `pages/`; all SQL behind `storage.py`; public API in `prospectsignal/__init__.py`; tests enforce these rules.
