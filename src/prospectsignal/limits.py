"""Data limits: none when Prospect Signal runs locally; hard caps only in a public demo.

Run on someone's own computer (standalone, a local Signal Hub, or an internal company deployment), the app has no
built-in limit on the register size, shortlist length, notes or saved ICPs: memory and disk are the limit. A public
demo sets ``SIGNAL_PUBLIC=1`` (Signal Hub's public Docker image does), and then the caps below protect the shared
server. Every cap lives in this module and is read at call time, so the environment decides.

On-screen tables show at most a few thousand rows because the browser has to draw them; that is a display choice
with a visible note, not a data limit (counts, market tables and exports always use all matching units).
"""

from __future__ import annotations

import os

DEMO_MAX_SHORTLIST = 500
DEMO_MAX_NOTE_CHARS = 2_000
DEMO_MAX_SAVED_ICPS = 25

DEMO_NOTE = "This is a limit of the public demo; the downloaded app has no such limit."
MEMORY_MESSAGE = (
    "There is not enough memory for this step on this computer. Close other programs and try again, or narrow the "
    "filters."
)


def is_public() -> bool:
    """True only in a public demo deployment (``SIGNAL_PUBLIC=1``)."""
    return os.environ.get("SIGNAL_PUBLIC") == "1"


def _cap(value: int) -> int | None:
    return value if is_public() else None


def max_shortlist() -> int | None:
    return _cap(DEMO_MAX_SHORTLIST)


def max_note_chars() -> int | None:
    return _cap(DEMO_MAX_NOTE_CHARS)


def max_saved_icps() -> int | None:
    return _cap(DEMO_MAX_SAVED_ICPS)


def register_download_allowed() -> bool:
    """The 150 MB register download and API refresh are for your own computer, not a shared public server."""
    return not is_public()


def exceeds(value: int, limit: int | None) -> bool:
    return limit is not None and value > limit


def demo_message(what: str) -> str:
    """A capped message: names the demo limit and says the downloaded app has none."""
    return f"{what} {DEMO_NOTE}"
