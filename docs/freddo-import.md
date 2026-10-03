# Importing a Prospect Signal shortlist into Freddo CRM

The bridge is **one-way and manual**: Prospect Signal writes a file, and you decide in Freddo whether to import it. Prospect Signal never connects to Freddo and never exports people.

## The file

`prospectsignal-freddo-YYYY-MM-DD.csv`, UTF-8 without BOM, comma-separated, every value quoted, header on line 1.

| Column | Freddo field | Content |
|---|---|---|
| `organization_name` | CRM Organization name (upstream, required) | Registered name |
| `org_nr` | `org_nr` (custom, unique, MOD11-validated) | Nine-character string; leading zeros kept |
| `entity_kind` | `entity_kind` (`hovedenhet` / `underenhet`, the register's terms) | Unit level: company or location (sub-unit) |
| `parent_org_nr` | `parent_org_nr` | Parent of a sub-unit (underenhet), or the parent body (overordnet enhet) of a public body |
| `nace` | `nace` | Main SN2025 code, e.g. `11.050` |
| `nace_description` | — | Code name from the register |
| `employee_band` | `employee_band` | `0`, `1-4`, `5-9`, `10-19`, `20-49`, `50-99`, `100-249`, `250+` |
| `street_address` | — | Business address lines (blank for ENK) |
| `region_postcode` | `region_postcode` | Four-character string |
| `post_town`, `municipality`, `county` | — | Post town (poststed), municipality (kommune), county (fylke) |
| `website` | `website` (upstream) | As registered |
| `brreg_source` | `brreg_source` (read-only) | Source and licence line (NLOD attribution) |
| `brreg_refreshed_at` | `brreg_refreshed_at` (read-only) | Download date, ISO `YYYY-MM-DD` |

## Status of Freddo's importer — TODO(verify)

On 1 October 2026 Freddo's own importer (signal-crm TASK-09 file importer, TASK-23 CSV import with duplicate review) is planned but not built, so the practical path today is Frappe CRM's generic *Data Import* into **CRM Organization**. Before relying on it, test with a few rows and check:

- that the columns map to the fields above (Frappe matches on field label or fieldname);
- whether read-only fields (`brreg_source`, `brreg_refreshed_at`) are filled on import or skipped;
- how columns without a matching field are treated (they should be left unmapped);
- that duplicate `org_nr` values are rejected rather than overwriting existing organisations.

Import only into **CRM Organization**. Do not import into Contact, Lead or Deal: the file contains companies, and Freddo's rule is that people are never imported from the register.

## Demo files

Demo organisation numbers fail MOD11 on purpose, so Freddo's validator rejects them. That is intended: fictional companies must never enter a real CRM.
