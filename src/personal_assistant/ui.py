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

    _console: Console | None = Console()
except ImportError:  # pragma: no cover - exercised only without rich
    _console = None


def render(result: Any) -> None:
    """Print whatever a handler returned."""
    if result is None:
        return
    if _console is not None:
        _console.print(result)
    else:
        print(result)


def success(message: str) -> None:
    """Report a completed action."""
    if _console is not None:
        _console.print(f"[green]{message}[/green]")
    else:
        print(message)


def failure(message: str) -> None:
    """Report an expected error, such as invalid input."""
    if _console is not None:
        _console.print(f"[red]{message}[/red]")
    else:
        print(message)


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
