"""Rebuild the bundled reference data in src/prospectsignal/data/.

Run manually by a maintainer (never by the app or the tests):

    python scripts/build_reference_data.py

Sources (verified 2026-10-01):

- SN2025 industry codes: Statistics Norway (SSB) Klass, classification 6, version 3218
  ("Næringsgruppering (SN) 2025", valid from 2025-01-01). Licence: CC BY 4.0 (https://www.ssb.no/diverse/lisens).
- County (fylke) boundaries: Kartverket, "Administrative enheter fylker", served by the Kommuneinfo API
  (https://api.kartverket.no/kommuneinfo/v1). Licence: CC BY 4.0 (Geonorge metadata
  6093c8a8-fa80-11e6-bc64-92361f002671). Polygons are simplified here for a small offline map;
  they are not suitable for any boundary-accurate use.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prospectsignal.http import make_session  # noqa: E402

SESSION = make_session()
OUT = ROOT / "src" / "prospectsignal" / "data"
KLASS_VERSION = "https://data.ssb.no/api/klass/v1/versions/3218"
KOMMUNEINFO = "https://api.kartverket.no/kommuneinfo/v1"
TOLERANCE_DEG = 0.012
MIN_RING_AREA = 0.002  # square degrees; drops small islands from the overview map only
TIMEOUT = 60


def build_sn2025() -> None:
    response = SESSION.get(KLASS_VERSION, headers={"Accept": "application/json"}, timeout=TIMEOUT)
    response.raise_for_status()
    items = response.json()["classificationItems"]
    rows = [
        {"code": item["code"], "parent": item.get("parentCode") or "", "level": item["level"], "name": item["name"]}
        for item in items
    ]
    path = OUT / "sn2025.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["code", "parent", "level", "name"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} SN2025 codes to {path}")


def _perpendicular(point, start, end) -> float:
    (x, y), (x1, y1), (x2, y2) = point, start, end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / math.hypot(dx, dy)


def _douglas_peucker(points: list, tolerance: float) -> list:
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        index, distance = 0, 0.0
        for i in range(first + 1, last):
            d = _perpendicular(points[i], points[first], points[last])
            if d > distance:
                index, distance = i, d
        if distance > tolerance:
            keep[index] = True
            stack.extend([(first, index), (index, last)])
    return [p for p, k in zip(points, keep) if k]


def _signed_area(ring: list) -> float:
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:])) / 2


def _ring_area(ring: list) -> float:
    return abs(_signed_area(ring))


def _simplify_multipolygon(coordinates: list) -> list:
    polygons = []
    for polygon in coordinates:
        outer = polygon[0]
        if _ring_area(outer) < MIN_RING_AREA:
            continue
        simplified = _douglas_peucker(outer, TOLERANCE_DEG)
        if len(simplified) >= 4:
            # Plotly draws geo shapes with d3-geo, which needs exterior rings wound clockwise (the opposite of
            # RFC 7946). A counter-clockwise ring would be read as "the whole globe except this county".
            if _signed_area(simplified) > 0:
                simplified = simplified[::-1]
            polygons.append([[[round(x, 4), round(y, 4)] for x, y in simplified]])
    return polygons


def build_fylker() -> None:
    listing = SESSION.get(f"{KOMMUNEINFO}/fylker", timeout=TIMEOUT)
    listing.raise_for_status()
    features = []
    for fylke in sorted(listing.json(), key=lambda item: item["fylkesnummer"]):
        number = fylke["fylkesnummer"]
        response = SESSION.get(f"{KOMMUNEINFO}/fylker/{number}/omrade", params={"utkoordsys": 4326}, timeout=TIMEOUT)
        response.raise_for_status()
        area = response.json()["omrade"]
        coordinates = area["coordinates"] if area["type"] == "MultiPolygon" else [area["coordinates"]]
        features.append(
            {
                "type": "Feature",
                "id": number,
                "properties": {"fylkesnummer": number, "fylkesnavn": fylke["fylkesnavn"]},
                "geometry": {"type": "MultiPolygon", "coordinates": _simplify_multipolygon(coordinates)},
            }
        )
        print(f"fylke {number} {fylke['fylkesnavn']}")
    collection = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "Kartverket, Administrative enheter fylker (Kommuneinfo API)",
            "licence": "CC BY 4.0",
            "simplified": f"Douglas-Peucker {TOLERANCE_DEG} degrees, small islands removed, rings wound clockwise (d3)",
        },
        "features": features,
    }
    path = OUT / "fylker.geojson"
    path.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    build_sn2025()
    build_fylker()
