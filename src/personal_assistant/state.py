"""The in-memory state of the application.

`AppState` is the single object that is persisted and passed to every command
handler. Each command group owns one section of it: contacts belong to the
`contact` group, notes to the `note` group.

The collection classes are imported lazily so that the core runs before the
group modules exist. A missing section stays `None`, and the group that owns
it is simply not registered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from personal_assistant.models.address_book import AddressBook
    from personal_assistant.models.note_book import NoteBook


def _build(module_name: str, class_name: str) -> Any | None:
    """Instantiate a collection class, or return None if it does not exist yet."""
    try:
        module = __import__(
            f"personal_assistant.models.{module_name}", fromlist=[class_name]
        )
    except ImportError:
        return None
    return getattr(module, class_name)()


@dataclass
class AppState:
    """Everything the assistant remembers between runs."""

    contacts: AddressBook | None = None
    notes: NoteBook | None = None

    @classmethod
    def empty(cls) -> AppState:
        """Build a state with an empty section for every available group."""
        return cls(
            contacts=_build("address_book", "AddressBook"),
            notes=_build("note_book", "NoteBook"),
        )
