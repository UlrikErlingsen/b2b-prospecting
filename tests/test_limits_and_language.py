"""No limits locally, demo caps with SIGNAL_PUBLIC=1, upload settings, and English app text."""

from pathlib import Path
import re

import pytest

from prospectsignal import brreg, limits
from prospectsignal.demo import make_demo_units
from prospectsignal.errors import DataProblem, RegisterUnavailable, friendly_message
from prospectsignal.export import FREDDO_COLUMNS
from prospectsignal.icp import demo_icp
from prospectsignal.schema import ORG_FORMS

ROOT = Path(__file__).parents[1]


def _org_nrs(store, count: int) -> list[str]:
    return store.query(demo_icp().__class__(name="all", include_enk=True, exclude_inactive=False), limit=count)[
        "org_nr"
    ].tolist()


def test_local_mode_has_no_limits(demo_store, monkeypatch: pytest.MonkeyPatch) -> None:
    assert not limits.is_public()
    assert limits.max_shortlist() is None and limits.max_note_chars() is None and limits.max_saved_icps() is None
    assert limits.register_download_allowed()
    monkeypatch.setattr(limits, "DEMO_MAX_SHORTLIST", 3)
    monkeypatch.setattr(limits, "DEMO_MAX_NOTE_CHARS", 5)
    monkeypatch.setattr(limits, "DEMO_MAX_SAVED_ICPS", 0)
    org_nrs = _org_nrs(demo_store, 10)
    assert demo_store.add_to_shortlist(org_nrs) == 10
    demo_store.update_shortlist(org_nrs[0], notes="x" * 50)
    demo_store.save_icp(demo_icp())
    assert demo_store.list_icps()


def test_public_demo_enforces_its_caps(demo_store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIGNAL_PUBLIC", "1")
    monkeypatch.setattr(limits, "DEMO_MAX_SHORTLIST", 3)
    org_nrs = _org_nrs(demo_store, 10)
    with pytest.raises(DataProblem, match="at most 3 companies here.*downloaded app has no such limit"):
        demo_store.add_to_shortlist(org_nrs)
    assert demo_store.add_to_shortlist(org_nrs[:3]) == 3
    assert demo_store.add_to_shortlist(org_nrs[:3]) == 0  # already listed: not new, so not over the cap
    with pytest.raises(DataProblem, match="limited to 2,000 characters here"):
        demo_store.update_shortlist(org_nrs[0], notes="x" * 2001)
    monkeypatch.setattr(limits, "DEMO_MAX_SAVED_ICPS", 0)
    with pytest.raises(DataProblem, match="saved ICPs here"):
        demo_store.save_icp(demo_icp())
    with pytest.raises(RegisterUnavailable, match="off in this public demo"):
        brreg.bulk_headers("enheter")
    with pytest.raises(RegisterUnavailable, match="off in this public demo"):
        brreg.fetch_unit("974760673")


def test_memory_errors_become_a_plain_message() -> None:
    assert "not enough memory" in friendly_message(MemoryError())


def test_launchers_and_docker_use_the_10000_mb_upload_cap() -> None:
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    windows = (ROOT / "run_app.bat").read_text(encoding="utf-8")
    mac = (ROOT / "run_app.command").read_text(encoding="utf-8")
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "maxUploadSize = 10000" in config
    assert "set PROSPECTSIGNAL_MAX_UPLOAD_MB=10000" in windows
    assert "--server.maxUploadSize=%PROSPECTSIGNAL_MAX_UPLOAD_MB%" in windows
    assert '--server.maxUploadSize="${PROSPECTSIGNAL_MAX_UPLOAD_MB:-10000}"' in mac
    assert "STREAMLIT_SERVER_MAX_UPLOAD_SIZE=10000" in docker
    assert "--server.maxUploadSize" not in docker


NORWEGIAN_SENTENCE = re.compile(r"\b(og|ikke|eller|har|laget|fiktiv|virksomhet|dataene|tilgjengeliggjort)\b", re.I)


def test_app_text_is_english() -> None:
    assert brreg.ATTRIBUTION.startswith("Contains data under the Norwegian licence")
    assert brreg.LICENCE_NAME.startswith("Norwegian Licence")
    assert {"post_town", "municipality", "county"} <= set(FREDDO_COLUMNS)
    assert not {"poststed", "kommune", "fylke"} & set(FREDDO_COLUMNS)
    activities = {unit["activity"] for unit in make_demo_units(size=20).to_dict("records") if unit["activity"]}
    assert activities == {"Fictional company created to demonstrate Prospect Signal."}
    for description in ORG_FORMS.values():
        assert re.match(r"^[A-Z][a-z]", description)  # English first, the register's Norwegian name in brackets
    for path in [*(ROOT / "src" / "prospectsignal" / "ui").rglob("*.py")]:
        if path.name in {"signal_theme.py", "signal_font.py"}:
            continue
        for literal in re.findall(r'"([^"\n]{12,})"', path.read_text(encoding="utf-8")):
            assert not NORWEGIAN_SENTENCE.search(literal), (path.name, literal)
