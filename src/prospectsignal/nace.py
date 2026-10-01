"""Industry codes (næringskoder) and their hierarchy.

Enhetsregisteret codes units with SN2025 (Statistics Norway's national version of NACE Rev. 2.1) since
1 January 2025. Codes look like ``10.110``: division ``10`` → group ``10.1`` → class ``10.11`` → subclass
``10.110``. Sections (letters A-U) sit above divisions. A filter prefix matches a code and everything below it.

Code names come from SSB Klass (classification 6, version 3218), bundled in ``data/sn2025.csv``, CC BY 4.0.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
import csv
import io
import re

NACE_SOURCE = "Industry codes: SN2025, Statistics Norway (SSB) Klass, CC BY 4.0."
UNSPECIFIED = "00.000"
_PREFIX = re.compile(r"^\d{2}(\.\d{1,3})?$")
_SECTION = re.compile(r"^[A-U]$")


@lru_cache(maxsize=1)
def _table() -> dict[str, tuple[str, str, int]]:
    """code -> (parent, name, level)."""
    text = resources.files("prospectsignal").joinpath("data/sn2025.csv").read_text(encoding="utf-8")
    return {row["code"]: (row["parent"], row["name"], int(row["level"])) for row in csv.DictReader(io.StringIO(text))}


def normalise_prefix(value: str) -> str:
    """Accept '10', '10.1', '10.11', '10.110', '10110', '1011', or a section letter 'C'.

    Digit-only input is re-dotted after the division ('10110' -> '10.110'). Raises ValueError for anything else.
    """
    text = str(value).strip().upper().replace(",", ".").replace(" ", "")
    if _SECTION.match(text):
        return text
    if text.isdigit() and 2 <= len(text) <= 5:
        text = text if len(text) == 2 else f"{text[:2]}.{text[2:]}"
    if not _PREFIX.match(text):
        raise ValueError(f"'{value}' is not a NACE code or prefix (examples: C, 10, 10.1, 10.11, 10.110)")
    return text


def parse_prefixes(text: str) -> list[str]:
    """Parse a comma/space/semicolon separated list of codes into normalised prefixes (sections expanded)."""
    tokens = [token for token in re.split(r"[\s;,]+", text.strip()) if token]
    # A bare "10.1" uses a dot as a separator inside the code, so tokens are split only on whitespace, ';' and ','.
    return expand_sections([normalise_prefix(token) for token in tokens])


def expand_sections(prefixes: list[str]) -> list[str]:
    """Replace section letters with their division codes, then de-duplicate and drop prefixes already covered."""
    expanded: list[str] = []
    for prefix in prefixes:
        if _SECTION.match(prefix):
            expanded.extend(code for code, (parent, _, level) in _table().items() if level == 2 and parent == prefix)
        else:
            expanded.append(prefix)
    unique = sorted(set(expanded), key=lambda code: (len(code), code))
    kept: list[str] = []
    for prefix in unique:
        if not any(prefix.startswith(parent) for parent in kept):
            kept.append(prefix)
    return sorted(kept)


def matches(code: str | None, prefixes: list[str] | tuple[str, ...]) -> bool:
    """True when ``code`` equals or sits below any prefix. An empty prefix list matches everything."""
    if not prefixes:
        return True
    if not code:
        return False
    return any(code.startswith(prefix) for prefix in prefixes)


def level(code: str) -> str:
    text = str(code)
    if _SECTION.match(text):
        return "section"
    if len(text) == 2:
        return "division"
    return {4: "group", 5: "class", 6: "subclass"}.get(len(text), "unknown")


def name(code: str) -> str:
    entry = _table().get(code)
    if entry:
        return entry[1]
    return "Unspecified (uoppgitt)" if code == UNSPECIFIED else ""


def label(code: str) -> str:
    text = name(code)
    return f"{code} {text}" if text else code


def division(code: str | None) -> str | None:
    return code[:2] if code and len(code) >= 2 and code[:2].isdigit() else None


def section_of(code: str) -> str | None:
    current = code
    for _ in range(6):
        entry = _table().get(current)
        if entry is None:
            return None
        parent, _, lvl = entry
        if lvl == 1:
            return current
        current = parent
    return None


def divisions() -> list[tuple[str, str]]:
    return sorted((code, entry[1]) for code, entry in _table().items() if entry[2] == 2)


def children(code: str) -> list[tuple[str, str]]:
    return sorted((child, entry[1]) for child, entry in _table().items() if entry[0] == code)
