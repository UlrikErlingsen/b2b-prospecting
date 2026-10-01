"""Norwegian organisation numbers: always nine-character strings with a MOD11 check digit.

Same rule as Freddo CRM (signal-crm ``core/orgnr.py``): strip spaces and the ``NO``/``MVA`` decorations, keep the
value a string so leading zeros survive, and never store it as a number.
"""

from __future__ import annotations

WEIGHTS = (3, 2, 7, 6, 5, 4, 3, 2)
_SEPARATORS = (" ", " ", " ", ".", "-")


def normalise(value: object) -> str:
    """Strip separators and the 'NO'/'MVA' decorations; the result is always a string."""
    if value is None:
        return ""
    text = str(value).strip().upper()
    for separator in _SEPARATORS:
        text = text.replace(separator, "")
    if text.startswith("NO"):
        text = text[2:]
    if text.endswith("MVA"):
        text = text[:-3]
    return text


def check_digit(first_eight: str) -> int | None:
    """MOD11 check digit for the first eight digits, or None when no valid digit exists (remainder gives 10)."""
    total = sum(int(digit) * weight for digit, weight in zip(first_eight, WEIGHTS))
    remainder = total % 11
    check = 0 if remainder == 0 else 11 - remainder
    return None if check == 10 else check


def is_valid(value: object) -> bool:
    text = normalise(value)
    if len(text) != 9 or not text.isdigit():
        return False
    return check_digit(text[:8]) == int(text[8])


def validate(value: object) -> str:
    text = normalise(value)
    if not is_valid(text):
        raise ValueError(f"Invalid organisation number: {value!r} (nine digits with a MOD11 check digit)")
    return text


def format_display(value: object) -> str:
    """'923609016' -> '923 609 016' (display only; storage keeps the plain string)."""
    text = normalise(value)
    return f"{text[:3]} {text[3:6]} {text[6:]}" if len(text) == 9 else text
