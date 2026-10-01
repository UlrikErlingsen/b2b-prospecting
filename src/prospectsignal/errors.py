"""User-facing errors raised by Prospect Signal."""

from __future__ import annotations


class DataProblem(ValueError):
    """Raised when a request cannot be honoured with the data or input supplied."""


class RegisterUnavailable(RuntimeError):
    """Raised when Brønnøysundregistrene cannot be reached or answers unexpectedly."""


def friendly_message(exc: Exception) -> str:
    """Return a useful message without exposing an internal traceback by default."""
    if isinstance(exc, (DataProblem, RegisterUnavailable)):
        return str(exc)
    if isinstance(exc, ValueError):
        return f"Prospect Signal could not complete that step: {exc}"
    return (
        "Prospect Signal could not complete that step. Try again, or set PROSPECTSIGNAL_DEBUG=1 before launch "
        "if you need technical details."
    )
