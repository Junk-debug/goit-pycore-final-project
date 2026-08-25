"""Types shared by the interface layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from rich.table import Table

# What a command may hand to `ui.render`: a line of text, a table built by
# `ui.table`, or nothing at all.
Renderable: TypeAlias = "str | Table | None"
