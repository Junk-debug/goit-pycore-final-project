"""A phone number of a contact."""

from __future__ import annotations

import re

from personal_assistant.errors import ValidationError
from personal_assistant.models.field import Field

SEPARATORS = re.compile(r"[\s()\-.]")
PATTERN = re.compile(r"^\+?\d{9,15}$")


class Phone(Field[str]):
    """A phone number, stored without the separators it was typed with.

    Spaces, dashes, dots and brackets are removed before validation, so
    `+48 123-456-789` and `+48123456789` are the same number.
    """

    def parse(self, raw: str) -> str:
        compact = SEPARATORS.sub("", raw)
        if not PATTERN.match(compact):
            raise ValidationError(
                f"'{raw}' is not a valid phone number. "
                "Expected 9 to 15 digits, optionally starting with '+'."
            )
        return compact
