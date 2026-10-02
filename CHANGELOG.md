# Changelog

## [1.0.0] - 2026-10-02

First release of **Prospect Signal**, the Signal suite's prospecting tool for the Norwegian market, with the Signal brand and the Signal Hub entry point.

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

- No person data: roles, e-mail addresses and phone numbers are never read; ENK excluded by default, flagged, and stored without street address. Sub-units whose parent is missing from open data (legal form unknown) get the same treatment.
- Registry data is described as not marketing consent on the shortlist and export screens.
- No scraping, telemetry, accounts or external AI calls. Network calls only to Brønnøysundregistrene, on request, with TLS verified against the OS trust store.

### Architecture

- All logic under `src/prospectsignal/` without Streamlit; Streamlit only in `src/prospectsignal/ui/` (plus the thin `app.py` and `pages/` wrappers); all SQL behind `storage.py`; public API in `prospectsignal/__init__.py`; tests enforce these rules.

### Signal brand

- The app uses the shared Signal theme (`prospectsignal.ui.signal_theme`, synced from Signal Hub): Organic look with the Market family colour `#728157`, Figtree, the shared sidebar lockup, masthead, hero, cards, page headers, notes and footer.
- Market charts use the per-app Signal Plotly template and the family sequential scale instead of hard-coded colours, shown with `sig.chart` so Streamlit's chart theme does not override Figtree and the palette.
- Display name is now **Prospect Signal** (with a space) in the app, messages, attribution line, export metadata, launchers and docs. Technical identifiers (`prospectsignal`, `PROSPECTSIGNAL_*`, file slugs, HTTP user agent) are unchanged.
- README follows the Signal README template (banner PNG, family badges, template section order, where-this-fits table, references, suite footer).
- The architecture rule now reads "no Streamlit under `src/` except `src/prospectsignal/ui/`" (guard test, CLAUDE.md, AGENTS.md, CONTRIBUTING, PR template); a new test keeps the core package from importing the ui layer.
- README screenshots re-taken in the Signal theme on the offline demo; `scripts/take_screenshots.py` now waits for the shared `.sg-mast` masthead.
- Figtree is embedded from the synced `prospectsignal.ui.signal_font` (Latin subset, OFL licence included), so the app makes no Google Fonts request.
- Synced brand assets (`assets/prospectsignal-banner.png`, `-social.png`, `-mark-32/64/512.png`; the old banner SVG is removed), theme marks shipped as `prospectsignal.ui` package data, and the synced `.streamlit/config.toml`.
- Issue templates (bug report, feature request, config) and brand tests.

### Signal Hub

- `prospectsignal.ui` exposes `APP_INFO` and `render()`, which draws the whole app (theme, sidebar lockup, a namespaced page radio, masthead, the selected page, footer) without `st.set_page_config`, `st.navigation` or `st.stop`. The page code moved into `prospectsignal.ui.pages`, so an installed package has it; `pages/*.py` are thin wrappers and the standalone app keeps its `st.navigation` layout and URLs.
- Every session-state and widget key is namespaced `prospect:` through one `k()` helper.
- Hub mode (`SIGNAL_HUB=1`): the fictional offline demo runs in an in-memory DuckDB per browser session. No database file is opened, no earlier local workspace is read, Brønnøysundregistrene is never called (the register loader and single-unit refresh are hidden or disabled with a note), and the bundled outreach checklist is used instead of a local override file. Standalone behaviour is unchanged.
- `ui` optional extra for Streamlit (`app` kept as an alias); `requirements.txt` still installs everything.
- Contract tests (entry point, Streamlit only under `ui/`, fresh-interpreter core import, render from the packaged files alone, namespaced keys) and hub-mode tests (every page renders, nothing written to the working, home or app-data folders, only `:memory:` databases, no network, no person columns, one database per session).
