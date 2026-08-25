"""The collection of contacts."""

from __future__ import annotations

from collections import UserDict

from personal_assistant.models.contact import Contact


class AddressBook(UserDict[str, Contact]):
    """Contacts kept by name.

    Names are matched without regard to case, so `john` finds `John`, while the
    spelling the user chose is what gets stored and displayed.
    """

    def add(self, contact: Contact) -> None:
        self.data[contact.name.value] = contact

    def find(self, name: str) -> Contact | None:
        """Return the contact with this name, or None."""
        exact = self.data.get(name)
        if exact is not None:
            return exact

        wanted = name.casefold()
        for stored, contact in self.data.items():
            if stored.casefold() == wanted:
                return contact
        return None

    def delete(self, name: str) -> bool:
        """Remove a contact. Returns whether one was there."""
        contact = self.find(name)
        if contact is None:
            return False
        del self.data[contact.name.value]
        return True
