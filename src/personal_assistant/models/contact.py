"""A single entry of the address book."""

from __future__ import annotations

from collections.abc import Iterable

from personal_assistant.errors import ValidationError
from personal_assistant.models.address import Address
from personal_assistant.models.birthday import Birthday
from personal_assistant.models.email import Email
from personal_assistant.models.name import Name
from personal_assistant.models.phone import Phone


class Contact:
    """One contact, composed of validated fields.

    The contact holds several phone numbers and at most one email, address and
    birthday, as decided in D15. It never validates anything itself: each field
    class does that when it is constructed, so a contact can only ever be built
    from valid values.
    """

    def __init__(self, name: str) -> None:
        self.name = Name(name)
        self.phones: list[Phone] = []
        self.email: Email | None = None
        self.address: Address | None = None
        self.birthday: Birthday | None = None

    def add_phone(self, raw: str) -> Phone:
        """Add a phone number, refusing one the contact already holds."""
        phone = Phone(raw)
        if phone in self.phones:
            raise ValidationError(f"{self.name} already has the number {phone}.")
        self.phones.append(phone)
        return phone

    def find_phone(self, raw: str) -> Phone | None:
        """Return the stored number equal to `raw`, whatever its spelling."""
        wanted = Phone(raw)
        for phone in self.phones:
            if phone == wanted:
                return phone
        return None

    def remove_phone(self, raw: str) -> None:
        """Remove a number, reporting one the contact does not hold."""
        phone = self.find_phone(raw)
        if phone is None:
            raise ValidationError(f"{self.name} has no number {raw}.")
        self.phones.remove(phone)

    def set_phones(self, numbers: Iterable[str]) -> None:
        """Replace every phone number with a freshly validated list.

        `add_phone`/`remove_phone` are what the CLI's paired `--add-phone` and
        `--remove-phone` options use (D19); this is the same operation for a
        caller that already knows the full list it wants, such as a single web
        form field. Every value is validated before anything is written, so an
        invalid or repeated number leaves the contact's phones untouched.
        """
        parsed: list[Phone] = []
        for raw in numbers:
            phone = Phone(raw)
            if phone in parsed:
                raise ValidationError(f"'{phone}' was given more than once.")
            parsed.append(phone)
        self.phones = parsed

    def rename(self, raw: str) -> None:
        self.name = Name(raw)

    def matches(self, query: str) -> bool:
        """Whether `query` is a substring of the name, a phone, the email or
        the address, ignoring case, as required by C2."""
        query = query.casefold()
        haystacks = [str(self.name), str(self.email or ""), str(self.address or "")]
        haystacks.extend(str(phone) for phone in self.phones)
        return any(query in haystack.casefold() for haystack in haystacks)

    def set_email(self, raw: str | None) -> None:
        """Set the email, or clear it when given nothing."""
        self.email = Email(raw) if raw else None

    def set_address(self, raw: str | None) -> None:
        """Set the address, or clear it when given nothing."""
        self.address = Address(raw) if raw else None

    def set_birthday(self, raw: str | None) -> None:
        """Set the birthday, or clear it when given nothing."""
        self.birthday = Birthday(raw) if raw else None

    def __str__(self) -> str:
        parts = [f"{self.name}"]
        if self.phones:
            parts.append("phones: " + ", ".join(str(phone) for phone in self.phones))
        if self.email is not None:
            parts.append(f"email: {self.email}")
        if self.address is not None:
            parts.append(f"address: {self.address}")
        if self.birthday is not None:
            parts.append(f"birthday: {self.birthday}")
        return "; ".join(parts)

    def __repr__(self) -> str:
        return f"Contact({self.name.value!r})"
