"""The collection of contacts."""

from __future__ import annotations

from collections import UserDict

from personal_assistant.models.record import Record


class AddressBook(UserDict[str, Record]):
    """Contacts kept by name.

    Names are matched without regard to case, so `john` finds `John`, while the
    spelling the user chose is what gets stored and displayed.
    """

    def add_record(self, record: Record) -> None:
        self.data[record.name.value] = record

    def find(self, name: str) -> Record | None:
        """Return the contact with this name, or None."""
        exact = self.data.get(name)
        if exact is not None:
            return exact

        wanted = name.casefold()
        for stored, record in self.data.items():
            if stored.casefold() == wanted:
                return record
        return None

    def delete(self, name: str) -> bool:
        """Remove a contact. Returns whether one was there."""
        record = self.find(name)
        if record is None:
            return False
        del self.data[record.name.value]
        return True
