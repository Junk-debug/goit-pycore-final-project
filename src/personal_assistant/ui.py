"""Presentation layer.

The only module that writes to the terminal. Commands decide what to say, this
module decides how it looks, which keeps formatting out of the domain and out
of the command bodies.

Everything is drawn by `rich`, which arrives as a hard dependency of `typer`.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from personal_assistant.types import Renderable

_console = Console()


def render(result: Renderable) -> None:
    """Print a line of text or a table.

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
    title: str, columns: Sequence[str], rows: Sequence[Sequence[object]]
) -> Table:
    """Build a table for a command to hand to `render`."""
    built = Table(
        title=title, box=box.ROUNDED, header_style="bold cyan", title_style="bold"
    )
    for index, column in enumerate(columns):
        # The first column holds the label of each row (a field name, a
        # contact's name); bolding it reads as a key, not as emphasis on some
        # rows over others the way alternating row colours would.
        built.add_column(column, style="bold" if index == 0 else None)
    for row in rows:
        built.add_row(*[str(cell) for cell in row])
    return built


def confirm(question: str) -> bool:
    """Ask the user to confirm a destructive action.

    Answers no whenever an answer cannot be read: input that is not a terminal
    (a piped or scripted run has nobody to say yes), and Ctrl-D or Ctrl-C at the
    prompt itself. A destructive action must never go ahead by default; `--force`
    is the way to mean it.
    """
    if not sys.stdin.isatty():
        return False

    prompt = Text(question)
    prompt.append(" [y/N] ", style="bold yellow")
    try:
        # A Text object, not an f-string: `question` may hold arbitrary data,
        # such as a contact name, and Console.input parses markup in a plain
        # string by default — the same trap render() guards against.
        answer = _console.input(prompt)
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip().lower() in {"y", "yes"}


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
        grid.add_row(label, value if value else "—")
    return Panel(grid, title=title, title_align="left", expand=False)
