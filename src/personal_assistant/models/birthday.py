"""The birthday of a contact."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from personal_assistant.errors import ValidationError
from personal_assistant.models.field import Field

FORMAT = "%d.%m.%Y"
EARLIEST_YEAR = 1900
SATURDAY = 5


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

    def next_greeting(self, today: date) -> date:
        """The next date this birthday is celebrated, on or after `today`.

        A 29 February without a matching leap year is celebrated on 1 March
        instead, and a date that lands on a Saturday or Sunday is moved to the
        following Monday, per C5.
        """
        occurrence = self._next_occurrence(today)
        if occurrence.weekday() >= SATURDAY:
            occurrence += timedelta(days=7 - occurrence.weekday())
        return occurrence

    def _next_occurrence(self, today: date) -> date:
        occurrence = self._for_year(today.year)
        if occurrence < today:
            occurrence = self._for_year(today.year + 1)
        return occurrence

    def _for_year(self, year: int) -> date:
        try:
            return self.value.replace(year=year)
        except ValueError:
            return date(year, 3, 1)

    def __str__(self) -> str:
        return self.value.strftime(FORMAT)
