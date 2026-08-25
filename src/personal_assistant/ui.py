"""Presentation layer.

Every handler returns data and never prints. This module is the only place
that writes to the terminal, which keeps the domain free of formatting and
lets the planned web interface reuse the same handlers (D8). The one thing a
handler may ask for is a confirmation, and it asks for it here rather than
reading the keyboard itself, for exactly the same reason.

`rich` is optional by D21: when it is unavailable the same calls fall back to
plain printing, so a missing package costs appearance, never function.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from personal_assistant.types import Renderable

if TYPE_CHECKING:
    from rich.table import Table

try:
    from rich import box
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    _console: Console | None = Console()
except ImportError:  # pragma: no cover - exercised only without rich
    _console = None

QUESTION_SUFFIX = "[y/N]"
AGREEMENT = ("y", "yes")


@dataclass(frozen=True)
class Column:
    """How one column of a table is presented.

    A handler describes its columns instead of formatting them itself, so
    every table in the assistant is built the same way and the decisions that
    depend on the terminal stay in this module.
    """

    header: str
    style: str = ""
    width: int | None = None
    wrap: bool = True


def render(result: Renderable) -> None:
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


def table(
    title: str,
    columns: Sequence[Column | str],
    rows: Sequence[Sequence[object]],
) -> Renderable:
    """Build a table for a handler to return, or plain text without rich."""
    described = [
        column if isinstance(column, Column) else Column(column) for column in columns
    ]
    if _console is None:
        return _plain(title, [column.header for column in described], rows)

    built = Table(
        title=title,
        box=box.ROUNDED,
        title_justify="left",
        title_style="bold",
        header_style="bold",
    )
    for column in described:
        built.add_column(
            column.header,
            style=column.style or None,
            width=column.width,
            no_wrap=not column.wrap,
            overflow="fold" if column.wrap else "ellipsis",
        )
    for row in rows:
        built.add_row(*[str(cell) for cell in row])
    return built


def details(title: str, fields: Sequence[tuple[str, object]]) -> Renderable:
    """Show one record field by field, for the `show` commands.

    A single record has a handful of long values rather than many short ones,
    so it reads better down the page than across a table, and the frame around
    it would carry no information.
    """
    if _console is None:
        return "\n".join([title, *(f"{name}: {value}" for name, value in fields)])

    built = Table(
        title=title,
        box=None,
        show_header=False,
        title_justify="left",
        title_style="bold",
        pad_edge=False,
    )
    built.add_column(style="bold cyan", no_wrap=True)
    built.add_column(overflow="fold")
    for name, value in fields:
        built.add_row(name, str(value))
    return built


def confirm(question: str) -> bool:
    """Ask before something irreversible happens, as section 7.1 requires.

    The default is no: an empty answer, an unreadable input or an interrupted
    one all leave the data alone, so nothing is destroyed by a stray Enter
    and a command that cannot ask never fails on it either.
    """
    try:
        answer = input(f"{question} {QUESTION_SUFFIX} ")
    except (EOFError, KeyboardInterrupt, OSError):
        return False
    return answer.strip().lower() in AGREEMENT


def _plain(title: str, headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """The same table as text, for a terminal without rich."""
    header = " | ".join(headers)
    body = "\n".join(" | ".join(str(cell) for cell in row) for row in rows)
    return f"{title}\n{header}\n{body}" if rows else f"{title}\n{header}"
