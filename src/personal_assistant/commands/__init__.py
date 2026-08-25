"""Assembly of the command tree.

Every group lives in its own module and exposes a single function:

    def register(app: typer.Typer) -> None

It attaches its own sub-application there. A group therefore never edits a
shared file, which keeps the developers of different groups out of each
other's way.

A command receives the application state through `ctx.obj` and prints what it
has to say through `personal_assistant.ui`, the only module that writes to the
terminal.
"""

from __future__ import annotations

import importlib
from types import ModuleType

import typer

GROUP_MODULES = ("common", "contacts", "notes")

HELP = "Personal assistant: an address book and notes."
EPILOG = "Run without arguments to start the interactive session."


def _load(name: str) -> ModuleType | None:
    """Import a group module, or return None while it does not exist yet."""
    try:
        return importlib.import_module(f"personal_assistant.commands.{name}")
    except ImportError:
        return None


def build_app() -> typer.Typer:
    """Build the application shared by the loop and the single-command mode."""
    app = typer.Typer(
        help=HELP,
        epilog=EPILOG,
        add_completion=False,
        no_args_is_help=True,
        pretty_exceptions_enable=False,
    )
    for name in GROUP_MODULES:
        module = _load(name)
        if module is not None:
            module.register(app)
    return app
