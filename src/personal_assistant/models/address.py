"""The postal address of a contact."""

from __future__ import annotations

from personal_assistant.errors import ValidationError
from personal_assistant.models.field import Field

MAX_LENGTH = 128


class Address(Field[str]):
    """A free-form postal address."""

    def parse(self, raw: str) -> str:
        if not raw:
            raise ValidationError("An address cannot be empty.")
        if len(raw) > MAX_LENGTH:
            raise ValidationError(f"An address cannot exceed {MAX_LENGTH} characters.")
        return raw
