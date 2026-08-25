"""Turning raw command-line text into values."""

from __future__ import annotations


def commas(raw: str) -> tuple[str, ...]:
    """Split a comma-separated value, ignoring spaces around the commas."""
    return tuple(part.strip() for part in raw.split(",") if part.strip())
