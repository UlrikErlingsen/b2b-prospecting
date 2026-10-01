# Privacy

ProspectSignal has no telemetry, advertising, user accounts, tracking pixels or external AI calls. It stores data only in local DuckDB files (`./data` by default, or `PROSPECTSIGNAL_DATA_DIR`). The only outbound requests go to Brønnøysundregistrene's open-data API, and only when you press a button that says so.

## What is stored

Company facts from Enhetsregisteret: organisation number, name, legal form, industry codes, employee count and band, founding and registration dates, VAT and business-register flags, bankruptcy and liquidation flags, business address, postcode, kommune, fylke, registered website, and the download date. Your shortlist statuses and notes and your saved ICPs are stored next to them.

## What is never stored

- Roles: board members, CEO (daglig leder), contact persons, auditors' people, birth numbers.
- E-mail addresses, phone and mobile numbers, even though the bulk file contains them.
- Street addresses of sole proprietorships (ENK), which are often the owner's home.
- Street addresses of sub-units whose parent company is missing from the open register (legal form unknown, so possibly a sole proprietorship).

## Sole proprietorships (ENK)

An ENK is usually named after its owner, so an ENK row identifies a person. NLOD § 3 does not license personal data without a lawful basis. ProspectSignal therefore excludes ENK from filters and exports unless you include them deliberately, shows a warning on every ENK row, and keeps only coarse location (postcode and kommune) for counts. Sub-units whose parent is missing from the open register are treated the same way, because their owner may be a sole proprietor.

## Your notes

Shortlist notes are free text. Do not write names, e-mail addresses or phone numbers of people into them; keep contact details in your CRM under its own legal basis.

## Registry data is not consent

A company's presence in Enhetsregisteret does not mean it, or anyone working there, agreed to receive marketing. Read the outreach checklist on the Export page before contacting anyone.

If someone deploys the app for others, that operator controls infrastructure logs, retention, authentication, backups and network access, and must document those practices separately.
