"""The tag of a note: a keyword describing what the note is about (T1)."""

from __future__ import annotations

from personal_assistant.errors import ValidationError
from personal_assistant.models.field import Field

MAX_LENGTH = 32


class Tag(Field[str]):
    """A single keyword attached to a note.

    A tag is normalised to lower case, so `Python` and `python` name the same
    subject. Without that, searching and sorting by tag would split one subject
    into several and quietly return half of the notes (T2, T3).
    """

    def parse(self, raw: str) -> str:
        """Validate the keyword and return it in its normalised form (D20)."""
        if not raw:
            raise ValidationError("A tag cannot be empty.")
        if any(character.isspace() for character in raw):
            raise ValidationError(
                f"A tag is a single keyword and cannot contain spaces: '{raw}'."
            )
        if len(raw) > MAX_LENGTH:
            raise ValidationError(
                f"A tag is at most {MAX_LENGTH} characters long: '{raw}'."
            )
        return raw.lower()

    def __lt__(self, other: object) -> bool:
        """Order tags alphabetically, which is what sorting by tag means (T3)."""
        if isinstance(other, Tag):
            return self.value < other.value
        return NotImplemented
