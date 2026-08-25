"""The `note` command group: notes, their tags and what you do to them.

Covers N1 to N4 and the optional tag scope T1 to T3. The group builds its own
application and keeps the notes in its own section of the state, so adding a
command here never touches a file another group owns.
"""

from __future__ import annotations

from typing import Annotated

import typer

from personal_assistant import ui
from personal_assistant.errors import CommandError
from personal_assistant.models.note import Note
from personal_assistant.models.note_book import NoteBook, SortKey
from personal_assistant.state import AppState
from personal_assistant.values import commas

TITLE = "Notes"
COLUMNS = (
    ui.Column("Id", style="cyan", wrap=False),
    ui.Column("Note"),
    ui.Column("Tags", style="magenta", wrap=False),
    ui.Column("Updated", wrap=False),
)
EMPTY = "There are no notes yet. Write one with 'note add <text>'."
NOTHING_FOUND = "No note matches."
NOTHING_TO_CHANGE = "Nothing to change. Pass --text, --add-tag or --remove-tag."


def register(app: typer.Typer) -> None:
    """Add the note commands to the command tree."""
    notes = typer.Typer(no_args_is_help=True)
    app.add_typer(notes, name="note", help="manage notes and their tags")

    @notes.command("add")
    def add_note(
        ctx: typer.Context,
        text: Annotated[
            str, typer.Argument(metavar="<text>", help="the text of the note")
        ],
        tag: Annotated[
            list[str] | None,
            typer.Option(
                metavar="<tag>",
                help="a keyword describing the note; repeat it or use commas",
            ),
        ] = None,
    ) -> None:
        """write a new note"""
        note = _notes(ctx).add(text, _tags(tag))
        ui.success(f"Note {note.id} saved.")

    @notes.command("show")
    def show_note(
        ctx: typer.Context,
        note_id: Annotated[
            int, typer.Argument(metavar="<id>", help="the id shown by 'note list'")
        ],
    ) -> None:
        """print one note in full"""
        note = _notes(ctx)[note_id]
        ui.render(ui.card(f"Note {note.id}", _fields(note)))

    @notes.command("list")
    def list_notes(
        ctx: typer.Context,
        query: Annotated[
            str | None,
            typer.Option(
                metavar="<text>", help="keep the notes whose text contains this"
            ),
        ] = None,
        tag: Annotated[
            str | None,
            typer.Option(metavar="<tag>", help="keep the notes carrying this tag"),
        ] = None,
        sort: Annotated[
            SortKey | None,
            typer.Option(
                help="order by first tag, or by the time written or last changed"
            ),
        ] = None,
    ) -> None:
        """list notes, narrowed by the options"""
        found = _notes(ctx).select(query=query, tag=tag, sort=sort)
        if not found:
            ui.render(NOTHING_FOUND if query or tag else EMPTY)
            return

        ui.render(
            ui.table(
                TITLE,
                COLUMNS,
                [
                    (note.id, note.preview(), _listed(note), note.stamp(note.updated))
                    for note in found
                ],
            )
        )

    @notes.command("edit")
    def edit_note(
        ctx: typer.Context,
        note_id: Annotated[
            int, typer.Argument(metavar="<id>", help="the id of the note")
        ],
        text: Annotated[
            str | None,
            typer.Option(metavar="<text>", help="replace the text of the note"),
        ] = None,
        add_tag: Annotated[
            list[str] | None,
            typer.Option(metavar="<tag>", help="attach a tag; repeat it or use commas"),
        ] = None,
        remove_tag: Annotated[
            list[str] | None,
            typer.Option(metavar="<tag>", help="detach a tag; repeat it or use commas"),
        ] = None,
    ) -> None:
        """change the text or the tags of a note"""
        added, removed = _tags(add_tag), _tags(remove_tag)
        if text is None and not added and not removed:
            raise CommandError(NOTHING_TO_CHANGE)

        note = _notes(ctx)[note_id]
        note.edit(text=text, add=added, remove=removed)
        ui.success(f"Note {note.id} updated.")
        ui.render(ui.card(f"Note {note.id}", _fields(note)))

    @notes.command("delete")
    def delete_note(
        ctx: typer.Context,
        note_id: Annotated[
            int, typer.Argument(metavar="<id>", help="the id of the note")
        ],
        force: Annotated[
            bool, typer.Option("--force", help="delete without asking first")
        ] = False,
    ) -> None:
        """remove a note"""
        book = _notes(ctx)
        note = book[note_id]

        if not force and not ui.confirm(f"Delete note {note.id}: {note.preview()}?"):
            ui.render(f"Note {note.id} was kept.")
            return

        book.remove(note.id)
        ui.success(f"Note {note.id} deleted.")


def _notes(ctx: typer.Context) -> NoteBook:
    """The notebook of this session, from the state the dispatcher passed in.

    Reading `ctx.obj` through one typed function keeps the commands themselves
    checkable: everywhere else the notebook is a `NoteBook` and not whatever
    the context happens to carry.
    """
    state: AppState = ctx.obj
    return state.section(NoteBook)


def _tags(given: list[str] | None) -> tuple[str, ...]:
    """The tags of one invocation, however they were spelled.

    `--tag study --tag python` is the form section 7.4 specifies and
    `--tag study,python` is how the contact group already writes a list, so
    both are accepted and the two groups teach the same habits.
    """
    return tuple(tag for value in given or () for tag in commas(value))


def _listed(note: Note) -> str:
    """The tags of a note on one line, in the order they are shown."""
    return ", ".join(note.tag_names())


def _fields(note: Note) -> list[tuple[str, str | None]]:
    """The fields of a note, as shown by `show` and `edit` alike."""
    return [
        ("Text", str(note.text)),
        ("Tags", _listed(note) or None),
        ("Created", note.stamp(note.created)),
        ("Updated", note.stamp(note.updated)),
    ]
