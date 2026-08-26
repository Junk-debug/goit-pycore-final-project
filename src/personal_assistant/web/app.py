"""Routes of the web adapter.

Every route does what a command does: read the state, call a model method,
show the result. The model methods already carry the rules — a duplicate
name, an unknown id, a bad phone number — so no route repeats what
`commands/contacts.py` or `commands/notes.py` already established. The
one thing genuinely new here is turning a caught `AssistantError` into a
re-rendered form instead of a printed line.
"""

from __future__ import annotations

from datetime import date

from flask import Flask, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from personal_assistant.errors import AssistantError, NotFoundError
from personal_assistant.models.address_book import AddressBook
from personal_assistant.models.address_book import SortKey as ContactSort
from personal_assistant.models.contact import Contact
from personal_assistant.models.note_book import NoteBook
from personal_assistant.models.note_book import SortKey as NoteSort
from personal_assistant.state import AppState
from personal_assistant.values import commas


def _iso_to_domain(raw: str) -> str:
    """Convert a date input's ISO value to the domain's DD.MM.YYYY.

    A native `<input type="date">` always submits ISO 8601, whatever the
    browser's locale; the domain format stays DD.MM.YYYY, which is also what
    the CLI accepts, so the two are bridged here and nowhere else. A value
    that does not split into three parts is passed through unchanged and left
    for `Birthday` to reject with its own message, rather than failing here
    with something less clear.
    """
    parts = raw.split("-")
    if len(parts) != 3:
        return raw
    year, month, day = parts
    return f"{day}.{month}.{year}"


def create_app(state: AppState) -> Flask:
    """Build the Flask application over one session's state.

    The state is captured once, by reference: every route reads and writes
    the same `AddressBook` and `NoteBook` the CLI commands use in this same
    process, so the two adapters see one another's changes immediately, and
    `Storage.save` persists whichever of them ran last.
    """
    app = Flask(__name__)

    @app.context_processor
    def inject_globals() -> dict[str, object]:
        # A birthday's date picker caps at today, matching the model's own
        # rule that a birthday cannot be in the future.
        return {"today": date.today().isoformat()}

    @app.errorhandler(AssistantError)
    def handle_assistant_error(error: AssistantError) -> ResponseReturnValue:
        """Turn a domain error into a page instead of an unhandled crash.

        Every not-found and every validation failure from the model layer
        reaches here the same way, whichever route it came from — the web
        equivalent of criterion 11, and a single place instead of a try/except
        around each route that reads a record.
        """
        status = 404 if isinstance(error, NotFoundError) else 400
        return render_template("error.html", message=str(error), status=status), status

    @app.get("/")
    def index() -> str:
        book = state.section(AddressBook)
        notes = state.section(NoteBook)
        return render_template(
            "index.html", contact_count=len(book), note_count=len(notes)
        )

    # --- Contacts ---------------------------------------------------------

    @app.get("/contacts")
    def list_contacts() -> str:
        book = state.section(AddressBook)
        query = request.args.get("query") or None
        sort = request.args.get("sort") or None
        raw_window = request.args.get("birthday_in") or ""
        error = None
        contacts: list[Contact] = []
        try:
            window = int(raw_window) if raw_window else None
            contacts = book.select(query=query, birthday_in=window, sort=sort)
        except (AssistantError, ValueError) as caught:
            error = (
                str(caught)
                if isinstance(caught, AssistantError)
                else ("The birthday window must be a whole number of days.")
            )
        return render_template(
            "contacts/list.html",
            contacts=contacts,
            query=query or "",
            sort=sort or "",
            birthday_in=raw_window,
            sort_keys=[key.value for key in ContactSort],
            error=error,
        )

    @app.get("/contacts/new")
    def new_contact_form() -> str:
        return render_template(
            "contacts/form.html", contact=None, error=None, values={}
        )

    @app.post("/contacts")
    def create_contact() -> ResponseReturnValue:
        form = request.form
        try:
            contact = Contact(form.get("name", ""))
            for number in commas(form.get("phone", "")):
                contact.add_phone(number)
            if form.get("email"):
                contact.set_email(form["email"])
            if form.get("address"):
                contact.set_address(form["address"])
            if form.get("birthday"):
                contact.set_birthday(_iso_to_domain(form["birthday"]))
            state.section(AddressBook).add(contact)
        except AssistantError as error:
            return _form_error("contacts/form.html", error, contact=None, values=form)
        return redirect(url_for("show_contact", name=contact.name.value))

    @app.get("/contacts/<name>")
    def show_contact(name: str) -> str:
        return render_template("contacts/detail.html", contact=_contact_or_404(name))

    @app.get("/contacts/<name>/edit")
    def edit_contact_form(name: str) -> str:
        contact = _contact_or_404(name)
        return render_template(
            "contacts/form.html", contact=contact, error=None, values=None
        )

    @app.post("/contacts/<name>/edit")
    def update_contact(name: str) -> ResponseReturnValue:
        book = state.section(AddressBook)
        contact = _contact_or_404(name)
        form = request.form
        try:
            if "phone" in form:
                contact.set_phones(commas(form["phone"]))
            if "email" in form:
                contact.set_email(form["email"])
            if "address" in form:
                contact.set_address(form["address"])
            if "birthday" in form:
                raw = form["birthday"]
                contact.set_birthday(_iso_to_domain(raw) if raw else raw)
            new_name = form.get("name", "").strip()
            if new_name and new_name != contact.name.value:
                book.rename(contact, new_name)
        except AssistantError as error:
            return _form_error(
                "contacts/form.html", error, contact=contact, values=form
            )
        return redirect(url_for("show_contact", name=contact.name.value))

    @app.post("/contacts/<name>/delete")
    def delete_contact(name: str) -> ResponseReturnValue:
        state.section(AddressBook).delete(name)
        return redirect(url_for("list_contacts"))

    # --- Notes --------------------------------------------------------------

    @app.get("/notes")
    def list_notes() -> str:
        book = state.section(NoteBook)
        query = request.args.get("query") or None
        tag = request.args.get("tag") or None
        sort = request.args.get("sort") or None
        try:
            notes = book.select(query=query, tag=tag, sort=sort)
            error = None
        except AssistantError as caught:
            notes, error = [], str(caught)
        return render_template(
            "notes/list.html",
            notes=notes,
            query=query or "",
            tag=tag or "",
            sort=sort or "",
            sort_keys=[key.value for key in NoteSort],
            all_tags=book.tags(),
            error=error,
        )

    @app.get("/notes/new")
    def new_note_form() -> str:
        return render_template("notes/form.html", note=None, error=None, values={})

    @app.post("/notes")
    def create_note() -> ResponseReturnValue:
        form = request.form
        book = state.section(NoteBook)
        try:
            note = book.add(form.get("text", ""), commas(form.get("tags", "")))
        except AssistantError as error:
            return _form_error("notes/form.html", error, note=None, values=form)
        return redirect(url_for("show_note", note_id=note.id))

    @app.get("/notes/<int:note_id>")
    def show_note(note_id: int) -> str:
        return render_template(
            "notes/detail.html", note=state.section(NoteBook)[note_id]
        )

    @app.get("/notes/<int:note_id>/edit")
    def edit_note_form(note_id: int) -> str:
        note = state.section(NoteBook)[note_id]
        return render_template("notes/form.html", note=note, error=None, values=None)

    @app.post("/notes/<int:note_id>/edit")
    def update_note(note_id: int) -> ResponseReturnValue:
        note = state.section(NoteBook)[note_id]
        form = request.form
        try:
            text = form.get("text") or None
            if text is not None:
                note.edit(text=text)
            if "tags" in form:
                note.set_tags(commas(form["tags"]))
        except AssistantError as error:
            return _form_error("notes/form.html", error, note=note, values=form)
        return redirect(url_for("show_note", note_id=note.id))

    @app.post("/notes/<int:note_id>/delete")
    def delete_note(note_id: int) -> ResponseReturnValue:
        state.section(NoteBook).remove(note_id)
        return redirect(url_for("list_notes"))

    def _contact_or_404(name: str) -> Contact:
        contact = state.section(AddressBook).find(name)
        if contact is None:
            raise NotFoundError(f"No contact named '{name}'.")
        return contact

    def _form_error(
        template: str, error: AssistantError, **context: object
    ) -> tuple[str, int]:
        return render_template(template, error=str(error), **context), 400

    return app
