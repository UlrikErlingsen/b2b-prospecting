"""All persistence for Prospect Signal, behind one class.

Everything that touches the database lives here: bulk import of the register files, ICP filtering, market counts,
saved ICPs, the shortlist, and metadata. The rest of the package works with plain Python objects and pandas
frames, so another engine (for example SQLite in a merged Signal Hub) only needs a replacement of this module.

The engine is DuckDB: an embedded, single-file database that reads the 150 MB gzip CSV from Brønnøysundregistrene
in seconds and filters 1.2 million rows interactively.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import threading

import duckdb
import pandas as pd

from . import limits
from .errors import DataProblem
from .icp import ICP
from .schema import (
    PERSON_FIELD_MARKERS,
    PERSON_NAME_FORMS,
    SHORTLIST_STATUSES,
    UNIT_COLUMNS,
    UNIT_SCHEMA,
    _BAND_EDGES,
)

SCHEMA_VERSION = "1"

# Columns read from the bulk CSV files. epostadresse, telefon and mobil exist in the files and are never read.
ENHET_CSV_COLUMNS: tuple[str, ...] = (
    "organisasjonsnummer",
    "navn",
    "organisasjonsform.kode",
    "organisasjonsform.beskrivelse",
    "naeringskode1.kode",
    "naeringskode1.beskrivelse",
    "naeringskode2.kode",
    "naeringskode2.beskrivelse",
    "naeringskode3.kode",
    "naeringskode3.beskrivelse",
    "harRegistrertAntallAnsatte",
    "antallAnsatte",
    "hjemmeside",
    "postadresse.adresse",
    "postadresse.poststed",
    "postadresse.postnummer",
    "postadresse.kommune",
    "postadresse.kommunenummer",
    "postadresse.landkode",
    "forretningsadresse.adresse",
    "forretningsadresse.poststed",
    "forretningsadresse.postnummer",
    "forretningsadresse.kommune",
    "forretningsadresse.kommunenummer",
    "forretningsadresse.landkode",
    "institusjonellSektorkode.kode",
    "registreringsdatoenhetsregisteret",
    "stiftelsesdato",
    "registrertIMvaRegisteret",
    "registrertIForetaksregisteret",
    "konkurs",
    "underAvvikling",
    "underTvangsavviklingEllerTvangsopplosning",
    "overordnetEnhet",
    "aktivitet",
)
UNDERENHET_CSV_COLUMNS: tuple[str, ...] = (
    "organisasjonsnummer",
    "navn",
    "organisasjonsform.kode",
    "naeringskode1.kode",
    "naeringskode1.beskrivelse",
    "naeringskode2.kode",
    "naeringskode2.beskrivelse",
    "naeringskode3.kode",
    "naeringskode3.beskrivelse",
    "harRegistrertAntallAnsatte",
    "antallAnsatte",
    "hjemmeside",
    "postadresse.adresse",
    "postadresse.poststed",
    "postadresse.postnummer",
    "postadresse.kommune",
    "postadresse.kommunenummer",
    "postadresse.landkode",
    "beliggenhetsadresse.adresse",
    "beliggenhetsadresse.poststed",
    "beliggenhetsadresse.postnummer",
    "beliggenhetsadresse.kommune",
    "beliggenhetsadresse.kommunenummer",
    "beliggenhetsadresse.landkode",
    "registreringsdatoIEnhetsregisteret",
    "registrertIMvaregisteret",
    "oppstartsdato",
    "overordnetEnhet",
    "nedleggelsesdato",
)

RESULT_COLUMNS: tuple[str, ...] = (
    "org_nr",
    "name",
    "org_form",
    "nace1",
    "nace1_desc",
    "employee_band",
    "employees",
    "founded",
    "postcode",
    "poststed",
    "kommune",
    "fylke_nr",
    "website",
    "entity_kind",
    "vat_registered",
    "is_demo",
)
DIMENSIONS: dict[str, str] = {
    "fylke": "fylke_nr",
    "kommune": "kommune_nr",
    "nace_division": "substr(nace1, 1, 2)",
    "nace1": "nace1",
    "employee_band": "employee_band",
    "org_form": "org_form",
    "registered_year": "CAST(year(registered) AS INTEGER)",
    "founded_year": "CAST(year(founded) AS INTEGER)",
}


def _q(column: str) -> str:
    return '"' + column.replace('"', '""') + '"'


def _nz(column: str) -> str:
    """NULL for missing or blank cells (the bulk files quote empty strings)."""
    return f"nullif(trim({_q(column)}), '')"


def _flag(column: str) -> str:
    return f"coalesce(lower(trim({_q(column)})) = 'true', false)"


def _band_sql(employees: str = "employees", has_employees: str = "has_employees") -> str:
    """SQL twin of schema.band_for; tests assert both agree."""
    cases = [
        f"WHEN {employees} IS NULL THEN CASE WHEN {has_employees} THEN '1-4' ELSE '0' END",
        f"WHEN {employees} <= 0 THEN '0'",
        f"WHEN {employees} < 5 THEN '1-4'",
    ]
    for _, high, label in _BAND_EDGES:
        if high is not None:
            cases.append(f"WHEN {employees} <= {high} THEN '{label}'")
    return "CASE " + " ".join(cases) + " ELSE '250+' END"


def _csv_source(path: Path) -> str:
    literal = str(path).replace("'", "''")
    # The register's CSV quotes every cell and may contain line breaks and doubled quotes inside cells
    # (API documentation, "Last ned totalbestand av enheter i csv format"); parallel=false keeps quoted
    # newlines intact.
    return (
        f"read_csv('{literal}', header=true, all_varchar=true, quote='\"', escape='\"', "
        "parallel=false, compression='auto')"
    )


def _fylke_sql(kommune_nr: str, country: str) -> str:
    return (
        f"CASE WHEN coalesce({country}, 'NO') = 'NO' AND regexp_full_match(coalesce({kommune_nr}, ''), '[0-9]{{4}}') "
        f"THEN substr({kommune_nr}, 1, 2) END"
    )


class Store:
    """A Prospect Signal database file (or ``":memory:"``)."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._con = duckdb.connect(self.path)
        self._lock = threading.RLock()
        self._ensure_schema()

    # -- plumbing -----------------------------------------------------------------------------------------
    def close(self) -> None:
        self._con.close()

    def _cursor(self) -> duckdb.DuckDBPyConnection:
        return self._con.cursor()

    def _ensure_schema(self) -> None:
        columns = ", ".join(f"{_q(name)} {kind}" for name, kind in UNIT_SCHEMA)
        with self._lock:
            cur = self._cursor()
            cur.execute(f"CREATE TABLE IF NOT EXISTS units ({columns})")
            cur.execute("CREATE TABLE IF NOT EXISTS meta (key VARCHAR PRIMARY KEY, value VARCHAR)")
            cur.execute(
                "CREATE TABLE IF NOT EXISTS icps (name VARCHAR PRIMARY KEY, definition VARCHAR NOT NULL, "
                "updated_at TIMESTAMP NOT NULL)"
            )
            cur.execute(
                "CREATE TABLE IF NOT EXISTS shortlist (org_nr VARCHAR PRIMARY KEY, status VARCHAR NOT NULL, "
                "notes VARCHAR NOT NULL DEFAULT '', icp_name VARCHAR, added_at TIMESTAMP NOT NULL, "
                "updated_at TIMESTAMP NOT NULL)"
            )
            if self.get_meta("schema_version") is None:
                self.set_meta("schema_version", SCHEMA_VERSION)

    def table_columns(self, table: str) -> list[str]:
        rows = (
            self._cursor()
            .execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = ? ORDER BY ordinal_position",
                [table],
            )
            .fetchall()
        )
        return [row[0] for row in rows]

    # -- metadata -----------------------------------------------------------------------------------------
    def get_meta(self, key: str, default: str | None = None) -> str | None:
        row = self._cursor().execute("SELECT value FROM meta WHERE key = ?", [key]).fetchone()
        return row[0] if row else default

    def set_meta(self, key: str, value: object) -> None:
        with self._lock:
            self._cursor().execute(
                "INSERT INTO meta VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                [key, "" if value is None else str(value)],
            )

    def meta(self) -> dict[str, str]:
        return dict(self._cursor().execute("SELECT key, value FROM meta ORDER BY key").fetchall())

    # -- loading units ------------------------------------------------------------------------------------
    def unit_count(self) -> int:
        return int(self._cursor().execute("SELECT count(*) FROM units").fetchone()[0])

    def replace_units(self, frame: pd.DataFrame) -> int:
        """Replace all units with a frame in the stored schema (used for the offline demo and tests)."""
        missing = [column for column in UNIT_COLUMNS if column not in frame.columns]
        extra = [column for column in frame.columns if column not in UNIT_COLUMNS]
        if missing or extra:
            raise DataProblem(f"Unit frame does not match the schema. Missing: {missing}; unexpected: {extra}")
        if not frame.empty and not frame["org_nr"].map(lambda value: isinstance(value, str)).all():
            raise DataProblem("Organisation numbers must be strings so leading zeros survive.")
        casts = ", ".join(f"CAST({_q(name)} AS {kind}) AS {_q(name)}" for name, kind in UNIT_SCHEMA)
        with self._lock:
            cur = self._cursor()
            cur.register("incoming_units", frame[list(UNIT_COLUMNS)])
            cur.execute("BEGIN TRANSACTION")
            try:
                cur.execute("DELETE FROM units")
                cur.execute(f"INSERT INTO units SELECT {casts} FROM incoming_units")
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise
            finally:
                cur.unregister("incoming_units")
        return self.unit_count()

    def _check_csv_columns(self, path: Path, required: tuple[str, ...], label: str) -> None:
        cur = self._cursor()
        description = cur.execute(f"SELECT * FROM {_csv_source(path)} LIMIT 0").description
        present = {column[0].lower() for column in description}
        missing = [column for column in required if column.lower() not in present]
        if missing:
            raise DataProblem(
                f"The {label} file from Brønnøysundregistrene no longer has these expected columns: "
                + ", ".join(missing)
                + ". The bulk format may have changed; the existing local data was kept."
            )

    def _enhet_select(self, path: Path, downloaded_at: date, published: str) -> tuple[str, list]:
        f = "forretningsadresse"
        p = "postadresse"
        use_business = f"{_nz(f + '.kommunenummer')} IS NOT NULL OR {_nz(f + '.postnummer')} IS NOT NULL"

        def pick(field: str) -> str:
            return f"CASE WHEN {use_business} THEN {_nz(f + '.' + field)} ELSE {_nz(p + '.' + field)} END"

        sql = f"""
            WITH raw AS (SELECT * FROM {_csv_source(path)}),
            mapped AS (
                SELECT
                    {_nz("organisasjonsnummer")} AS org_nr,
                    {_nz("navn")} AS name,
                    'hovedenhet' AS entity_kind,
                    {_nz("overordnetEnhet")} AS parent_org_nr,
                    {_nz("organisasjonsform.kode")} AS org_form,
                    {_nz("organisasjonsform.beskrivelse")} AS org_form_desc,
                    {_nz("organisasjonsform.kode")} AS unit_form,
                    {_nz("naeringskode1.kode")} AS nace1,
                    {_nz("naeringskode1.beskrivelse")} AS nace1_desc,
                    {_nz("naeringskode2.kode")} AS nace2,
                    {_nz("naeringskode2.beskrivelse")} AS nace2_desc,
                    {_nz("naeringskode3.kode")} AS nace3,
                    {_nz("naeringskode3.beskrivelse")} AS nace3_desc,
                    {_flag("harRegistrertAntallAnsatte")} AS has_employees,
                    try_cast({_nz("antallAnsatte")} AS INTEGER) AS employees,
                    try_cast({_nz("stiftelsesdato")} AS DATE) AS founded,
                    try_cast({_nz("registreringsdatoenhetsregisteret")} AS DATE) AS registered,
                    {_flag("registrertIMvaRegisteret")} AS vat_registered,
                    {_flag("registrertIForetaksregisteret")} AS in_business_register,
                    {_flag("konkurs")} AS bankrupt,
                    {_flag("underAvvikling")} AS winding_up,
                    {_flag("underTvangsavviklingEllerTvangsopplosning")} AS forced_winding_up,
                    false AS closed,
                    {pick("adresse")} AS address_raw,
                    {pick("postnummer")} AS postcode,
                    {pick("poststed")} AS poststed,
                    {pick("kommunenummer")} AS kommune_nr,
                    {pick("kommune")} AS kommune,
                    {pick("landkode")} AS country_code,
                    {_nz("hjemmeside")} AS website,
                    {_nz("aktivitet")} AS activity,
                    {_nz("institusjonellSektorkode.kode")} AS sector_code
                FROM raw
            )
            SELECT
                org_nr, name, entity_kind, parent_org_nr, org_form, org_form_desc, unit_form,
                nace1, nace1_desc, nace2, nace2_desc, nace3, nace3_desc,
                has_employees, employees, {_band_sql()} AS employee_band,
                founded, registered, vat_registered, in_business_register,
                bankrupt, winding_up, forced_winding_up, closed,
                CASE WHEN org_form = 'ENK' THEN ''
                     ELSE regexp_replace(coalesce(address_raw, ''), '\\s*[\\r\\n]+\\s*', ', ', 'g') END AS address,
                postcode, poststed, kommune_nr, kommune, {_fylke_sql("kommune_nr", "country_code")} AS fylke_nr,
                country_code, website, activity, sector_code,
                false AS is_demo, 'brreg-bulk' AS source, CAST(? AS DATE) AS downloaded_at,
                CAST(? AS VARCHAR) AS source_published_at
            FROM mapped
            WHERE org_nr IS NOT NULL
        """
        return sql, [downloaded_at.isoformat(), published]

    def _underenhet_select(self, path: Path, downloaded_at: date, published: str) -> tuple[str, list]:
        b = "beliggenhetsadresse"
        p = "postadresse"
        use_location = f"{_nz(b + '.kommunenummer')} IS NOT NULL OR {_nz(b + '.postnummer')} IS NOT NULL"

        def pick(field: str) -> str:
            return f"CASE WHEN {use_location} THEN {_nz(b + '.' + field)} ELSE {_nz(p + '.' + field)} END"

        sql = f"""
            WITH raw AS (SELECT * FROM {_csv_source(path)}),
            mapped AS (
                SELECT
                    {_nz("organisasjonsnummer")} AS org_nr,
                    {_nz("navn")} AS name,
                    {_nz("overordnetEnhet")} AS parent_org_nr,
                    {_nz("organisasjonsform.kode")} AS unit_form,
                    {_nz("naeringskode1.kode")} AS nace1,
                    {_nz("naeringskode1.beskrivelse")} AS nace1_desc,
                    {_nz("naeringskode2.kode")} AS nace2,
                    {_nz("naeringskode2.beskrivelse")} AS nace2_desc,
                    {_nz("naeringskode3.kode")} AS nace3,
                    {_nz("naeringskode3.beskrivelse")} AS nace3_desc,
                    {_flag("harRegistrertAntallAnsatte")} AS has_employees,
                    try_cast({_nz("antallAnsatte")} AS INTEGER) AS employees,
                    try_cast({_nz("oppstartsdato")} AS DATE) AS founded,
                    try_cast({_nz("registreringsdatoIEnhetsregisteret")} AS DATE) AS registered,
                    {_flag("registrertIMvaregisteret")} AS vat_registered,
                    {_nz("nedleggelsesdato")} IS NOT NULL AS closed,
                    {pick("adresse")} AS address_raw,
                    {pick("postnummer")} AS postcode,
                    {pick("poststed")} AS poststed,
                    {pick("kommunenummer")} AS kommune_nr,
                    {pick("kommune")} AS kommune,
                    {pick("landkode")} AS country_code,
                    {_nz("hjemmeside")} AS website
                FROM raw
            )
            SELECT
                m.org_nr, m.name, 'underenhet' AS entity_kind, m.parent_org_nr,
                coalesce(parent.org_form, 'UKJENT') AS org_form,
                coalesce(parent.org_form_desc, 'Parent not in the open register') AS org_form_desc,
                m.unit_form,
                m.nace1, m.nace1_desc, m.nace2, m.nace2_desc, m.nace3, m.nace3_desc,
                m.has_employees, m.employees, {_band_sql("m.employees", "m.has_employees")} AS employee_band,
                m.founded, m.registered, m.vat_registered,
                coalesce(parent.in_business_register, false) AS in_business_register,
                coalesce(parent.bankrupt, false) AS bankrupt,
                coalesce(parent.winding_up, false) AS winding_up,
                coalesce(parent.forced_winding_up, false) AS forced_winding_up,
                m.closed,
                CASE WHEN parent.org_nr IS NULL OR parent.org_form = 'ENK' THEN ''
                     ELSE regexp_replace(coalesce(m.address_raw, ''), '\\s*[\\r\\n]+\\s*', ', ', 'g') END AS address,
                m.postcode, m.poststed, m.kommune_nr, m.kommune,
                {_fylke_sql("m.kommune_nr", "m.country_code")} AS fylke_nr,
                m.country_code, m.website, NULL AS activity, NULL AS sector_code,
                false AS is_demo, 'brreg-bulk' AS source, CAST(? AS DATE) AS downloaded_at,
                CAST(? AS VARCHAR) AS source_published_at
            FROM mapped m
            LEFT JOIN units_new parent ON parent.org_nr = m.parent_org_nr AND parent.entity_kind = 'hovedenhet'
            WHERE m.org_nr IS NOT NULL
        """
        return sql, [downloaded_at.isoformat(), published]

    def import_bulk(
        self,
        enheter_csv: Path,
        underenheter_csv: Path | None = None,
        *,
        downloaded_at: date,
        published: dict[str, str] | None = None,
    ) -> dict[str, int]:
        """Index the official bulk CSV files into ``units``, replacing earlier register data atomically.

        The previous data stays in place until the new table is complete, so a failed or format-changed download
        never leaves an empty database. Units no longer in the bulk files (including any "Fjernet" from open data)
        disappear with the swap, as the API documentation requires of copies.
        """
        published = published or {}
        self._check_csv_columns(Path(enheter_csv), ENHET_CSV_COLUMNS, "enheter")
        if underenheter_csv is not None:
            self._check_csv_columns(Path(underenheter_csv), UNDERENHET_CSV_COLUMNS, "underenheter")
        columns = ", ".join(_q(name) for name in UNIT_COLUMNS)
        with self._lock:
            cur = self._cursor()
            cur.execute("DROP TABLE IF EXISTS units_new")
            sql, params = self._enhet_select(Path(enheter_csv), downloaded_at, published.get("enheter", ""))
            cur.execute(f"CREATE TABLE units_new AS SELECT {columns} FROM ({sql})", params)
            hovedenheter = int(cur.execute("SELECT count(*) FROM units_new").fetchone()[0])
            underenheter = 0
            if underenheter_csv is not None:
                sql, params = self._underenhet_select(
                    Path(underenheter_csv), downloaded_at, published.get("underenheter", "")
                )
                cur.execute(f"INSERT INTO units_new SELECT {columns} FROM ({sql})", params)
                underenheter = int(cur.execute("SELECT count(*) FROM units_new").fetchone()[0]) - hovedenheter
            duplicates = int(cur.execute("SELECT count(*) - count(DISTINCT org_nr) FROM units_new").fetchone()[0])
            if duplicates:
                cur.execute("DROP TABLE units_new")
                raise DataProblem(f"The bulk files contain {duplicates} repeated organisation numbers; not imported.")
            cur.execute("BEGIN TRANSACTION")
            try:
                cur.execute("DROP TABLE units")
                cur.execute("ALTER TABLE units_new RENAME TO units")
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise
            cur.execute("CREATE INDEX IF NOT EXISTS units_org_nr ON units (org_nr)")
        return {"hovedenheter": hovedenheter, "underenheter": underenheter}

    def upsert_unit(self, record: dict) -> None:
        """Insert or replace one unit (from a single REST lookup)."""
        unknown = [key for key in record if key not in UNIT_COLUMNS]
        if unknown:
            raise DataProblem(f"Unknown unit fields: {unknown}")
        row = [record.get(column) for column in UNIT_COLUMNS]
        placeholders = ", ".join(f"CAST(? AS {kind})" for _, kind in UNIT_SCHEMA)
        with self._lock:
            cur = self._cursor()
            cur.execute("BEGIN TRANSACTION")
            try:
                cur.execute("DELETE FROM units WHERE org_nr = ?", [record["org_nr"]])
                cur.execute(f"INSERT INTO units VALUES ({placeholders})", row)
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise

    def remove_unit(self, org_nr: str) -> None:
        with self._lock:
            self._cursor().execute("DELETE FROM units WHERE org_nr = ?", [org_nr])

    def get_unit(self, org_nr: str) -> dict | None:
        cur = self._cursor()
        result = cur.execute("SELECT * FROM units WHERE org_nr = ?", [org_nr])
        row = result.fetchone()
        if row is None:
            return None
        return dict(zip([column[0] for column in result.description], row))

    def find_units(self, text: str, limit: int = 25) -> pd.DataFrame:
        """Look up by organisation number or by part of the name."""
        needle = text.strip()
        digits = needle.replace(" ", "")
        return (
            self._cursor()
            .execute(
                "SELECT org_nr, name, org_form, entity_kind, kommune, nace1 FROM units "
                "WHERE org_nr = ? OR name ILIKE ? ORDER BY (org_nr = ?) DESC, name LIMIT ?",
                [digits, f"%{needle}%", digits, int(limit)],
            )
            .df()
        )

    # -- ICP filtering ------------------------------------------------------------------------------------
    @staticmethod
    def _where(icp: ICP) -> tuple[str, list]:
        icp = icp.validated()
        clauses: list[str] = []
        params: list = []
        if icp.entity_kind != "both":
            clauses.append("entity_kind = ?")
            params.append(icp.entity_kind)
        if icp.nace_prefixes:
            code_columns = ["nace1", "nace2", "nace3"] if icp.nace_any_code else ["nace1"]
            parts = []
            for column in code_columns:
                for prefix in icp.nace_prefixes:
                    parts.append(f"starts_with(coalesce({column}, ''), ?)")
                    params.append(prefix)
            clauses.append("(" + " OR ".join(parts) + ")")
        if icp.fylker:
            clauses.append("list_contains(?, fylke_nr)")
            params.append(list(icp.fylker))
        if icp.kommuner:
            clauses.append("list_contains(?, kommune_nr)")
            params.append(list(icp.kommuner))
        if icp.employees_min is not None or icp.employees_max is not None:
            low = icp.employees_min or 0
            high = icp.employees_max
            parts = []
            known = "(employees IS NOT NULL AND employees >= ?"
            params_known: list = [low]
            if high is not None:
                known += " AND employees <= ?"
                params_known.append(high)
            parts.append(known + ")")
            params.extend(params_known)
            # 1-4 employees are reported without a count; include them only when the whole 1-4 range fits.
            if low <= 1 and (high is None or high >= 4):
                parts.append("(employees IS NULL AND has_employees)")
            if low <= 0:
                parts.append("(employees IS NULL AND NOT coalesce(has_employees, false))")
            clauses.append("(" + " OR ".join(parts) + ")")
        if icp.founded_from:
            clauses.append("founded >= ?")
            params.append(icp.founded_from)
        if icp.founded_to:
            clauses.append("founded <= ?")
            params.append(icp.founded_to)
        if icp.org_forms:
            clauses.append("list_contains(?, org_form)")
            params.append(list(icp.org_forms))
        if not icp.include_enk:
            # ENK names are personal data; sub-units with an unknown legal form may belong to an ENK.
            clauses.append("NOT list_contains(?, coalesce(org_form, ''))")
            params.append(list(PERSON_NAME_FORMS))
        if icp.vat_registered is not None:
            clauses.append("vat_registered = ?")
            params.append(icp.vat_registered)
        if icp.exclude_inactive:
            clauses.append(
                "NOT (coalesce(bankrupt, false) OR coalesce(winding_up, false) "
                "OR coalesce(forced_winding_up, false) OR coalesce(closed, false))"
            )
        return (" AND ".join(clauses) or "TRUE"), params

    def count(self, icp: ICP) -> int:
        where, params = self._where(icp)
        return int(self._cursor().execute(f"SELECT count(*) FROM units WHERE {where}", params).fetchone()[0])

    def query(self, icp: ICP, limit: int = 5000) -> pd.DataFrame:
        where, params = self._where(icp)
        columns = ", ".join(f"u.{_q(column)}" for column in RESULT_COLUMNS)
        sql = (
            f"SELECT {columns}, s.status AS shortlist_status FROM units u "
            f"LEFT JOIN shortlist s ON s.org_nr = u.org_nr WHERE {where} "
            "ORDER BY u.employees DESC NULLS LAST, u.name LIMIT ?"
        )
        return self._cursor().execute(sql, [*params, int(limit)]).df()

    def counts_by(self, icp: ICP, dimension: str) -> pd.DataFrame:
        if dimension not in DIMENSIONS:
            raise DataProblem(f"Unknown dimension: {dimension}")
        where, params = self._where(icp)
        expression = DIMENSIONS[dimension]
        sql = (
            f"SELECT {expression} AS key, count(*) AS units FROM units WHERE {where} "
            "GROUP BY 1 ORDER BY units DESC, key"
        )
        return self._cursor().execute(sql, params).df()

    def nace_codes_present(self) -> pd.DataFrame:
        return (
            self._cursor()
            .execute(
                "SELECT nace1 AS code, any_value(nace1_desc) AS description, count(*) AS units FROM units "
                "WHERE nace1 IS NOT NULL GROUP BY 1 ORDER BY 1"
            )
            .df()
        )

    def kommuner_present(self) -> pd.DataFrame:
        return (
            self._cursor()
            .execute(
                "SELECT kommune_nr, any_value(kommune) AS kommune, fylke_nr, count(*) AS units FROM units "
                "WHERE kommune_nr IS NOT NULL GROUP BY 1, 3 ORDER BY 1"
            )
            .df()
        )

    # -- saved ICPs ---------------------------------------------------------------------------------------
    def save_icp(self, icp: ICP) -> None:
        icp = icp.validated()
        existing = self.list_icps()
        if icp.name not in existing and limits.exceeds(len(existing) + 1, limits.max_saved_icps()):
            raise DataProblem(limits.demo_message(f"At most {limits.DEMO_MAX_SAVED_ICPS} saved ICPs here."))
        with self._lock:
            self._cursor().execute(
                "INSERT INTO icps VALUES (?, ?, ?) ON CONFLICT (name) DO UPDATE SET "
                "definition = excluded.definition, updated_at = excluded.updated_at",
                [icp.name, icp.to_json(), datetime.now(timezone.utc).replace(tzinfo=None)],
            )

    def list_icps(self) -> list[str]:
        return [row[0] for row in self._cursor().execute("SELECT name FROM icps ORDER BY name").fetchall()]

    def load_icp(self, name: str) -> ICP:
        row = self._cursor().execute("SELECT definition FROM icps WHERE name = ?", [name]).fetchone()
        if row is None:
            raise DataProblem(f"No saved ICP named '{name}'.")
        return ICP.from_json(row[0])

    def delete_icp(self, name: str) -> None:
        with self._lock:
            self._cursor().execute("DELETE FROM icps WHERE name = ?", [name])

    # -- shortlist ----------------------------------------------------------------------------------------
    def add_to_shortlist(self, org_nrs: list[str], icp_name: str | None = None) -> int:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        added = 0
        cap = limits.max_shortlist()
        if cap is not None:
            current = set(self._cursor().execute("SELECT org_nr FROM shortlist").df()["org_nr"].astype(str))
            new = [org_nr for org_nr in dict.fromkeys(map(str, org_nrs)) if org_nr not in current]
            if limits.exceeds(len(current) + len(new), cap):
                raise DataProblem(limits.demo_message(f"The shortlist holds at most {limits.DEMO_MAX_SHORTLIST} companies here."))
        with self._lock:
            cur = self._cursor()
            for org_nr in dict.fromkeys(org_nrs):
                exists = cur.execute("SELECT 1 FROM shortlist WHERE org_nr = ?", [org_nr]).fetchone()
                if exists:
                    continue
                cur.execute("INSERT INTO shortlist VALUES (?, 'new', '', ?, ?, ?)", [str(org_nr), icp_name, now, now])
                added += 1
        return added

    def update_shortlist(self, org_nr: str, *, status: str | None = None, notes: str | None = None) -> None:
        if status is not None and status not in SHORTLIST_STATUSES:
            raise DataProblem(f"Status must be one of: {', '.join(SHORTLIST_STATUSES)}")
        if notes is not None and limits.exceeds(len(notes), limits.max_note_chars()):
            raise DataProblem(limits.demo_message(f"Notes are limited to {limits.DEMO_MAX_NOTE_CHARS:,} characters here."))
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with self._lock:
            cur = self._cursor()
            if status is not None:
                cur.execute("UPDATE shortlist SET status = ?, updated_at = ? WHERE org_nr = ?", [status, now, org_nr])
            if notes is not None:
                cur.execute("UPDATE shortlist SET notes = ?, updated_at = ? WHERE org_nr = ?", [notes, now, org_nr])

    def remove_from_shortlist(self, org_nrs: list[str]) -> None:
        with self._lock:
            cur = self._cursor()
            for org_nr in org_nrs:
                cur.execute("DELETE FROM shortlist WHERE org_nr = ?", [org_nr])

    def shortlist_frame(self) -> pd.DataFrame:
        """Shortlist rows joined to current register facts. ``in_register`` is false when a unit has left."""
        unit_columns = ", ".join(f"u.{_q(column)}" for column in UNIT_COLUMNS if column != "org_nr")
        return (
            self._cursor()
            .execute(
                f"SELECT s.org_nr, s.status, s.notes, s.icp_name, s.added_at, s.updated_at, "
                f"u.org_nr IS NOT NULL AS in_register, {unit_columns} "
                "FROM shortlist s LEFT JOIN units u ON u.org_nr = s.org_nr ORDER BY s.added_at, s.org_nr"
            )
            .df()
        )


def assert_no_person_columns(columns: list[str] | tuple[str, ...]) -> None:
    """Raise if any column name looks like a person field. Used for storage and export checks."""
    offending = [column for column in columns if any(marker in str(column).lower() for marker in PERSON_FIELD_MARKERS)]
    if offending:
        raise DataProblem("Person fields are not allowed in Prospect Signal: " + ", ".join(offending))
