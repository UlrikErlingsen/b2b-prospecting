# AGENTS.md — ProspectSignal (repo: b2b-prospecting)

You are building **ProspectSignal**, a new product in Ulrik Erlingsen's **Signal** suite
(open-source, local-first marketing tools; see sibling repos such as `brand-tracking`
= TrackSignal for house style, and `signal-crm` = Freddo CRM). This repo starts empty except
for this file, a README stub, LICENSE and .gitignore. Build v1 from this brief.

## What it is

An open, local-first **B2B prospecting tool for the Norwegian market**, built on the open
Enhetsregisteret data from Brønnøysundregistrene. Free alternative to paid tools such as
Proff Forvalt, Vainu, Enin and Infobel for small sales and marketing teams.

## The question it answers

> Which Norwegian companies fit our ideal customer profile, how big is that market,
> and which ones should we look at first?

## Relationship to Freddo CRM (important)

Freddo has a binding rule: "NACE counts may size a market. They never become a contact list."
ProspectSignal is the **separate** tool where shortlists are allowed. The bridge is one-way and
manual: ProspectSignal exports a shortlist (CSV in Freddo's file-import format: org.nr as a
string, name, address, NACE, employee band), and the user chooses to import it into Freddo.
Never write into Freddo directly; never import people.

## v1 scope

1. **Data loader** — prefer the official **bulk download** of Enhetsregisteret (and
   underenheter) over thousands of API calls; fall back to the REST API
   (`https://data.brreg.no/enhetsregisteret/api/...`) for single lookups and refresh.
   *Read the official API documentation first and verify endpoints, query parameters, bulk
   file format, rate limits and the NLOD licence + attribution requirement before coding.*
   Store locally in DuckDB or SQLite; record download date per row.
2. **ICP filters** — NACE code(s) incl. hierarchy (e.g. 10 → 10.1 → 10.11), fylke/kommune,
   employee band, founded date range, organisation form (AS, ENK, …), VAT-registered,
   exclude konkurs/under avvikling/slettet. Save filter sets as named ICPs.
3. **Market view** — counts by region, NACE and size band; new registrations per year;
   map by fylke (plotly choropleth with a bundled GeoJSON, source and licence noted).
4. **Shortlist** — results table, select companies into a shortlist with status
   (new / researching / qualified / not a fit / sent to CRM) and notes. Optional simple
   fit score with **visible, user-set weights** (size band, region, NACE match, age).
5. **Company card** — registry facts, link to the official register page, hjemmeside if
   registered. Financials only if an open, documented source allows it (verify the
   Regnskapsregisteret API terms first; otherwise leave out).
6. **Export** — CSV in Freddo import format, XLSX, with the attribution line and download date.
7. **Outreach checklist** (configurable YAML, not legal advice) — shown before export:
   contacting a company vs a named person, email marketing consent rules, telemarketing and
   Reservasjonsregisteret, GDPR legitimate-interest note. *Seed every rule only from fetched
   official sources (Forbrukertilsynet, Brønnøysundregistrene, Datatilsynet) with URLs; mark
   anything uncertain `TODO(verify)`.*

## Hard rules

- **No personal data.** Do not import roller (board members, CEO, contact persons) or any
  person field, even though the registry exposes them. ENK companies carry a person's name
  as the company name: show a warning on ENK rows and exclude ENK by default.
- Registry data never implies marketing consent — say so on the shortlist and export screens.
- No scraping of websites, LinkedIn or Proff. Open registry data only.
- No telemetry, no accounts, no external AI calls.

## Demo

The real register is public, so the demo can use it — but ship an **offline demo** too:
a small fictional dataset (`src/prospectsignal/demo.py`, ~2,000 fictional companies with
fake org.nr that fail MOD11 on purpose and are labelled DEMO) so the app runs without network.
Demo ICP: "Food & beverage producers in Viken/Østfold, 10–100 employees" for fictional
brand "Fjellbrus".

## Stack and house style (match other Signal repos)

- Python 3.10+, Streamlit `app.py`, package `src/prospectsignal/`, tests in `tests/`.
- pandas, duckdb (or sqlite3), requests, plotly, openpyxl, pyyaml.
- Streamlit only in `app.py`, `pages/` and `src/prospectsignal/ui/`: nothing else under `src/prospectsignal/`
  imports Streamlit (guard test). `ui/` holds the shared Signal theme (`signal_theme.py`, `assets/marks/`),
  synced from Signal Hub with `.streamlit/config.toml` and `assets/prospectsignal-*`; never edit those copies.
- Page code lives in `src/prospectsignal/ui/pages/` (`pages/*.py` only wrap it). `prospectsignal.ui.render()` is the
  Signal Hub entry point (no `st.set_page_config`/`st.navigation`/`st.stop`; keys via `k()` = `prospect:...`). With
  `SIGNAL_HUB=1` the app uses the in-memory demo only: no files, no Brønnøysund calls. See Signal Hub `docs/APP_CONTRACT.md`.
- Display name is **Prospect Signal** (with a space) in user-facing text; technical identifiers
  (`prospectsignal`, `PROSPECTSIGNAL_*`, file slugs) stay unchanged.
- `pyproject.toml` (setuptools, AGPL-3.0-or-later, author "Ulrik Erlingsen"), `requirements.txt`,
  `Dockerfile`, `run_app.bat` — mirror `brand-tracking`.
- ruff (line length 120) + pytest with recorded API fixtures (no live calls in tests).
  Tests: org.nr as string + MOD11, leading-zero postcodes, Æ/Ø/Å, NACE hierarchy filter,
  ENK exclusion, no person fields in storage or export, Freddo CSV format.
- README in TrackSignal's structure; CHANGELOG, SECURITY, PRIVACY, CONTRIBUTING.

## Definition of done for v1

- `run_app.bat` opens with the offline demo; "Load real register" downloads and indexes the
  bulk file with a progress bar.
- An ICP filter on real data returns counts and a shortlist in seconds.
- Export opens cleanly in Freddo's file importer format; attribution line present.
- `pytest` and `ruff check` pass; screenshots in `assets/`.

## Working rules

- Ulrik commits and pushes from **GitHub Desktop** himself; you do not push.
- Small logical commits; short summary at the end of each session.
- When unsure about an API detail or a legal rule, leave `TODO(verify)` and say so; never guess.
