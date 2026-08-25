"""The birthday of a contact."""

from __future__ import annotations

from datetime import date, datetime

from personal_assistant.errors import ValidationError
from personal_assistant.models.field import Field

FORMAT = "%d.%m.%Y"
EARLIEST_YEAR = 1900


class Birthday(Field[date]):
    """A date of birth, entered and displayed as `DD.MM.YYYY`."""

    def parse(self, raw: str) -> date:
        try:
            parsed = datetime.strptime(raw, FORMAT).date()
        except ValueError:
            raise ValidationError(
                f"'{raw}' is not a valid date. Expected the format DD.MM.YYYY."
            ) from None

        if parsed > date.today():
            raise ValidationError("A birthday cannot be in the future.")
        if parsed.year < EARLIEST_YEAR:
            raise ValidationError(f"A birthday cannot be before {EARLIEST_YEAR}.")
        return parsed

    def __str__(self) -> str:
        return self.value.strftime(FORMAT)
