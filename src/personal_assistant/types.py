"""Types shared by the interface layer.

Keeping them in one place stops the command modules from re-inventing the same
aliases and gives the type checker something precise to hold on to.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Protocol, TypeAlias

if TYPE_CHECKING:
    from rich.table import Table

    from personal_assistant.parser import ReplArgumentParser
    from personal_assistant.state import AppState

# What a handler may hand back for display: a line of text, a table built by
# `ui.table`, or nothing at all.
Renderable: TypeAlias = "str | Table | None"

# The sub-parser collection a command group registers itself into.
SubParsers: TypeAlias = "argparse._SubParsersAction[ReplArgumentParser]"


class Handler(Protocol):
    """What every command handler looks like.

    Handlers receive the parsed arguments and the application state, and return
    what should be shown. They never print: `ui` decides how a value reaches the
    terminal, which is what will let the web interface reuse them unchanged.
    """

    def __call__(self, args: argparse.Namespace, state: AppState) -> Renderable: ...
