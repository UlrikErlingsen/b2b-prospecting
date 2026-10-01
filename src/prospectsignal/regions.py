"""Norwegian counties (fylker) after the 1 January 2024 reform, and the bundled county map.

Fylke numbers and names verified against Kartverket's Kommuneinfo API on 2026-10-01. A kommune number's first two
digits are its fylke number. Viken (30) was dissolved on 1 January 2024 into Østfold (31), Akershus (32) and
Buskerud (33); the register no longer uses 30, so "Viken" is offered only as an alias for those three.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
import json

FYLKER: dict[str, str] = {
    "03": "Oslo",
    "11": "Rogaland",
    "15": "Møre og Romsdal",
    "18": "Nordland",
    "31": "Østfold",
    "32": "Akershus",
    "33": "Buskerud",
    "34": "Innlandet",
    "39": "Vestfold",
    "40": "Telemark",
    "42": "Agder",
    "46": "Vestland",
    "50": "Trøndelag",
    "55": "Troms",
    "56": "Finnmark",
}
# Svalbard is not a fylke, but its kommune numbers (21xx) occur in the register.
OTHER_AREAS: dict[str, str] = {"21": "Svalbard"}
REGION_ALIASES: dict[str, tuple[str, ...]] = {"Viken (former, 2020-2023)": ("31", "32", "33")}

MAP_SOURCE = "County boundaries: Kartverket, Administrative enheter fylker (CC BY 4.0), simplified for an overview map."


def fylke_for_kommune(kommune_nr: str | None) -> str | None:
    if not kommune_nr or len(str(kommune_nr)) != 4 or not str(kommune_nr).isdigit():
        return None
    return str(kommune_nr)[:2]


def fylke_name(fylke_nr: str | None) -> str:
    if not fylke_nr:
        return "Unknown or abroad"
    return FYLKER.get(fylke_nr) or OTHER_AREAS.get(fylke_nr) or f"Fylke {fylke_nr}"


def expand_regions(selection: list[str] | tuple[str, ...]) -> list[str]:
    """Turn fylke numbers and aliases (e.g. former Viken) into a sorted, de-duplicated list of fylke numbers."""
    numbers: set[str] = set()
    for item in selection:
        if item in REGION_ALIASES:
            numbers.update(REGION_ALIASES[item])
        elif item in FYLKER or item in OTHER_AREAS:
            numbers.add(item)
        else:
            raise ValueError(f"Unknown fylke: {item}")
    return sorted(numbers)


@lru_cache(maxsize=1)
def fylker_geojson() -> dict:
    text = resources.files("prospectsignal").joinpath("data/fylker.geojson").read_text(encoding="utf-8")
    return json.loads(text)
