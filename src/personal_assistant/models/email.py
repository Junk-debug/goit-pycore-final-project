"""The email address of a contact."""

from __future__ import annotations

import re

from personal_assistant.errors import ValidationError
from personal_assistant.models.field import Field

PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$"
)


class Email(Field[str]):
    """An email address of the form `name@domain.tld`."""

    def parse(self, raw: str) -> str:
        if not PATTERN.match(raw):
            raise ValidationError(f"'{raw}' is not a valid email address.")
        return raw
