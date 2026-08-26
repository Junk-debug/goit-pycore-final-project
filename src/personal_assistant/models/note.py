"""The note itself: text and the tags describing it, nothing else (D18)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from personal_assistant.errors import NotFoundError, ValidationError
from personal_assistant.models.field import Field
from personal_assistant.models.tag import Tag

MAX_LENGTH = 4096
PREVIEW_LENGTH = 60
ELLIPSIS = "..."
TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M"


class NoteText(Field[str]):
    """The textual content of a note."""

    def parse(self, raw: str) -> str:
        """Validate the text of a note (D20)."""
        if not raw:
            raise ValidationError("A note cannot be empty.")
        if len(raw) > MAX_LENGTH:
            raise ValidationError(
                f"A note is at most {MAX_LENGTH} characters long, "
                f"and this one is {len(raw)}."
            )
        return raw


class Note:
    """One note: an id, its text, its tags and its timestamps.

    The note is composed of validated fields rather than of plain strings, so
    an existing note is always valid: there is no way to build one around text
    or a tag that was never checked.

    The id is assigned by the notebook and never changes, which keeps the
    commands addressing a note working while its text is edited (D16).
    """

    def __init__(self, note_id: int, text: str, tags: Iterable[str] = ()) -> None:
        self.id = note_id
        self.text = NoteText(text)
        self.tags = {Tag(tag) for tag in tags}
        self.created = datetime.now()
        self.updated = self.created

    def edit(
        self,
        *,
        text: str | None = None,
        add: Iterable[str] = (),
        remove: Iterable[str] = (),
    ) -> None:
        """Apply the changes of one `note edit` invocation (N3, T1).

        Every value is validated before anything is written, so a rejected tag
        cannot leave the note half-edited. Adding and removing in the same call
        therefore replaces a tag atomically, which is what D19 promises.
        """
        replacement = NoteText(text) if text is not None else None
        added = {Tag(tag) for tag in add}
        removed = {Tag(tag) for tag in remove}

        missing = sorted(tag.value for tag in removed - self.tags)
        if missing:
            raise NotFoundError(f"Note {self.id} is not tagged {', '.join(missing)}.")

        if replacement is not None:
            self.text = replacement
        self.tags = (self.tags - removed) | added
        self.touch()

    def set_tags(self, tags: Iterable[str]) -> None:
        """Replace every tag with a freshly validated set (T1).

        `edit(add=..., remove=...)` is what the CLI's paired options use
        (D19); this is the same operation for a caller that already knows the
        full set it wants, such as a single web form field. A set silently
        collapses a repeated tag, which matches how `add` already behaves.
        """
        self.tags = {Tag(tag) for tag in tags}
        self.touch()

    def touch(self) -> None:
        """Record that the note has just been changed."""
        self.updated = datetime.now()

    def has_tag(self, tag: str) -> bool:
        """Whether the note carries that tag, however it was capitalised (T2)."""
        return Tag(tag) in self.tags

    def matches(self, query: str) -> bool:
        """Whether the text contains the query, ignoring case (N2)."""
        return query.strip().lower() in self.text.value.lower()

    def tag_names(self) -> list[str]:
        """The tags in alphabetical order, as plain strings."""
        return [tag.value for tag in sorted(self.tags)]

    def first_tag(self) -> str | None:
        """The alphabetically first tag, or None when the note has none.

        This is what `note list --sort tag` orders by (T3): a note carries
        several tags, so one of them has to speak for it.
        """
        names = self.tag_names()
        return names[0] if names else None

    def preview(self, width: int = PREVIEW_LENGTH) -> str:
        """The opening of the text on a single line, for a listing (D18)."""
        single_line = " ".join(self.text.value.split())
        if len(single_line) <= width:
            return single_line
        return single_line[: width - len(ELLIPSIS)].rstrip() + ELLIPSIS

    def stamp(self, moment: datetime) -> str:
        """One of the note's timestamps, in the format the interface uses."""
        return moment.strftime(TIMESTAMP_FORMAT)

    def __str__(self) -> str:
        tags = f" [{', '.join(self.tag_names())}]" if self.tags else ""
        return f"{self.id}: {self.preview()}{tags}"

    def __repr__(self) -> str:
        return f"Note(id={self.id}, tags={self.tag_names()})"
