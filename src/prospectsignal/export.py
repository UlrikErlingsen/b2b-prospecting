"""Shortlist exports: a CSV for Freddo CRM's company import, and an XLSX workbook for people.

Freddo's own importer is not built yet (signal-crm TASK-09/TASK-23), so the CSV targets the fields Freddo has added
to Frappe CRM's ``CRM Organization`` (signal-crm ``fixtures/custom_field.json``: org_nr, entity_kind, parent_org_nr,
nace, employee_band, region_postcode) plus the upstream ``organization_name`` and ``website``. Rules:

- the header is the first line (a generic CSV importer reads line one as the header), UTF-8 without BOM;
- org.nr is written as a quoted nine-character string; postcodes keep their leading zeros;
- attribution and download date travel in every row (``brreg_source``, ``brreg_refreshed_at``), because a leading
  comment line would break the import;
- no person fields, ever.

TODO(verify) once Freddo's importer exists: whether Frappe Data Import fills the read-only ``brreg_source`` /
``brreg_refreshed_at`` fields, and how it treats the unmapped ``street_address``/``post_town``/``municipality``/``county`` columns.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO, StringIO
import csv
import re

import pandas as pd

from . import brreg, regions
from .storage import assert_no_person_columns

FREDDO_COLUMNS: tuple[str, ...] = (
    "organization_name",
    "org_nr",
    "entity_kind",
    "parent_org_nr",
    "nace",
    "nace_description",
    "employee_band",
    "street_address",
    "region_postcode",
    "post_town",
    "municipality",
    "county",
    "website",
    "brreg_source",
    "brreg_refreshed_at",
)
_ILLEGAL_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _safe_cell(value: object) -> object:
    """Strip control characters and neutralise spreadsheet formulas."""
    if isinstance(value, str):
        cleaned = _ILLEGAL_XML.sub("", value)
        if cleaned.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + cleaned
        return cleaned
    return value


def safe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.columns:
        if result[column].dtype == object or str(result[column].dtype).startswith("string"):
            result[column] = result[column].map(_safe_cell)
    result.columns = [_safe_cell(str(column)) for column in result.columns]
    return result


def _text(value: object) -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    return str(value)


def _date_text(value: object) -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    return pd.Timestamp(value).date().isoformat()


def source_line(row: pd.Series) -> str:
    if bool(row.get("is_demo")):
        return brreg.DEMO_ATTRIBUTION
    via = "bulk file" if row.get("source") == "brreg-bulk" else "API lookup"
    return f"Enhetsregisteret, Brønnøysundregistrene ({via}), {brreg.LICENCE_NAME}"


def freddo_frame(shortlist: pd.DataFrame) -> pd.DataFrame:
    """Map shortlist rows (``Store.shortlist_frame``) to Freddo's company-import columns. Units no longer in the
    register are left out."""
    rows = (
        shortlist.loc[shortlist["in_register"].fillna(False).astype(bool)] if "in_register" in shortlist else shortlist
    )
    records = []
    for _, row in rows.iterrows():
        records.append(
            {
                "organization_name": _text(row.get("name")),
                "org_nr": _text(row.get("org_nr")),
                "entity_kind": _text(row.get("entity_kind")),
                "parent_org_nr": _text(row.get("parent_org_nr")),
                "nace": _text(row.get("nace1")),
                "nace_description": _text(row.get("nace1_desc")),
                "employee_band": _text(row.get("employee_band")),
                "street_address": _text(row.get("address")),
                "region_postcode": _text(row.get("postcode")),
                "post_town": _text(row.get("poststed")),
                "municipality": _text(row.get("kommune")),
                "county": regions.fylke_name(_text(row.get("fylke_nr")) or None),
                "website": _text(row.get("website")),
                "brreg_source": source_line(row),
                "brreg_refreshed_at": _date_text(row.get("downloaded_at")),
            }
        )
    frame = pd.DataFrame(records, columns=list(FREDDO_COLUMNS))
    assert_no_person_columns(list(frame.columns))
    return frame


def freddo_csv_bytes(shortlist: pd.DataFrame) -> bytes:
    frame = safe_frame(freddo_frame(shortlist))
    buffer = StringIO()
    frame.to_csv(buffer, index=False, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
    return buffer.getvalue().encode("utf-8")


def xlsx_bytes(
    shortlist: pd.DataFrame,
    *,
    meta: dict[str, str],
    checklist_rows: list[dict[str, str]] | None = None,
    icp_lines: list[str] | None = None,
    exported_on: date | None = None,
) -> bytes:
    """A workbook with the shortlist, its source and licence, the outreach checklist, and the ICP used."""
    exported_on = exported_on or date.today()
    data = freddo_frame(shortlist)
    if not shortlist.empty and "status" in shortlist:
        statuses = (
            shortlist.loc[shortlist["in_register"].fillna(False).astype(bool)]
            if "in_register" in shortlist
            else shortlist
        )
        data.insert(2, "status", statuses["status"].tolist())
        data.insert(3, "notes", statuses["notes"].tolist())
    is_demo = meta.get("dataset") == "demo"
    source_rows = [
        ("Attribution", brreg.DEMO_ATTRIBUTION if is_demo else brreg.ATTRIBUTION),
        ("Licence", "Not applicable (fictional data)" if is_demo else f"{brreg.LICENCE_NAME} — {brreg.LICENCE_URL}"),
        ("Source", "Prospect Signal demo generator" if is_demo else brreg.DOCS_URL),
        ("Register downloaded", meta.get("downloaded_at", "")),
        ("Bulk file published (Last-Modified)", meta.get("enheter_last_modified", "")),
        ("Exported", exported_on.isoformat()),
        ("Consent", brreg.CONSENT_NOTE),
        ("Personal data", "No person fields are stored or exported. ENK names can identify a person."),
    ]
    source = pd.DataFrame(source_rows, columns=["Item", "Value"])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        safe_frame(data).to_excel(writer, sheet_name="Shortlist", index=False)
        safe_frame(source).to_excel(writer, sheet_name="Source & licence", index=False)
        if icp_lines:
            safe_frame(pd.DataFrame({"ICP": icp_lines})).to_excel(writer, sheet_name="ICP", index=False)
        if checklist_rows:
            safe_frame(pd.DataFrame(checklist_rows)).to_excel(writer, sheet_name="Outreach checklist", index=False)
        for sheet in writer.book.worksheets:
            for column in sheet.columns:
                width = max(len(str(cell.value or "")) for cell in column[:200])
                sheet.column_dimensions[column[0].column_letter].width = min(max(10, width + 2), 70)
            # Keep organisation numbers and postcodes as text in Excel.
            for cell in sheet[1]:
                if cell.value in ("org_nr", "parent_org_nr", "region_postcode"):
                    for target in sheet[cell.column_letter][1:]:
                        target.number_format = "@"
    return output.getvalue()
