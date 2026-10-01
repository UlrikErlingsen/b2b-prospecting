from datetime import date

import pytest

from conftest import ENHET_HEADER, ENHETER_ROWS, FAKE_CONTACT_VALUES, write_bulk
from prospectsignal import ICP, Store, UNIT_COLUMNS
from prospectsignal.errors import DataProblem
from prospectsignal.schema import EXCLUDED_REGISTER_FIELDS, band_for
from prospectsignal.storage import _band_sql, assert_no_person_columns

AS_NR, ENK_NR, BANKRUPT_NR, HOLDING_NR = "100011379", "100022745", "100034115", "100045486"
SUB_NR, ENK_SUB_NR, CLOSED_SUB_NR, ORPHAN_SUB_NR = "100056852", "100068222", "100079593", "100090950"


@pytest.fixture
def loaded(bulk_files) -> Store:
    store = Store()
    counts = store.import_bulk(
        *bulk_files, downloaded_at=date(2026, 10, 1), published={"enheter": "Thu, 01 Oct 2026 02:27:24 GMT"}
    )
    assert counts == {"hovedenheter": 4, "underenheter": 4}
    return store


def test_recorded_header_still_has_the_person_fields_we_skip():
    header = ENHET_HEADER.read_text(encoding="utf-8")
    for field in EXCLUDED_REGISTER_FIELDS:
        assert f'"{field}"' in header


def test_stored_schema_has_no_person_fields(loaded):
    columns = loaded.table_columns("units")
    assert columns == list(UNIT_COLUMNS)
    assert_no_person_columns(columns)
    for table in ("shortlist", "icps", "meta"):
        assert_no_person_columns(loaded.table_columns(table))


def test_contact_values_never_reach_storage(loaded):
    rows = loaded._cursor().execute("SELECT * FROM units").fetchall()
    text = " ".join(str(value) for row in rows for value in row)
    for value in FAKE_CONTACT_VALUES:
        assert value not in text
    assert "@" not in text


def test_orgnr_postcode_and_norwegian_letters_survive(loaded):
    unit = loaded.get_unit(AS_NR)
    assert unit["org_nr"] == AS_NR
    assert unit["postcode"] == "0150"
    assert unit["name"] == "FIXTURE ÆRLIG ØL OG BRØD AS"
    assert unit["address"] == 'c/o Regnskap "Å" AS, Bryggeveien 1'  # embedded newline and doubled quotes
    assert unit["fylke_nr"] == "03"
    assert unit["employee_band"] == "20-49"
    assert unit["downloaded_at"] == date(2026, 10, 1)
    assert unit["source_published_at"] == "Thu, 01 Oct 2026 02:27:24 GMT"


def test_enk_street_address_is_never_stored(loaded):
    enk = loaded.get_unit(ENK_NR)
    assert enk["org_form"] == "ENK"
    assert enk["address"] == ""
    assert enk["postcode"] == "1606"  # coarse location is kept for counts
    assert enk["employee_band"] == "1-4"  # registered employees, count hidden
    enk_sub = loaded.get_unit(ENK_SUB_NR)
    assert enk_sub["org_form"] == "ENK"  # inherited from the parent
    assert enk_sub["address"] == ""


def test_postadresse_is_used_when_business_address_is_missing(loaded):
    holding = loaded.get_unit(HOLDING_NR)
    assert holding["kommune_nr"] == "3301"
    assert holding["fylke_nr"] == "33"
    assert holding["employee_band"] == "0"


def test_underenhet_inherits_parent_status_and_closure(loaded):
    sub = loaded.get_unit(SUB_NR)
    assert sub["entity_kind"] == "underenhet"
    assert sub["parent_org_nr"] == AS_NR
    assert sub["org_form"] == "AS" and sub["unit_form"] == "BEDR"
    assert sub["fylke_nr"] == "31"
    assert loaded.get_unit(CLOSED_SUB_NR)["closed"] is True


def test_enk_excluded_by_default(loaded):
    everyone = ICP(entity_kind="both", exclude_inactive=False, include_enk=True)
    default = ICP(entity_kind="both", exclude_inactive=False)
    assert loaded.count(everyone) == 8
    assert loaded.count(default) == 5
    assert ENK_NR not in set(loaded.query(default)["org_nr"])
    assert ENK_SUB_NR not in set(loaded.query(default)["org_nr"])
    assert ORPHAN_SUB_NR not in set(loaded.query(default)["org_nr"])
    assert ORPHAN_SUB_NR in set(loaded.query(everyone)["org_nr"])


def test_subunit_with_unknown_parent_is_handled_like_enk(loaded):
    orphan = loaded.get_unit(ORPHAN_SUB_NR)
    assert orphan["org_form"] == "UKJENT"
    assert orphan["address"] == ""  # may belong to a sole proprietor: no street address
    assert orphan["kommune_nr"] == "3301"


def test_inactive_units_excluded_by_default(loaded):
    result = set(loaded.query(ICP(entity_kind="both"))["org_nr"])
    assert BANKRUPT_NR not in result
    assert CLOSED_SUB_NR not in result
    assert AS_NR in result and SUB_NR in result


def test_nace_hierarchy_filter_on_imported_data(loaded):
    base = dict(exclude_inactive=False, include_enk=True)
    assert set(loaded.query(ICP(nace_prefixes=("10",), **base))["org_nr"]) == {ENK_NR, BANKRUPT_NR}
    assert set(loaded.query(ICP(nace_prefixes=("10.6",), **base))["org_nr"]) == {BANKRUPT_NR}
    assert set(loaded.query(ICP(nace_prefixes=("10.71",), **base))["org_nr"]) == {ENK_NR}
    # Secondary codes only when asked for.
    assert AS_NR not in set(loaded.query(ICP(nace_prefixes=("10.7",), **base))["org_nr"])
    assert AS_NR in set(loaded.query(ICP(nace_prefixes=("10.7",), nace_any_code=True, **base))["org_nr"])


def test_failed_reimport_keeps_existing_data(loaded, tmp_path):
    broken_rows = [{key: value for key, value in ENHETER_ROWS[0].items()}]
    path = write_bulk(tmp_path / "broken.csv.gz", ENHET_HEADER, broken_rows)
    # Simulate a format change: drop a required column from the header.
    import gzip

    text = gzip.open(path, "rt", encoding="utf-8").read().replace('"antallAnsatte"', '"antallAnsatteNy"', 1)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)
    with pytest.raises(DataProblem, match="antallAnsatte"):
        loaded.import_bulk(path, downloaded_at=date(2026, 10, 2))
    assert loaded.unit_count() == 8


def test_band_python_and_sql_agree():
    store = Store()
    cursor = store._cursor()
    for employees in [None, 0, 1, 4, 5, 9, 10, 19, 20, 49, 50, 99, 100, 249, 250, 5000]:
        for has in (True, False):
            sql = cursor.execute(
                f"SELECT {_band_sql('e', 'h')} FROM (SELECT CAST(? AS INTEGER) AS e, CAST(? AS BOOLEAN) AS h)",
                [employees, has],
            ).fetchone()[0]
            assert sql == band_for(employees, has), (employees, has)
