"""Presentation layer.

The only module that writes to the terminal. Commands decide what to say,
this module decides how it looks, which keeps formatting out of the domain
and out of the command bodies.

Everything is drawn by `rich`, which arrives as a hard dependency of `typer`.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from personal_assistant.types import Renderable

MIN_WIDTH = 100


def _ensure_a_sane_width() -> None:
    """Give a floor to the width rendering is measured against.

    A real terminal is left alone: interactive use should wrap to whatever the
    user's window actually is. Without one — piped output, a redirect, a CI
    runner, this test suite — `rich` and `typer` fall back to `COLUMNS`, and
    some environments report it too narrow to hold even a single flag's own
    name, wrapping `--phone` across lines and making it vanish from a plain
    substring search. The floor is enforced, not just filled in when absent,
    because the narrow value seen in CI could equally be an explicit `COLUMNS`
    as an absent one falling back to something small; either way, nothing
    without a real terminal should render narrower than this.
    """
    if sys.stdout.isatty():
        return
    ambient = os.environ.get("COLUMNS", "")
    if not (ambient.isdigit() and int(ambient) >= MIN_WIDTH):
        os.environ["COLUMNS"] = str(MIN_WIDTH)


_ensure_a_sane_width()
_console = Console()

DASH = "—"


@dataclass(frozen=True)
class Column:
    """How one column of a table is presented.

    A command describes its columns instead of formatting them itself, so
    every table in the assistant is built the same way and the decisions that
    depend on the terminal stay in this module.
    """

    header: str
    style: str = ""
    width: int | None = None
    wrap: bool = True


def render(result: Renderable) -> None:
    """Print a line of text, a table, or a card.

    A plain string is printed verbatim, because `rich` would otherwise read
    square brackets as its own markup and colour arbitrary words on its own,
    which mangles pre-formatted text such as the output of `--help`.
    """
    if result is None:
        return
    if isinstance(result, str):
        _console.print(result, markup=False, highlight=False)
    else:
        _console.print(result)


def success(message: str) -> None:
    """Report a completed action."""
    _console.print(Text(message, style="green"))


def failure(message: str) -> None:
    """Report an expected error, such as invalid input."""
    _console.print(Text(message, style="red"))


def table(
    title: str,
    columns: Sequence[Column | str],
    rows: Sequence[Sequence[object]],
) -> Table:
    """Build a table for a command to hand to `render`.

    A bare string stands for a column with no particular style, which keeps a
    simple listing simple to write; `Column` is there for one that needs a
    style, a fixed width or control over wrapping, as `note list` does.
    """
    described = [
        column if isinstance(column, Column) else Column(column) for column in columns
    ]
    built = Table(
        title=title,
        box=box.ROUNDED,
        title_justify="left",
        title_style="bold",
        header_style="bold cyan",
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


def card(title: str, fields: Sequence[tuple[str, str | None]]) -> Panel:
    """Build a labelled panel for a single record, such as one contact.

    A record is a handful of "label: value" pairs, not a set of rows to
    compare against each other, so it is framed once with its own name in the
    border rather than drawn as a table with a repeated title and column
    headers. A field that is not set is shown as a dash.

    Built on a borderless `Table.grid` rather than plain lines of text: a long
    value that wraps then continues under the value column instead of running
    back under the label, which a hand-built line of text cannot do on its own.
    """
    grid = Table.grid(padding=(0, 2, 0, 0))
    grid.add_column(style="bold cyan", no_wrap=True)
    grid.add_column()
    for label, value in fields:
        grid.add_row(label, value if value else DASH)
    return Panel(grid, title=title, title_align="left", expand=False)


def confirm(question: str) -> bool:
    """Ask the user to confirm a destructive action (section 7.1).

    Answers no whenever an answer cannot be read: input that is not a
    terminal (a piped or scripted run has nobody to say yes), and Ctrl-D or
    Ctrl-C at the prompt itself. A destructive action must never go ahead by
    default; `--force` is the way to mean it.
    """
    if not sys.stdin.isatty():
        return False

    prompt = Text(question)
    prompt.append(" [y/N] ", style="bold yellow")
    try:
        # A Text object, not an f-string: `question` may hold arbitrary data,
        # such as a note's preview, and Console.input parses markup in a plain
        # string by default — the same trap render() guards against.
        answer = _console.input(prompt)
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip().lower() in {"y", "yes"}
