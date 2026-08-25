"""The collection of notes, and the state section the note commands own.

The notebook is a mapping from the numeric id of a note to the note itself
(D16). Inheriting from `UserDict` gives it everything a mapping already knows —
iteration, `len`, membership — so this class only adds what a notebook does on
top of a dictionary: it hands out ids, and it answers the questions the `note
list` command asks (N2, T2, T3).
"""

from __future__ import annotations

from collections import UserDict
from collections.abc import Iterable

from personal_assistant.errors import NotFoundError, ValidationError
from personal_assistant.models.note import Note
from personal_assistant.models.tag import Tag

SORT_KEYS = ("tag", "created", "updated")


class NoteBook(UserDict[int, Note]):
    """Every note the assistant remembers, addressed by its id."""

    def __init__(self) -> None:
        super().__init__()
        self._last_id = 0

    def __missing__(self, note_id: int) -> Note:
        """Turn a missing id into the message the user is meant to see.

        `UserDict` calls this instead of raising `KeyError`, so every way of
        reaching a note — including `book[3]` — reports the same thing, and no
        command has to check first and then fetch.
        """
        raise NotFoundError(f"There is no note with id {note_id}.")

    def add(self, text: str, tags: Iterable[str] = ()) -> Note:
        """Write a new note and return it, with the id it received (N1, T1)."""
        note = Note(self._next_id(), text, tags)
        self._last_id = note.id
        self.data[note.id] = note
        return note

    def remove(self, note_id: int) -> Note:
        """Delete a note and return it, or report that there is none (N4)."""
        note = self[note_id]
        del self.data[note_id]
        return note

    def select(
        self,
        *,
        query: str | None = None,
        tag: str | None = None,
        sort: str | None = None,
    ) -> list[Note]:
        """The notes a `note list` invocation asks for.

        Every criterion narrows the previous result, so the options combine
        instead of competing (D17). Ordering is ascending throughout: notes
        without a tag come last, because there is nothing to order them by.
        """
        chosen = list(self.data.values())
        if query:
            chosen = [note for note in chosen if note.matches(query)]
        if tag:
            wanted = Tag(tag)
            chosen = [note for note in chosen if wanted in note.tags]

        if sort is None:
            return sorted(chosen, key=lambda note: note.id)
        if sort == "tag":
            return sorted(chosen, key=_by_tag)
        if sort == "created":
            return sorted(chosen, key=lambda note: (note.created, note.id))
        if sort == "updated":
            return sorted(chosen, key=lambda note: (note.updated, note.id))
        raise ValidationError(
            f"Notes cannot be sorted by '{sort}'. "
            f"Sort by {', '.join(SORT_KEYS)} instead."
        )

    def tags(self) -> list[str]:
        """Every tag currently in use, alphabetically and without repetition."""
        return sorted({tag.value for note in self.data.values() for tag in note.tags})

    def _next_id(self) -> int:
        """One past the largest id ever handed out, so ids are never reused.

        Counting from the notes alone would give the id of a deleted note to
        the next one written, and every command that names an id would then
        point at a different note than the user remembers (D16).
        """
        return max([self._last_id, *self.data]) + 1


def _by_tag(note: Note) -> tuple[bool, str, int]:
    """Order by the first tag, keeping untagged notes at the end (T3)."""
    first = note.first_tag()
    return (first is None, first or "", note.id)
