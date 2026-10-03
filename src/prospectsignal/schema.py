"""The stored company schema, employee bands, organisation forms, and the person-data boundary."""

from __future__ import annotations

# Every column Prospect Signal stores about a unit, in order, with its DuckDB type. Nothing about people:
# no roller (board, CEO, contact persons), no e-mail address, no telephone or mobile number.
UNIT_SCHEMA: tuple[tuple[str, str], ...] = (
    ("org_nr", "VARCHAR"),  # nine-character string, never a number
    ("name", "VARCHAR"),
    ("entity_kind", "VARCHAR"),  # hovedenhet | underenhet
    ("parent_org_nr", "VARCHAR"),
    ("org_form", "VARCHAR"),  # legal form; an underenhet inherits its parent's form so ENK rules still apply
    ("org_form_desc", "VARCHAR"),
    ("unit_form", "VARCHAR"),  # the unit's own form code (BEDR/AAFY for underenheter)
    ("nace1", "VARCHAR"),
    ("nace1_desc", "VARCHAR"),
    ("nace2", "VARCHAR"),
    ("nace2_desc", "VARCHAR"),
    ("nace3", "VARCHAR"),
    ("nace3_desc", "VARCHAR"),
    ("has_employees", "BOOLEAN"),
    ("employees", "INTEGER"),  # NULL when 0-4: the register hides counts below five
    ("employee_band", "VARCHAR"),
    ("founded", "DATE"),  # stiftelsesdato (hovedenhet) or oppstartsdato (underenhet)
    ("registered", "DATE"),  # registration date in Enhetsregisteret
    ("vat_registered", "BOOLEAN"),
    ("in_business_register", "BOOLEAN"),  # Foretaksregisteret
    ("bankrupt", "BOOLEAN"),
    ("winding_up", "BOOLEAN"),
    ("forced_winding_up", "BOOLEAN"),
    ("closed", "BOOLEAN"),  # underenhet with nedleggelsesdato
    ("address", "VARCHAR"),  # street lines; always blank for ENK (often a person's home address)
    ("postcode", "VARCHAR"),  # string: leading zeros survive
    ("poststed", "VARCHAR"),
    ("kommune_nr", "VARCHAR"),
    ("kommune", "VARCHAR"),
    ("fylke_nr", "VARCHAR"),
    ("country_code", "VARCHAR"),
    ("website", "VARCHAR"),
    ("activity", "VARCHAR"),
    ("sector_code", "VARCHAR"),
    ("is_demo", "BOOLEAN"),
    ("source", "VARCHAR"),  # brreg-bulk | brreg-api | demo
    ("downloaded_at", "DATE"),  # the day this row was fetched from Brønnøysundregistrene
    ("source_published_at", "VARCHAR"),  # the file's Last-Modified header, when known
)
UNIT_COLUMNS: tuple[str, ...] = tuple(name for name, _ in UNIT_SCHEMA)

# Substrings that must never appear in a stored or exported column name.
PERSON_FIELD_MARKERS: tuple[str, ...] = (
    "rolle",
    "roller",
    "person",
    "fodsel",
    "fødsel",
    "epost",
    "e_post",
    "email",
    "telefon",
    "phone",
    "mobil",
    "daglig_leder",
    "dagligleder",
    "styre",
    "kontaktperson",
    "contact",
    "first_name",
    "last_name",
)

# Bulk-file columns that are deliberately never read, even though Brønnøysundregistrene publishes them.
EXCLUDED_REGISTER_FIELDS: tuple[str, ...] = ("epostadresse", "telefon", "mobil")

EMPLOYEE_BANDS: tuple[str, ...] = ("0", "1-4", "5-9", "10-19", "20-49", "50-99", "100-249", "250+")
_BAND_EDGES: tuple[tuple[int, int | None, str], ...] = (
    (5, 9, "5-9"),
    (10, 19, "10-19"),
    (20, 49, "20-49"),
    (50, 99, "50-99"),
    (100, 249, "100-249"),
    (250, None, "250+"),
)


def band_for(employees: int | None, has_employees: bool | None) -> str:
    """Employee band from the register's two fields.

    Since API v2 the register reports ``antallAnsatte`` only from five employees upward; units with 1-4 employees
    have ``harRegistrertAntallAnsatte = true`` and no count, and units with none have it false.
    """
    if employees is None or employees != employees:  # None or NaN
        return "1-4" if has_employees else "0"
    employees = int(employees)
    if employees <= 0:
        return "0"
    if employees < 5:
        return "1-4"
    for low, high, label in _BAND_EDGES:
        if employees >= low and (high is None or employees <= high):
            return label
    return "250+"  # pragma: no cover


def band_range(label: str) -> tuple[int, int | None]:
    if label == "0":
        return 0, 0
    if label == "1-4":
        return 1, 4
    for low, high, band in _BAND_EDGES:
        if band == label:
            return low, high
    raise ValueError(f"Unknown employee band: {label}")


# Organisation-form codes from Enhetsregisteret with an English description (the register's own Norwegian name in
# parentheses, as shown on official register pages).
ORG_FORMS: dict[str, str] = {
    "AS": "Private limited company (aksjeselskap)",
    "ASA": "Public limited company (allmennaksjeselskap)",
    "ENK": "Sole proprietorship (enkeltpersonforetak)",
    "ANS": "General partnership, joint liability (ansvarlig selskap)",
    "DA": "General partnership, shared liability (selskap med delt ansvar)",
    "SA": "Cooperative (samvirkeforetak)",
    "NUF": "Norwegian branch of a foreign company (NUF)",
    "STI": "Foundation (stiftelse)",
    "FLI": "Association or club (forening/lag/innretning)",
    "BA": "Company with limited liability (selskap med begrenset ansvar)",
    "KS": "Limited partnership (kommandittselskap)",
    "SE": "European company (SE)",
    "ESEK": "Condominium (eierseksjonssameie)",
    "BRL": "Housing cooperative (borettslag)",
}
DEFAULT_ORG_FORMS: tuple[str, ...] = ()  # empty = any form (ENK still excluded unless explicitly included)

SHORTLIST_STATUSES: tuple[str, ...] = ("new", "researching", "qualified", "not a fit", "sent to CRM")

# A sub-unit whose parent is not in the open register has an unknown legal form; it may belong to a sole
# proprietor, so it is handled like ENK (2,858 such sub-units in the 2026-10-01 bulk files).
UNKNOWN_FORM = "UKJENT"
PERSON_NAME_FORMS: tuple[str, ...] = ("ENK", UNKNOWN_FORM)

ENK_WARNING = (
    "ENK (enkeltpersonforetak, sole proprietorship): the company name is usually a person's name, so this row is personal data. "
    "Prospect Signal excludes ENK by default and never stores an ENK street address. Sub-units whose parent is "
    "missing from the open register (legal form unknown) are treated the same way."
)
