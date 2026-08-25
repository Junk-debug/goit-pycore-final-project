"""The `note` command group: notes, their tags and what you do to them.

Covers N1 to N4 and the optional tag scope T1 to T3. The group registers its
own actions and keeps the notes in its own section of the application state,
so adding a command here never touches a file another group owns (D12).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from personal_assistant import ui
from personal_assistant.errors import CommandError
from personal_assistant.models.note import Note
from personal_assistant.models.note_book import SORT_KEYS, NoteBook
from personal_assistant.parser import ReplArgumentParser
from personal_assistant.state import AppState
from personal_assistant.types import Handler, Renderable, SubParsers

TITLE = "Notes"
NO_TAGS = "-"
COLUMNS = (
    ui.Column("Id", style="cyan", wrap=False),
    ui.Column("Note"),
    ui.Column("Tags", style="magenta", wrap=False),
    ui.Column("Updated", wrap=False),
)


def register(groups: SubParsers) -> None:
    """Add the note commands to the command tree."""
    note = groups.add_parser(
        "note",
        help="notes and the tags describing them",
        description="Write, find and edit notes. A note is its text and its tags.",
    )
    note.set_defaults(handler=_help_of(note))
    actions = note.add_subparsers(
        dest="action", metavar="<action>", parser_class=ReplArgumentParser
    )

    add = actions.add_parser(
        "add",
        help="write a new note",
        description="Write a note and report the id it received.",
    )
    add.add_argument(
        "text", metavar="<text>", help="the text of the note; quote it if it has spaces"
    )
    add.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        metavar="<tag>",
        help="a keyword describing the note; may be repeated",
    )
    add.set_defaults(handler=add_note)

    show = actions.add_parser(
        "show",
        help="print one note in full",
        description="Print one note with its tags and its timestamps.",
    )
    show.add_argument(
        "note_id", type=int, metavar="<id>", help="the id shown by 'note list'"
    )
    show.set_defaults(handler=show_note)

    listing = actions.add_parser(
        "list",
        help="list notes, narrowed by the options",
        description="List notes as a table. Options narrow the result and combine.",
    )
    listing.add_argument(
        "--query", metavar="<text>", help="keep the notes whose text contains this"
    )
    listing.add_argument(
        "--tag", metavar="<tag>", help="keep the notes carrying this tag"
    )
    listing.add_argument(
        "--sort",
        choices=SORT_KEYS,
        metavar="|".join(SORT_KEYS),
        help="order by first tag, or by the time written or last changed",
    )
    listing.set_defaults(handler=list_notes)

    edit = actions.add_parser(
        "edit",
        help="change the text or the tags of a note",
        description="Change a note. Adding and removing a tag at once replaces it.",
    )
    edit.add_argument("note_id", type=int, metavar="<id>", help="the id of the note")
    edit.add_argument("--text", metavar="<text>", help="replace the text of the note")
    edit.add_argument(
        "--add-tag",
        action="append",
        default=[],
        metavar="<tag>",
        help="attach a tag; may be repeated",
    )
    edit.add_argument(
        "--remove-tag",
        action="append",
        default=[],
        metavar="<tag>",
        help="detach a tag; may be repeated",
    )
    edit.set_defaults(handler=edit_note)

    delete = actions.add_parser(
        "delete",
        help="remove a note",
        description="Remove a note. You are asked first unless --force is given.",
    )
    delete.add_argument("note_id", type=int, metavar="<id>", help="the id of the note")
    delete.add_argument(
        "--force", action="store_true", help="delete without asking first"
    )
    delete.set_defaults(handler=delete_note)


@dataclass(frozen=True)
class AddArguments:
    """What `note add` accepts."""

    text: str
    tags: tuple[str, ...]

    @classmethod
    def read(cls, args: argparse.Namespace) -> AddArguments:
        return cls(text=args.text, tags=tuple(args.tags))


@dataclass(frozen=True)
class IdArgument:
    """The single id that `note show` and `note delete` act upon."""

    note_id: int
    force: bool = False

    @classmethod
    def read(cls, args: argparse.Namespace) -> IdArgument:
        return cls(note_id=args.note_id, force=getattr(args, "force", False))


@dataclass(frozen=True)
class ListArguments:
    """What `note list` accepts; every field narrows the result."""

    query: str | None
    tag: str | None
    sort: str | None

    @classmethod
    def read(cls, args: argparse.Namespace) -> ListArguments:
        return cls(query=args.query, tag=args.tag, sort=args.sort)

    @property
    def narrowed(self) -> bool:
        """Whether the user asked for a subset rather than for everything."""
        return bool(self.query or self.tag)


@dataclass(frozen=True)
class EditArguments:
    """What `note edit` accepts."""

    note_id: int
    text: str | None
    added: tuple[str, ...]
    removed: tuple[str, ...]

    @classmethod
    def read(cls, args: argparse.Namespace) -> EditArguments:
        return cls(
            note_id=args.note_id,
            text=args.text,
            added=tuple(args.add_tag),
            removed=tuple(args.remove_tag),
        )

    @property
    def empty(self) -> bool:
        """Whether the command was given nothing to change."""
        return self.text is None and not self.added and not self.removed


def add_note(args: argparse.Namespace, state: AppState) -> Renderable:
    """Write a note and report the id it received (N1, T1)."""
    given = AddArguments.read(args)
    note = state.section(NoteBook).add(given.text, given.tags)
    return f"Note {note.id} saved."


def show_note(args: argparse.Namespace, state: AppState) -> Renderable:
    """Print one note with its tags and timestamps."""
    given = IdArgument.read(args)
    note = state.section(NoteBook)[given.note_id]
    return ui.details(
        f"Note {note.id}",
        [
            ("Text", note.text),
            ("Tags", _tags(note) or NO_TAGS),
            ("Created", note.stamp(note.created)),
            ("Updated", note.stamp(note.updated)),
        ],
    )


def list_notes(args: argparse.Namespace, state: AppState) -> Renderable:
    """List the notes the options ask for (N2, T2, T3)."""
    given = ListArguments.read(args)
    notes = state.section(NoteBook).select(
        query=given.query, tag=given.tag, sort=given.sort
    )
    if not notes:
        if given.narrowed:
            return "No note matches."
        return "There are no notes yet. Write one with 'note add <text>'."

    rows = [
        (note.id, note.preview(), _tags(note), note.stamp(note.updated))
        for note in notes
    ]
    return ui.table(TITLE, COLUMNS, rows)


def edit_note(args: argparse.Namespace, state: AppState) -> Renderable:
    """Change the text or the tags of a note (N3, T1)."""
    given = EditArguments.read(args)
    if given.empty:
        raise CommandError("Nothing to change. Pass --text, --add-tag or --remove-tag.")

    note = state.section(NoteBook)[given.note_id]
    note.edit(text=given.text, add=given.added, remove=given.removed)
    return f"Note {note.id} updated."


def delete_note(args: argparse.Namespace, state: AppState) -> Renderable:
    """Remove a note, asking first unless --force was given (N4)."""
    given = IdArgument.read(args)
    book = state.section(NoteBook)
    note = book[given.note_id]

    if not given.force and not ui.confirm(f"Delete note {note.id}: {note.preview()}?"):
        return f"Note {note.id} was kept."

    book.remove(note.id)
    return f"Note {note.id} deleted."


def _tags(note: Note) -> str:
    """The tags of a note on one line, in the order they are shown."""
    return ", ".join(note.tag_names())


def _help_of(parser: ReplArgumentParser) -> Handler:
    """A handler that shows what a group offers when it is typed on its own.

    Without it, `note` alone would only report that an action is missing, and
    the user would have to know that `help note` exists to find out which ones
    there are (D25).
    """

    def show(args: argparse.Namespace, state: AppState) -> Renderable:
        return parser.format_help().rstrip()

    return show
