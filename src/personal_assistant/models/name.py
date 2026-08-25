"""The name of a contact."""

from __future__ import annotations

from personal_assistant.errors import ValidationError
from personal_assistant.models.field import Field

MAX_LENGTH = 64


class Name(Field[str]):
    """A non-empty name, used as the key of a contact in the address book."""

    def parse(self, raw: str) -> str:
        if not raw:
            raise ValidationError("A name cannot be empty.")
        if len(raw) > MAX_LENGTH:
            raise ValidationError(f"A name cannot exceed {MAX_LENGTH} characters.")
        return raw
