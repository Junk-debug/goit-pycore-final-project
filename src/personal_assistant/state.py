"""The in-memory state of the application.

`AppState` is the single object that is persisted and handed to every command
handler. It deliberately knows nothing about what any command group stores: a
group asks for its own section by naming the class that holds it, and the state
creates one on first use.

That keeps the dependency pointing one way. A new command group brings its own
collection and never edits this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar

Section = TypeVar("Section")


@dataclass
class AppState:
    """Everything the assistant remembers between runs."""

    sections: dict[str, object] = field(default_factory=dict)

    def section(self, kind: type[Section]) -> Section:
        """Return the section held by `kind`, creating it on first use.

        Creating on demand is also what makes an older file keep working: a
        state saved before a group existed simply has no entry for it, and the
        first command of that group makes one.
        """
        key = f"{kind.__module__}.{kind.__qualname__}"
        stored = self.sections.get(key)
        if isinstance(stored, kind):
            return stored

        created = kind()
        self.sections[key] = created
        return created

    def ensure_ready(self) -> None:
        """Make a state restored from an older layout usable."""
        if getattr(self, "sections", None) is None:
            self.sections = {}

    @classmethod
    def empty(cls) -> AppState:
        """A state that holds nothing yet."""
        return cls()
