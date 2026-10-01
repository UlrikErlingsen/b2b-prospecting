import pytest

from prospectsignal import nace, regions


def test_prefix_hierarchy_matches_down_the_tree():
    assert nace.matches("10.110", ["10"])
    assert nace.matches("10.110", ["10.1"])
    assert nace.matches("10.110", ["10.11"])
    assert nace.matches("10.110", ["10.110"])
    assert not nace.matches("10.120", ["10.11"])
    assert not nace.matches("11.050", ["10"])
    assert not nace.matches("10.710", ["10.1"])
    assert nace.matches("anything", [])
    assert not nace.matches(None, ["10"])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("10", "10"), ("10.1", "10.1"), ("1011", "10.11"), ("10110", "10.110"), (" 10,11 ", "10.11"), ("c", "C")],
)
def test_normalise_prefix(raw, expected):
    assert nace.normalise_prefix(raw) == expected


@pytest.mark.parametrize("raw", ["1", "abc", "10.1111", "123456", "Z"])
def test_bad_prefix_raises(raw):
    with pytest.raises(ValueError):
        nace.normalise_prefix(raw)


def test_parse_drops_prefixes_covered_by_a_parent_and_expands_sections():
    assert nace.parse_prefixes("10, 10.1; 10.110 11.05") == ["10", "11.05"]
    manufacturing = nace.parse_prefixes("C")
    assert "10" in manufacturing and "11" in manufacturing and "33" in manufacturing
    assert "01" not in manufacturing


def test_sn2025_names_and_levels():
    assert nace.name("10") == "Produksjon av nærings- og nytelsesmidler"
    assert nace.level("10.110") == "subclass"
    assert nace.level("10.11") == "class"
    assert nace.section_of("10.110") == "C"
    assert nace.label("00.000").startswith("00.000 Unspecified")


def test_fylker_after_2024_reform_and_viken_alias():
    assert "30" not in regions.FYLKER
    assert regions.expand_regions(["Viken (former, 2020-2023)"]) == ["31", "32", "33"]
    assert regions.fylke_for_kommune("0301") == "03"
    assert regions.fylke_for_kommune("301") is None
    assert regions.fylke_name("31") == "Østfold"
    with pytest.raises(ValueError):
        regions.expand_regions(["30"])


def test_bundled_map_covers_every_fylke():
    geojson = regions.fylker_geojson()
    numbers = {feature["properties"]["fylkesnummer"] for feature in geojson["features"]}
    assert numbers == set(regions.FYLKER)
    assert "CC BY 4.0" in geojson["metadata"]["licence"]


def test_map_rings_are_clockwise_for_plotly():
    # d3-geo (used by plotly) reads a counter-clockwise exterior ring as "everything except this county".
    for feature in regions.fylker_geojson()["features"]:
        for polygon in feature["geometry"]["coordinates"]:
            ring = polygon[0]
            signed = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:])) / 2
            assert signed < 0, feature["properties"]["fylkesnavn"]
