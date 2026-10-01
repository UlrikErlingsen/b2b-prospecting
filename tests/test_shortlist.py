from datetime import date

import pandas as pd
import pytest

from prospectsignal import ICP, FitTargets, FitWeights, demo_icp, score_frame
from prospectsignal.errors import DataProblem


def test_shortlist_status_and_notes(demo_store):
    picks = demo_store.query(demo_icp())["org_nr"].head(3).tolist()
    assert demo_store.add_to_shortlist(picks, "demo") == 3
    assert demo_store.add_to_shortlist(picks, "demo") == 0  # no duplicates
    demo_store.update_shortlist(picks[0], status="qualified", notes="Ring innkjøpssjef — via sentralbord")
    frame = demo_store.shortlist_frame()
    row = frame.set_index("org_nr").loc[picks[0]]
    assert row["status"] == "qualified"
    assert row["notes"].startswith("Ring")
    assert set(frame["status"]) <= {"new", "qualified"}
    with pytest.raises(DataProblem):
        demo_store.update_shortlist(picks[0], status="hot lead")
    demo_store.remove_from_shortlist([picks[1]])
    assert len(demo_store.shortlist_frame()) == 2


def test_query_flags_shortlisted_units(demo_store):
    first = demo_store.query(demo_icp())["org_nr"].iloc[0]
    demo_store.add_to_shortlist([first])
    flagged = demo_store.query(demo_icp()).set_index("org_nr")["shortlist_status"]
    assert flagged.loc[first] == "new"


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "employee_band": ["20-49", "250+", "20-49"],
            "fylke_nr": ["31", "31", "46"],
            "nace1": ["11.050", "47.110", "62.100"],
            "nace2": [None, "11.050", None],
            "nace3": [None, None, None],
            "founded": pd.to_datetime(["2015-01-01", "2015-01-01", "1950-01-01"]),
        }
    )


def test_fit_score_components_and_weights_are_transparent():
    targets = FitTargets(bands=("20-49",), fylker=("31",), nace_prefixes=("11",), age_min_years=3, age_max_years=30)
    scored = score_frame(_frame(), targets, FitWeights(), today=date(2026, 10, 1))
    assert scored["fit_score"].tolist() == [100.0, 62.0, 25.0]
    assert scored["fit_nace"].tolist() == [1.0, 0.5, 0.0]  # secondary code match counts half
    region_only = score_frame(_frame(), targets, FitWeights(size=0, region=1, nace=0, age=0), today=date(2026, 10, 1))
    assert region_only["fit_score"].tolist() == [100.0, 100.0, 0.0]
    nothing = score_frame(_frame(), targets, FitWeights(0, 0, 0, 0))
    assert nothing["fit_score"].eq(0).all()


def test_fit_targets_follow_the_icp():
    targets = FitTargets.from_icp(ICP(employees_min=10, employees_max=100, fylker=("31",)).validated())
    assert targets.bands == ("10-19", "20-49", "50-99", "100-249")
    assert targets.fylker == ("31",)
