# Sources and verified facts

Every external fact Prospect Signal relies on, where it came from, and when it was checked. Anything that could not be confirmed from an official source is listed under *Open questions* and marked `TODO(verify)` in the code.

All checks below were made on **1 October 2026**.

## Brønnøysundregistrene — Enhetsregisteret open data

Source: [API documentation](https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/index.html) (OpenAPI 2.0.0) and live responses.

| Fact | How it is used |
|---|---|
| Bulk CSV: `GET /enhetsregisteret/api/enheter/lastned/csv` (gzip, ~155 MB, `application/vnd.brreg.enhetsregisteret.enhet.v2+gzip`); underenheter at `/underenheter/lastned/csv` (~61 MB gzip, 866,726 units). | `brreg.BULK_URLS`, streamed download with progress. |
| Bulk files are produced every night around 05:00; `etag` and `last-modified` headers identify a version. | Stored per load as metadata; `last-modified` is stored on every row. |
| CSV cells are all quoted and can contain line breaks and doubled quotes. | DuckDB `read_csv(..., quote='"', escape='"', parallel=false)`; multi-line addresses are joined with “, ”. |
| Search (`/api/enheter`) is limited to 10,000 results per query ((page+1)·size ≤ 10,000); the documentation points to the bulk download for the full set. | Bulk download is the primary loader; REST is used for single lookups only. |
| Single lookups `/api/enheter/{orgnr}` and `/api/underenheter/{orgnr}`; an unknown number returns 404; an invalid number returns 400. | `brreg.fetch_unit` (validates MOD11 before calling). |
| Copies must delete units published as “Fjernet” (removed from open data). | A full reload replaces the table; a single refresh that finds nothing removes the local row. |
| Since API v2, `antallAnsatte` is null for 0–4 employees; `harRegistrertAntallAnsatte` distinguishes 0 from 1–4; the search API rejects employee filters between 1 and 4. | Employee bands `0` and `1-4`; the employee filter includes 1–4 only when the whole range fits. |
| The bulk CSV contains `epostadresse`, `telefon` and `mobil`; separate endpoints expose roles (`/roller`), some with birth numbers behind Maskinporten. | These columns and endpoints are never read. |
| Industry codes in the register are SN2025 subclasses (`10.110`); 717 of 718 distinct main codes in the 1 October 2026 file exist in SN2025 level 5, the other being `00.000` (“Uoppgitt”). | Prefix matching on the dotted code. |
| Kommune numbers in the register use the 2024 county structure (no `30` Viken). | Fylke = first two digits of the kommune number. |
| The underenheter bulk file has a `nedleggelsesdato` column, but it was empty on every row of the 1 October 2026 file (closed sub-units appear not to be published in bulk). | The “closed” flag stays as a guard for single API lookups. |
| 2,858 underenheter in the 1 October 2026 files point to a parent (`overordnetEnhet`) that is not in the enheter file, so their legal form is unknown and could be ENK. | Stored as legal form `UKJENT`, without street address, and excluded with ENK by default. |
| Official register page: `https://virksomhet.brreg.no/nb/oppslag/enheter/{orgnr}` (200 OK). | Company card link. |
| Licence: Norsk lisens for offentlige data (NLOD); no registration needed ([brreg.no open data](https://www.brreg.no/produkter-og-tjenester/apne-data/)). | Attribution on screen and in every export. |

## NLOD 2.0

Source: [data.norge.no/nlod/no/2.0](https://data.norge.no/nlod/no/2.0).

- § 3: the licence does not cover information containing personal data unless there is a lawful basis for disclosure and further processing → ENK handling.
- § 5: name the licensor as specified, refer to and (where practical) link the licence and the source, and mark changes. Default wording «Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av [lisensgiver]» → `brreg.ATTRIBUTION`, which also notes that Prospect Signal filtered the data and derived fields.
- § 6: do not use the licensor's name to endorse or market your product.

## Reference data bundled in `src/prospectsignal/data/`

| File | Source | Licence | Rebuild |
|---|---|---|---|
| `sn2025.csv` | SSB Klass, classification 6, version 3218 “Næringsgruppering (SN) 2025”, valid from 2025-01-01 (`copyrighted: false`) | CC BY 4.0 ([ssb.no/diverse/lisens](https://www.ssb.no/diverse/lisens)) | `python scripts/build_reference_data.py` |
| `fylker.geojson` | Kartverket “Administrative enheter fylker” via `https://api.kartverket.no/kommuneinfo/v1` | CC BY 4.0 (Geonorge metadata `6093c8a8-fa80-11e6-bc64-92361f002671`) | same script; Douglas–Peucker 0.012°, islands < 0.002 deg² dropped, rings wound clockwise for Plotly |
| `outreach_checklist.yaml` | See below | Summaries with links | edit by hand |

## Outreach checklist sources

| Source | Retrieved page state |
|---|---|
| [Markedsføringsloven, Lovdata](https://lovdata.no/dokument/NL/lov/2009-01-09-2) §§ 12, 13, 13 a, 14, 15, 16 | Law last amended by LOV-2026-05-07-17 (in force 1 July 2026); §§ 12–16 last changed 2017. |
| [Forbrukertilsynet: Veileder for markedsføring via e-post, SMS og lignende](https://www.forbrukertilsynet.no/lov-og-rett/veiledninger-og-retningslinjer/forbrukertilsynets-veiledning-markedsforing-via-e-post-sms-o-l) | Updated 8 May 2026. Section 2.4: work addresses such as ola.nordmann@firmaX.no are covered; post@firmaX.no is not; registration as a company contact address in Brønnøysund does not change that. |
| [Forbrukertilsynet: Veileder for telefonsalg](https://www.forbrukertilsynet.no/lov-og-rett/veiledninger-og-retningslinjer/forbrukerombudets-veiledning-regelverket-telefonsalg) | Updated 16 September 2026. |
| [Brønnøysundregistrene: Om Reservasjonsregisteret](https://www.brreg.no/om-oss/registrene-vare/om-reservasjonsregisteret/) | Updated 14 November 2023. Private persons can reserve; marketers to private customers must update lists at least monthly. |
| [Datatilsynet: Nyhetsbrev, e-postlister og SMS](https://www.datatilsynet.no/personvern-pa-ulike-omrader/kundehandtering-handel-og-medlemskap/nyhetsbrev-epostlister-og-sms/) | Last changed 6 May 2026. |
| [Datatilsynet: Berettigede interesser — interesseavveiing](https://www.datatilsynet.no/rettigheter-og-plikter/virksomhetenes-plikter/om-behandlingsgrunnlag/nodvendig-for-a-ivareta-legitime-interesser---interesseavveiing/) | Last changed 17 March 2026. |
| [Datatilsynet: Rett til å protestere](https://www.datatilsynet.no/rettigheter-og-plikter/den-registrertes-rettigheter/rett-til-a-protestere/) | Published 26 June 2024. |

## Freddo CRM (sibling repository `signal-crm`)

Checked in the local checkout on 1 October 2026: the company file importer is planned (TASK-09, TASK-23) but not implemented. The CSV targets the custom fields in `apps/signal_no/signal_no/fixtures/custom_field.json` (`org_nr` unique, `entity_kind`, `parent_org_nr`, `nace`, `employee_band`, `region_postcode`, read-only `brreg_source` and `brreg_refreshed_at`) and Freddo's org.nr rule (string, MOD11, leading zeros kept). See [freddo-import.md](freddo-import.md).

## Open questions — `TODO(verify)`

1. **API rate limits.** None are published in the API documentation. Prospect Signal calls the API only on a user action, one request at a time. Ask opendata@brreg.no before any automated refresh.
2. **Deleted units in single lookups.** The documentation does not state the status code for deleted units; 404 and 410 are both treated as “not in open data”, and a `slettedato` in the body is treated the same way.
3. **Financial statements.** `data.brreg.no/regnskapsregisteret/regnskap/{orgnr}` answers, but its OpenAPI specification states no licence, and Brønnøysundregistrene's open-data page mentions a temporary research API that “can be shut down without notice”. v1 shows no financials until the terms are confirmed.
4. **Freddo importer behaviour.** Whether Frappe Data Import fills read-only fields and how it treats unmapped columns (`street_address`, `poststed`, `kommune`, `fylke`, `nace_description`).
5. **ENK and telemarketing.** Whether a call to a sole proprietor counts as a call to a consumer under §§ 12 and 14.
6. **Name screen.** “Prospect Signal” (written “ProspectSignal” in earlier releases and in technical identifiers such as `prospectsignal`) has not been screened for trademarks or existing products.
