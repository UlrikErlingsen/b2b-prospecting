from datetime import date

import pytest

from prospectsignal import ICP, demo_icp, market_tables
from prospectsignal.errors import DataProblem
from prospectsignal.market import fylke_map


def test_demo_icp_finds_food_and_beverage_in_former_viken(demo_store):
    icp = demo_icp()
    result = demo_store.query(icp)
    assert 20 <= len(result) <= 200
    assert result["nace1"].str[:2].isin(["10", "11"]).all()
    assert result["fylke_nr"].isin(["31", "32", "33"]).all()
    assert result["org_form"].ne("ENK").all()
    known = result["employees"].dropna()
    assert known.between(10, 100).all()
    assert demo_store.count(icp) == len(result)


def test_icp_validation_rejects_contradictions():
    with pytest.raises(DataProblem):
        ICP(employees_min=50, employees_max=10).validated()
    with pytest.raises(DataProblem):
        ICP(founded_from=date(2020, 1, 1), founded_to=date(2019, 1, 1)).validated()
    with pytest.raises(DataProblem):
        ICP(org_forms=("ENK",)).validated()  # ENK must be included deliberately
    with pytest.raises(DataProblem):
        ICP(nace_prefixes=("abc",)).validated()


def test_icp_round_trips_through_json_and_storage(demo_store):
    icp = ICP(
        name="Bryggerier i Østfold",
        nace_prefixes=("11.05",),
        fylker=("31",),
        employees_min=5,
        founded_from=date(2018, 1, 1),
        vat_registered=True,
    ).validated()
    assert ICP.from_json(icp.to_json()) == icp
    demo_store.save_icp(icp)
    assert demo_store.list_icps() == ["Bryggerier i Østfold"]
    assert demo_store.load_icp("Bryggerier i Østfold") == icp
    demo_store.delete_icp("Bryggerier i Østfold")
    assert demo_store.list_icps() == []


def test_employee_range_handles_hidden_small_counts(demo_store):
    zero_to_four = demo_store.query(ICP(employees_max=4, exclude_inactive=False), limit=100000)
    assert set(zero_to_four["employee_band"]) <= {"0", "1-4"}
    two_to_three = demo_store.query(ICP(employees_min=2, employees_max=3), limit=100000)
    assert two_to_three.empty  # 1-4 is hidden, so a 2-3 filter cannot honestly include those units
    five_plus = demo_store.query(ICP(employees_min=5), limit=100000)
    assert not five_plus["employee_band"].isin(["0", "1-4"]).any()


def test_founded_filter_and_unit_level(demo_store):
    recent = demo_store.query(ICP(founded_from=date(2018, 1, 1)), limit=100000)
    assert (recent["founded"].dt.date >= date(2018, 1, 1)).all()
    subs = demo_store.query(ICP(entity_kind="underenhet"), limit=100000)
    assert set(subs["entity_kind"]) == {"underenhet"}


def test_market_tables_are_counts_only(demo_store):
    tables = market_tables(demo_store, demo_icp())
    for name, table in tables.items():
        assert list(table.columns[:2]) == ["key", "units"], name
        assert "name" not in table.columns and "org_nr" not in table.columns
    assert tables["fylke"]["units"].sum() == demo_store.count(demo_icp())
    figure = fylke_map(tables["fylke"])
    assert len(figure.data[0]["locations"]) == 15
