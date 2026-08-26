"""The collection of contacts, and the state section the contact commands own.

Every question an interface asks about the book as a whole — is this name
taken, which contacts match a search, in what order should they be shown — is
answered here, mirroring `NoteBook`. Both adapters therefore share the same
answers instead of each working them out again.
"""

from __future__ import annotations

from collections import UserDict
from datetime import date
from enum import Enum

from personal_assistant.errors import ValidationError
from personal_assistant.models.contact import Contact


class SortKey(str, Enum):
    """The two ways `contact list` can order its results."""

    NAME = "name"
    BIRTHDAY = "birthday"


SORT_KEYS = tuple(key.value for key in SortKey)


class AddressBook(UserDict[str, Contact]):
    """Contacts kept by name.

    Names are matched without regard to case, so `john` finds `John`, while the
    spelling the user chose is what gets stored and displayed.
    """

    def add(self, contact: Contact) -> None:
        """Store a new contact, refusing a name the book already holds."""
        if self.find(contact.name.value) is not None:
            raise ValidationError(f"A contact named '{contact.name}' already exists.")
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

    def rename(self, contact: Contact, new_name: str) -> None:
        """Give a stored contact a new name, keeping the book keyed by it."""
        taken = self.find(new_name)
        if taken is not None and taken is not contact:
            raise ValidationError(f"A contact named '{new_name}' already exists.")

        del self.data[contact.name.value]
        contact.rename(new_name)
        self.data[contact.name.value] = contact

    def delete(self, name: str) -> bool:
        """Remove a contact. Returns whether one was there."""
        contact = self.find(name)
        if contact is None:
            return False
        del self.data[contact.name.value]
        return True

    def select(
        self,
        *,
        query: str | None = None,
        birthday_in: int | None = None,
        sort: str | None = None,
        today: date | None = None,
    ) -> list[Contact]:
        """The contacts a `contact list` invocation asks for.

        Every criterion narrows the previous result, so the options combine
        instead of competing: a search and a birthday window may be
        given together. Ascending order throughout; a contact with no
        birthday sorts last under `--sort birthday`, since there is nothing to
        order it by.
        """
        if birthday_in is not None and birthday_in < 0:
            raise ValidationError("--birthday-in must not be negative.")

        today = today or date.today()
        chosen = list(self.data.values())
        if query:
            chosen = [contact for contact in chosen if contact.matches(query)]
        if birthday_in is not None:
            chosen = [
                contact
                for contact in chosen
                if contact.birthday is not None
                and _days_until(contact, today) <= birthday_in
            ]

        if sort == SortKey.NAME:
            chosen.sort(key=lambda contact: str(contact.name).casefold())
        elif sort == SortKey.BIRTHDAY:
            chosen.sort(key=lambda contact: _birthday_sort_key(contact, today))
        elif sort is not None:
            raise ValidationError(
                f"Contacts cannot be sorted by '{sort}'. "
                f"Sort by {', '.join(SORT_KEYS)} instead."
            )
        return chosen


def _days_until(contact: Contact, today: date) -> int:
    """Days from `today` until `contact`'s next birthday greeting.

    Only meaningful once the caller has checked the contact has a birthday.
    """
    assert contact.birthday is not None
    return (contact.birthday.next_greeting(today) - today).days


def _birthday_sort_key(contact: Contact, today: date) -> date:
    """A birthday-less contact sorts after every contact with one."""
    if contact.birthday is None:
        return date.max
    return contact.birthday.next_greeting(today)
