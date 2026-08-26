"""The tag of a note: a keyword describing what the note is about."""

from __future__ import annotations

from personal_assistant.errors import ValidationError
from personal_assistant.models.field import Field

MAX_LENGTH = 32


class Tag(Field[str]):
    """A single keyword attached to a note.

    A tag is normalised to lower case, so `Python` and `python` name the same
    subject. Without that, searching and sorting by tag would split one subject
    into several and quietly return half of the notes.
    """

    def parse(self, raw: str) -> str:
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
        """Order tags alphabetically, which is what sorting by tag means."""
        if isinstance(other, Tag):
            return self.value < other.value
        return NotImplemented
