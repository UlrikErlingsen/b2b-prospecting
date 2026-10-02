from __future__ import annotations

import csv
import gzip
import io
from pathlib import Path

import pytest
import requests

from prospectsignal import Store, load_demo

FIXTURES = Path(__file__).parent / "fixtures"
ENHET_HEADER = FIXTURES / "enheter_header_2026-10-01.csv"
UNDERENHET_HEADER = FIXTURES / "underenheter_header_2026-10-01.csv"


@pytest.fixture(autouse=True)
def standalone_mode_by_default(monkeypatch):
    """Tests run the standalone app unless they opt into Signal Hub mode themselves."""
    monkeypatch.delenv("SIGNAL_HUB", raising=False)


@pytest.fixture(autouse=True)
def no_live_network(monkeypatch):
    """Tests use recorded fixtures only; any real HTTP request fails loudly."""

    def refuse(*args, **kwargs):
        raise RuntimeError("Live network call attempted in tests")

    monkeypatch.setattr(requests.sessions.Session, "request", refuse)


def header(path: Path) -> list[str]:
    return next(csv.reader(io.StringIO(path.read_text(encoding="utf-8"))))


def write_bulk(path: Path, header_path: Path, rows: list[dict[str, str]]) -> Path:
    """Write a gzip CSV in the register's format (recorded header, every cell quoted) with fictional rows."""
    columns = header(header_path)
    unknown = {key for row in rows for key in row} - set(columns)
    assert not unknown, f"fixture uses columns the real file lacks: {unknown}"
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(column, "") for column in columns])
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write(buffer.getvalue())
    return path


# Fictional units: numbers start with 1 (real ones start with 8 or 9) and pass MOD11; names say FIXTURE.
# Phone and e-mail values are fake and must never reach storage.
ENHETER_ROWS: list[dict[str, str]] = [
    {
        "organisasjonsnummer": "100011379",
        "navn": "FIXTURE ÆRLIG ØL OG BRØD AS",
        "organisasjonsform.kode": "AS",
        "organisasjonsform.beskrivelse": "Aksjeselskap",
        "naeringskode1.kode": "11.050",
        "naeringskode1.beskrivelse": "Produksjon av øl",
        "naeringskode2.kode": "10.710",
        "naeringskode2.beskrivelse": "Produksjon av brød og ferske konditorvarer",
        "harRegistrertAntallAnsatte": "true",
        "antallAnsatte": "42",
        "hjemmeside": "www.fixture-ol.example",
        "epostadresse": "kari.fixture@fixture-ol.example",
        "telefon": "11 22 33 44",
        "mobil": "999 88 777",
        "forretningsadresse.adresse": 'c/o Regnskap "Å" AS\nBryggeveien 1',
        "forretningsadresse.postnummer": "0150",
        "forretningsadresse.poststed": "OSLO",
        "forretningsadresse.kommune": "OSLO",
        "forretningsadresse.kommunenummer": "0301",
        "forretningsadresse.landkode": "NO",
        "registreringsdatoenhetsregisteret": "2019-03-01",
        "stiftelsesdato": "2019-02-15",
        "registrertIMvaRegisteret": "true",
        "registrertIForetaksregisteret": "true",
        "konkurs": "false",
        "underAvvikling": "false",
        "underTvangsavviklingEllerTvangsopplosning": "false",
    },
    {
        "organisasjonsnummer": "100022745",
        "navn": "KARI FIXTURESEN BAKERI",
        "organisasjonsform.kode": "ENK",
        "organisasjonsform.beskrivelse": "Enkeltpersonforetak",
        "naeringskode1.kode": "10.710",
        "naeringskode1.beskrivelse": "Produksjon av brød og ferske konditorvarer",
        "harRegistrertAntallAnsatte": "true",
        "antallAnsatte": "",
        "epostadresse": "kari@fixturesen.example",
        "mobil": "911 22 333",
        "forretningsadresse.adresse": "Hjemmeveien 7",
        "forretningsadresse.postnummer": "1606",
        "forretningsadresse.poststed": "FREDRIKSTAD",
        "forretningsadresse.kommune": "FREDRIKSTAD",
        "forretningsadresse.kommunenummer": "3107",
        "forretningsadresse.landkode": "NO",
        "registreringsdatoenhetsregisteret": "2021-05-05",
        "stiftelsesdato": "2021-05-01",
        "registrertIMvaRegisteret": "false",
        "konkurs": "false",
        "underAvvikling": "false",
        "underTvangsavviklingEllerTvangsopplosning": "false",
    },
    {
        "organisasjonsnummer": "100034115",
        "navn": "FIXTURE KONKURS MØLLE AS",
        "organisasjonsform.kode": "AS",
        "organisasjonsform.beskrivelse": "Aksjeselskap",
        "naeringskode1.kode": "10.610",
        "naeringskode1.beskrivelse": "Produksjon av kornvarer",
        "harRegistrertAntallAnsatte": "true",
        "antallAnsatte": "15",
        "forretningsadresse.adresse": "Møllevegen 2",
        "forretningsadresse.postnummer": "1710",
        "forretningsadresse.poststed": "SARPSBORG",
        "forretningsadresse.kommune": "SARPSBORG",
        "forretningsadresse.kommunenummer": "3105",
        "forretningsadresse.landkode": "NO",
        "registreringsdatoenhetsregisteret": "2005-01-01",
        "stiftelsesdato": "2004-12-01",
        "konkurs": "true",
        "underAvvikling": "true",
    },
    {
        "organisasjonsnummer": "100045486",
        "navn": "FIXTURE HOLDING AS",
        "organisasjonsform.kode": "AS",
        "organisasjonsform.beskrivelse": "Aksjeselskap",
        "naeringskode1.kode": "64.200",
        "naeringskode1.beskrivelse": "Holdingselskaper",
        "harRegistrertAntallAnsatte": "false",
        "postadresse.adresse": "Postboks 12",
        "postadresse.postnummer": "3015",
        "postadresse.poststed": "DRAMMEN",
        "postadresse.kommune": "DRAMMEN",
        "postadresse.kommunenummer": "3301",
        "postadresse.landkode": "NO",
        "registreringsdatoenhetsregisteret": "2010-06-01",
        "stiftelsesdato": "2010-05-20",
    },
]

UNDERENHETER_ROWS: list[dict[str, str]] = [
    {
        "organisasjonsnummer": "100056852",
        "navn": "FIXTURE ÆRLIG ØL AVD. HALDEN",
        "organisasjonsform.kode": "BEDR",
        "naeringskode1.kode": "11.050",
        "naeringskode1.beskrivelse": "Produksjon av øl",
        "harRegistrertAntallAnsatte": "true",
        "antallAnsatte": "30",
        "telefon": "22 33 44 55",
        "beliggenhetsadresse.adresse": "Bryggeriveien 3",
        "beliggenhetsadresse.postnummer": "1767",
        "beliggenhetsadresse.poststed": "HALDEN",
        "beliggenhetsadresse.kommune": "HALDEN",
        "beliggenhetsadresse.kommunenummer": "3101",
        "beliggenhetsadresse.landkode": "NO",
        "registreringsdatoIEnhetsregisteret": "2020-01-10",
        "oppstartsdato": "2020-01-01",
        "registrertIMvaregisteret": "true",
        "overordnetEnhet": "100011379",
    },
    {
        "organisasjonsnummer": "100068222",
        "navn": "KARI FIXTURESEN BAKERI AVD. MOSS",
        "organisasjonsform.kode": "BEDR",
        "naeringskode1.kode": "10.710",
        "harRegistrertAntallAnsatte": "false",
        "beliggenhetsadresse.adresse": "Bakergata 9",
        "beliggenhetsadresse.postnummer": "1530",
        "beliggenhetsadresse.poststed": "MOSS",
        "beliggenhetsadresse.kommune": "MOSS",
        "beliggenhetsadresse.kommunenummer": "3103",
        "beliggenhetsadresse.landkode": "NO",
        "oppstartsdato": "2022-02-02",
        "overordnetEnhet": "100022745",
    },
    {
        "organisasjonsnummer": "100079593",
        "navn": "FIXTURE NEDLAGT LAGER",
        "organisasjonsform.kode": "BEDR",
        "naeringskode1.kode": "11.050",
        "harRegistrertAntallAnsatte": "true",
        "antallAnsatte": "8",
        "beliggenhetsadresse.kommunenummer": "3107",
        "beliggenhetsadresse.kommune": "FREDRIKSTAD",
        "beliggenhetsadresse.postnummer": "1606",
        "overordnetEnhet": "100011379",
        "nedleggelsesdato": "2024-12-31",
    },
    {
        "organisasjonsnummer": "100090950",
        "navn": "OLA FIXTURESEN SNEKKERVERKSTED",
        "organisasjonsform.kode": "BEDR",
        "naeringskode1.kode": "16.230",
        "harRegistrertAntallAnsatte": "false",
        "beliggenhetsadresse.adresse": "Heimveien 4",
        "beliggenhetsadresse.postnummer": "3015",
        "beliggenhetsadresse.poststed": "DRAMMEN",
        "beliggenhetsadresse.kommune": "DRAMMEN",
        "beliggenhetsadresse.kommunenummer": "3301",
        "beliggenhetsadresse.landkode": "NO",
        "overordnetEnhet": "100101900",  # parent not in the enheter file (removed from open data)
    },
]
FAKE_CONTACT_VALUES = (
    "kari.fixture@fixture-ol.example",
    "kari@fixturesen.example",
    "11 22 33 44",
    "999 88 777",
    "911 22 333",
    "22 33 44 55",
)


@pytest.fixture
def bulk_files(tmp_path) -> tuple[Path, Path]:
    enheter = write_bulk(tmp_path / "enheter.csv.gz", ENHET_HEADER, ENHETER_ROWS)
    underenheter = write_bulk(tmp_path / "underenheter.csv.gz", UNDERENHET_HEADER, UNDERENHETER_ROWS)
    return enheter, underenheter


@pytest.fixture
def demo_store() -> Store:
    store = Store()
    load_demo(store)
    return store
