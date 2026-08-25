"""Types shared by the interface layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from rich.panel import Panel
    from rich.table import Table

# What a command may hand to `ui.render`: a line of text, something built by
# `ui.table` or `ui.card`, or nothing at all.
Renderable: TypeAlias = "str | Table | Panel | None"
