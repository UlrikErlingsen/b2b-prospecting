"""Ideal-customer-profile (ICP) filter sets: plain data, validated, serialisable, storage-agnostic."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import date
import json

from . import nace, regions
from .errors import DataProblem

ENTITY_KINDS = ("hovedenhet", "underenhet", "both")


@dataclass(frozen=True)
class ICP:
    """A named filter set. Empty lists mean "any"."""

    name: str = "Untitled ICP"
    nace_prefixes: tuple[str, ...] = ()
    nace_any_code: bool = False  # also match secondary codes (naeringskode2/3), not only the main code
    fylker: tuple[str, ...] = ()
    kommuner: tuple[str, ...] = ()
    employees_min: int | None = None
    employees_max: int | None = None
    founded_from: date | None = None
    founded_to: date | None = None
    org_forms: tuple[str, ...] = ()
    include_enk: bool = False
    vat_registered: bool | None = None  # None = either
    exclude_inactive: bool = True  # konkurs, under avvikling, tvangsavvikling, nedlagt underenhet
    entity_kind: str = "hovedenhet"
    notes: str = field(default="", compare=False)

    def validated(self) -> "ICP":
        """Return a normalised copy, or raise DataProblem with every problem found."""
        problems: list[str] = []
        try:
            prefixes = tuple(nace.expand_sections([nace.normalise_prefix(p) for p in self.nace_prefixes]))
        except ValueError as exc:
            problems.append(str(exc))
            prefixes = ()
        try:
            fylker = tuple(regions.expand_regions(list(self.fylker)))
        except ValueError as exc:
            problems.append(str(exc))
            fylker = ()
        kommuner = tuple(sorted({str(k).strip().zfill(4) for k in self.kommuner if str(k).strip()}))
        bad_kommuner = [k for k in kommuner if not (len(k) == 4 and k.isdigit())]
        if bad_kommuner:
            problems.append("Municipality (kommune) numbers must have four digits: " + ", ".join(bad_kommuner))
        for label, value in (("Minimum", self.employees_min), ("Maximum", self.employees_max)):
            if value is not None and value < 0:
                problems.append(f"{label} employees cannot be negative.")
        if (
            self.employees_min is not None
            and self.employees_max is not None
            and self.employees_min > self.employees_max
        ):
            problems.append("Minimum employees is larger than maximum employees.")
        if self.founded_from and self.founded_to and self.founded_from > self.founded_to:
            problems.append("The founded-from date is after the founded-to date.")
        if self.entity_kind not in ENTITY_KINDS:
            problems.append(f"Unit level must be one of {', '.join(ENTITY_KINDS)}.")
        forms = tuple(sorted({f.strip().upper() for f in self.org_forms if f.strip()}))
        if "ENK" in forms and not self.include_enk:
            problems.append("ENK is listed as an organisation form, but 'include ENK' is off. Turn it on deliberately.")
        if not self.name.strip():
            problems.append("Give the ICP a name.")
        if problems:
            raise DataProblem(" ".join(problems))
        return replace(
            self, name=self.name.strip(), nace_prefixes=prefixes, fylker=fylker, kommuner=kommuner, org_forms=forms
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in ("founded_from", "founded_to"):
            data[key] = data[key].isoformat() if data[key] else None
        for key in ("nace_prefixes", "fylker", "kommuner", "org_forms"):
            data[key] = list(data[key])
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict) -> "ICP":
        known = {key: value for key, value in data.items() if key in cls.__dataclass_fields__}
        for key in ("founded_from", "founded_to"):
            if known.get(key):
                known[key] = date.fromisoformat(known[key])
        for key in ("nace_prefixes", "fylker", "kommuner", "org_forms"):
            if key in known:
                known[key] = tuple(known[key] or ())
        return cls(**known)

    @classmethod
    def from_json(cls, text: str) -> "ICP":
        return cls.from_dict(json.loads(text))

    def describe(self) -> list[str]:
        """Human-readable lines, used on screen and in exports."""
        lines = []
        lines.append("Industry: " + (", ".join(nace.label(p) for p in self.nace_prefixes) or "any"))
        if self.nace_any_code:
            lines.append("Industry match includes secondary codes")
        lines.append("Fylke: " + (", ".join(regions.fylke_name(f) for f in self.fylker) or "any"))
        if self.kommuner:
            lines.append("Municipality numbers: " + ", ".join(self.kommuner))
        low = self.employees_min if self.employees_min is not None else 0
        high = self.employees_max if self.employees_max is not None else "∞"
        lines.append(f"Employees: {low}–{high}")
        if self.founded_from or self.founded_to:
            lines.append(f"Founded: {self.founded_from or '…'} to {self.founded_to or '…'}")
        lines.append("Organisation form: " + (", ".join(self.org_forms) or "any"))
        lines.append(
            "ENK and unknown-form sub-units: "
            + ("included (person names — handle as personal data)" if self.include_enk else "excluded")
        )
        if self.vat_registered is not None:
            lines.append("VAT-registered: " + ("yes" if self.vat_registered else "no"))
        lines.append("Inactive units: " + ("excluded" if self.exclude_inactive else "included"))
        lines.append("Unit level: " + self.entity_kind)
        return lines


def demo_icp() -> ICP:
    """The brief's demo ICP for the fictional brand Fjellbrus.

    "Viken/Østfold": Viken no longer exists (dissolved 2024), so the demo uses the former Viken counties, which
    include Østfold.
    """
    return ICP(
        name="Fjellbrus — food & beverage producers, former Viken, 10–100 employees",
        nace_prefixes=("10", "11"),
        fylker=regions.REGION_ALIASES["Viken (former, 2020-2023)"],
        employees_min=10,
        employees_max=100,
        notes="Demo ICP for the fictional beverage brand Fjellbrus.",
    )
