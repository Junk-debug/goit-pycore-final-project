"""Presentation layer.

Every handler returns data and never prints. This module is the only place
that writes to the terminal, which keeps the domain free of formatting and
lets the planned web interface reuse the same handlers (D8).

`rich` is optional by D21: when it is unavailable the same calls fall back to
plain printing, so a missing package costs appearance, never function.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    _console: Console | None = Console()
except ImportError:  # pragma: no cover - exercised only without rich
    _console = None


def render(result: Any) -> None:
    """Print whatever a handler returned.

    Plain strings are printed verbatim: `rich` would otherwise read square
    brackets as its own markup and colour arbitrary tokens on its own, which
    mangles pre-formatted text such as the output of `--help`. Objects built
    by this module, tables among them, are rendered normally.
    """
    if result is None:
        return
    if _console is None:
        print(result)
    elif isinstance(result, str):
        _console.print(result, markup=False, highlight=False)
    else:
        _console.print(result)


def success(message: str) -> None:
    """Report a completed action."""
    _styled(message, "green")


def failure(message: str) -> None:
    """Report an expected error, such as invalid input."""
    _styled(message, "red")


def _styled(message: str, colour: str) -> None:
    """Print a whole message in one colour, never parsing its content."""
    if _console is None:
        print(message)
        return
    _console.print(Text(message, style=colour))


def table(title: str, columns: Sequence[str], rows: Sequence[Sequence[str]]) -> Any:
    """Build a table for a handler to return, or plain text without rich."""
    if _console is not None:
        built = Table(title=title)
        for column in columns:
            built.add_column(column)
        for row in rows:
            built.add_row(*[str(cell) for cell in row])
        return built

    header = " | ".join(columns)
    body = "\n".join(" | ".join(str(cell) for cell in row) for row in rows)
    return f"{title}\n{header}\n{body}" if rows else f"{title}\n{header}"
