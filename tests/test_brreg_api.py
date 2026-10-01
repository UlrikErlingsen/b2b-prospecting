"""Brønnøysund API handling with recorded responses only (no live calls)."""

from __future__ import annotations

from datetime import date
import json

import pytest

from conftest import FIXTURES
from prospectsignal import Store, brreg
from prospectsignal.schema import UNIT_COLUMNS
from prospectsignal.storage import assert_no_person_columns

ENHET = json.loads((FIXTURES / "api_enhet_974760673.json").read_text(encoding="utf-8"))
UNDERENHET = json.loads((FIXTURES / "api_underenhet_994667084.json").read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, status: int, payload=None, body: bytes = b"", headers=None):
        self.status_code = status
        self._payload = payload
        self._body = body
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"{self.status_code}")

    def iter_content(self, chunk_size=1):
        for start in range(0, len(self._body), chunk_size):
            yield self._body[start : start + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, routes: dict[str, FakeResponse]):
        self.routes = routes
        self.calls: list[str] = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return self.routes.get(url, FakeResponse(404))

    def head(self, url, **kwargs):
        self.calls.append("HEAD " + url)
        return self.routes.get(url, FakeResponse(404))


def test_recorded_api_payload_contains_contact_fields_we_drop():
    assert "epostadresse" in ENHET and "telefon" in ENHET
    record = brreg.normalise_api_unit(ENHET, "hovedenhet", downloaded_at=date(2026, 10, 1))
    assert set(record) == set(UNIT_COLUMNS)
    assert_no_person_columns(list(record))
    assert ENHET["epostadresse"] not in json.dumps(record, default=str)
    assert record["org_nr"] == "974760673"
    assert record["employees"] == ENHET["antallAnsatte"]
    assert record["kommune_nr"] == "1813" and record["fylke_nr"] == "18"
    assert record["address"] == "Havnegata 48"
    assert record["source"] == "brreg-api"


def test_underenhet_payload_inherits_parent_form():
    parent = brreg.normalise_api_unit(ENHET, "hovedenhet")
    record = brreg.normalise_api_unit(UNDERENHET, "underenhet", parent=parent)
    assert record["entity_kind"] == "underenhet"
    assert record["parent_org_nr"] == "974760673"
    assert record["org_form"] == parent["org_form"]
    assert record["unit_form"] == "BEDR"
    assert record["kommune"] == "NARVIK"
    assert record["founded"] == date(2009, 1, 1)


def test_fetch_falls_back_to_underenhet_and_reports_missing():
    api = brreg.API_ROOT
    session = FakeSession({f"{api}/underenheter/994667084": FakeResponse(200, UNDERENHET)})
    kind, payload = brreg.fetch_unit("994667084", session=session)
    assert kind == "underenhet" and payload["navn"] == UNDERENHET["navn"]
    assert session.calls == [f"{api}/enheter/994667084", f"{api}/underenheter/994667084"]
    assert brreg.fetch_unit("974760673", session=FakeSession({})) is None


def test_fetch_rejects_invalid_number_without_calling():
    session = FakeSession({})
    with pytest.raises(ValueError):
        brreg.fetch_unit("123", session=session)
    assert session.calls == []


def test_refresh_removes_units_no_longer_in_open_data():
    store = Store()
    store.upsert_unit(brreg.normalise_api_unit(ENHET, "hovedenhet"))
    assert store.unit_count() == 1
    assert brreg.refresh_unit(store, "974760673", session=FakeSession({})) is None
    assert store.unit_count() == 0


def test_refresh_updates_local_copy():
    store = Store()
    session = FakeSession({f"{brreg.API_ROOT}/enheter/974760673": FakeResponse(200, ENHET)})
    record = brreg.refresh_unit(store, "974760673", session=session)
    assert record["name"] == ENHET["navn"]
    assert store.get_unit("974760673")["employees"] == ENHET["antallAnsatte"]


def test_load_register_streams_bulk_file_with_progress(bulk_files, tmp_path):
    enheter, _ = bulk_files
    body = enheter.read_bytes()
    headers = {"content-length": str(len(body)), "etag": '"abc"', "last-modified": "Thu, 01 Oct 2026 02:27:24 GMT"}
    session = FakeSession({brreg.BULK_URLS["enheter"]: FakeResponse(200, body=body, headers=headers)})
    progress: list[tuple[str, int, int | None]] = []
    store = Store()
    summary = brreg.load_register(
        store, tmp_path, session=session, progress=lambda *args: progress.append(args), today=date(2026, 10, 1)
    )
    assert summary["counts"]["hovedenheter"] == 4
    assert progress[-1] == ("enheter", len(body), len(body))
    assert store.get_meta("dataset") == "register"
    assert store.get_meta("enheter_last_modified") == headers["last-modified"]
    assert store.get_meta("downloaded_at") == "2026-10-01"
    assert not (tmp_path / "raw" / "enheter.csv.gz").exists()  # raw file removed after indexing


def test_incomplete_download_is_rejected(tmp_path):
    session = FakeSession(
        {brreg.BULK_URLS["enheter"]: FakeResponse(200, body=b"abc", headers={"content-length": "10"})}
    )
    with pytest.raises(brreg.RegisterUnavailable):
        brreg.download_bulk("enheter", tmp_path / "e.csv.gz", session=session)
    assert not (tmp_path / "e.csv.gz").exists()


def test_register_urls():
    assert brreg.register_url("974760673") == "https://virksomhet.brreg.no/nb/oppslag/enheter/974760673"
    assert brreg.register_url("994667084", "underenhet").endswith("/underenheter/994667084")


def test_attribution_follows_nlod_wording():
    assert brreg.ATTRIBUTION.startswith(
        "Inneholder data under Norsk lisens for offentlige data (NLOD) tilgjengeliggjort av Brønnøysundregistrene."
    )
    assert "endret" in brreg.ATTRIBUTION or "filtrert" in brreg.ATTRIBUTION  # NLOD § 5: mark changes
