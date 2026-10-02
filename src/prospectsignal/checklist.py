"""The configurable outreach checklist shown before export (YAML; not legal advice)."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import os
from pathlib import Path

import yaml

from .errors import DataProblem

STATUSES = ("verified", "TODO(verify)")
CHANNELS = ("email", "sms", "phone", "post", "any")
ENV_OVERRIDE = "PROSPECTSIGNAL_CHECKLIST"


@dataclass(frozen=True)
class Source:
    publisher: str
    title: str
    url: str
    reference: str
    retrieved: str


@dataclass(frozen=True)
class Item:
    id: str
    title: str
    applies_to: str
    status: str
    rule: str
    action: str
    sources: tuple[Source, ...]

    @property
    def needs_verification(self) -> bool:
        return self.status != "verified"


@dataclass(frozen=True)
class Checklist:
    version: str
    disclaimer: str
    items: tuple[Item, ...]

    def rows(self) -> list[dict[str, str]]:
        """Flat rows for the XLSX export."""
        return [
            {
                "id": item.id,
                "title": item.title,
                "applies_to": item.applies_to,
                "status": item.status,
                "rule": item.rule,
                "action": item.action,
                "sources": " | ".join(f"{s.publisher}: {s.title} ({s.reference}) {s.url}" for s in item.sources),
            }
            for item in self.items
        ]


def parse(text: str) -> Checklist:
    data = yaml.safe_load(text) or {}
    problems: list[str] = []
    items: list[Item] = []
    seen: set[str] = set()
    for index, raw in enumerate(data.get("items") or []):
        where = f"item {index + 1}"
        missing = [key for key in ("id", "title", "applies_to", "status", "rule", "action") if not raw.get(key)]
        if missing:
            problems.append(f"{where}: missing {', '.join(missing)}")
            continue
        if raw["id"] in seen:
            problems.append(f"{where}: duplicate id {raw['id']}")
        seen.add(raw["id"])
        if raw["status"] not in STATUSES:
            problems.append(f"{raw['id']}: status must be one of {', '.join(STATUSES)}")
        if raw["applies_to"] not in CHANNELS:
            problems.append(f"{raw['id']}: applies_to must be one of {', '.join(CHANNELS)}")
        sources = []
        for source in raw.get("sources") or []:
            if not str(source.get("url", "")).startswith("https://"):
                problems.append(f"{raw['id']}: every source needs an https URL")
            sources.append(
                Source(
                    publisher=str(source.get("publisher", "")),
                    title=str(source.get("title", "")),
                    url=str(source.get("url", "")),
                    reference=str(source.get("reference", "")),
                    retrieved=str(source.get("retrieved", "")),
                )
            )
        if not sources:
            problems.append(f"{raw['id']}: at least one official source is required")
        items.append(
            Item(
                id=str(raw["id"]),
                title=str(raw["title"]),
                applies_to=str(raw["applies_to"]),
                status=str(raw["status"]),
                rule=" ".join(str(raw["rule"]).split()),
                action=" ".join(str(raw["action"]).split()),
                sources=tuple(sources),
            )
        )
    if not items:
        problems.append("the checklist has no items")
    if problems:
        raise DataProblem("Outreach checklist is invalid: " + "; ".join(problems))
    return Checklist(
        version=str(data.get("version", "")),
        disclaimer=" ".join(str(data.get("disclaimer", "")).split()),
        items=tuple(items),
    )


def bundled() -> Checklist:
    """The checklist shipped with the package (ignores PROSPECTSIGNAL_CHECKLIST)."""
    return parse(resources.files("prospectsignal").joinpath("data/outreach_checklist.yaml").read_text(encoding="utf-8"))


def load(path: str | Path | None = None) -> Checklist:
    """Load the checklist from ``path``, the PROSPECTSIGNAL_CHECKLIST file, or the bundled default."""
    chosen = path or os.environ.get(ENV_OVERRIDE)
    if chosen:
        return parse(Path(chosen).read_text(encoding="utf-8"))
    return bundled()
