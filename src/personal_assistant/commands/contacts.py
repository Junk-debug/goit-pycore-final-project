"""The `contact` command group."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated

import typer
from rich.table import Table

from personal_assistant import ui
from personal_assistant.errors import NotFoundError, ValidationError
from personal_assistant.models.address_book import AddressBook
from personal_assistant.models.birthday import FORMAT as BIRTHDAY_FORMAT
from personal_assistant.models.contact import Contact
from personal_assistant.state import AppState
from personal_assistant.values import commas


class SortKey(str, Enum):
    """The two ways `contact list` can order its results."""

    name = "name"
    birthday = "birthday"


def register(app: typer.Typer) -> None:
    """Add the contact commands to the command tree."""
    contacts = typer.Typer(no_args_is_help=True)
    app.add_typer(contacts, name="contact", help="manage contacts")

    @contacts.command("add")
    def add_contact(
        ctx: typer.Context,
        name: Annotated[
            str, typer.Argument(metavar="<name>", help="the name of the contact")
        ],
        phone: Annotated[
            str,
            typer.Option(
                metavar="<phone>[,<phone>]",
                help="phone numbers, separated by commas",
            ),
        ] = "",
        email: Annotated[
            str | None, typer.Option(metavar="<email>", help="the email address")
        ] = None,
        address: Annotated[
            str | None, typer.Option(metavar="<address>", help="the postal address")
        ] = None,
        birthday: Annotated[
            str | None,
            typer.Option(metavar="<DD.MM.YYYY>", help="the date of birth"),
        ] = None,
    ) -> None:
        """create a contact"""
        book = ctx.obj.section(AddressBook)
        if book.find(name) is not None:
            raise ValidationError(f"A contact named '{name}' already exists.")

        contact = Contact(name)
        for number in commas(phone):
            contact.add_phone(number)
        if email is not None:
            contact.set_email(email)
        if address is not None:
            contact.set_address(address)
        if birthday is not None:
            contact.set_birthday(birthday)

        book.add(contact)
        ui.success(f"Added {contact.name}.")
        ui.render(ui.card(str(contact.name), _fields(contact)))

    @contacts.command("show")
    def show_contact(
        ctx: typer.Context,
        name: Annotated[
            str, typer.Argument(metavar="<name>", help="the name of the contact")
        ],
    ) -> None:
        """print one contact in full"""
        contact = required(ctx.obj, name)
        ui.render(ui.card(str(contact.name), _fields(contact)))

    @contacts.command("list")
    def list_contacts(
        ctx: typer.Context,
        query: Annotated[
            str | None,
            typer.Option(
                metavar="<text>",
                help="keep contacts whose name, phone, email or address "
                "contains this text",
            ),
        ] = None,
        birthday_in: Annotated[
            int | None,
            typer.Option(
                "--birthday-in",
                metavar="<days>",
                help="keep contacts whose birthday falls within this many "
                "days from today",
            ),
        ] = None,
        sort: Annotated[SortKey | None, typer.Option(help="order the results")] = None,
    ) -> None:
        """list and filter contacts"""
        if birthday_in is not None and birthday_in < 0:
            raise ValidationError("--birthday-in must not be negative.")

        book = ctx.obj.section(AddressBook)
        today = date.today()
        results = list(book.values())

        if query is not None:
            results = [contact for contact in results if contact.matches(query)]
        if birthday_in is not None:
            results = [
                contact
                for contact in results
                if contact.birthday is not None
                and _days_until(contact, today) <= birthday_in
            ]

        if sort is SortKey.name:
            results.sort(key=lambda contact: str(contact.name).casefold())
        elif sort is SortKey.birthday:
            results.sort(key=lambda contact: _sort_key_birthday(contact, today))

        if not results:
            ui.render("No contacts yet." if not book else "No contacts match.")
            return

        ui.render(_table(results, today, show_greeting=birthday_in is not None))

    @contacts.command("delete")
    def delete_contact(
        ctx: typer.Context,
        name: Annotated[
            str, typer.Argument(metavar="<name>", help="the contact to remove")
        ],
        force: Annotated[
            bool, typer.Option("--force", help="do not ask for confirmation")
        ] = False,
    ) -> None:
        """remove a contact and everything stored with it"""
        contact = required(ctx.obj, name)

        if not force and not ui.confirm(f"Delete {contact.name} and all its data?"):
            ui.render("Cancelled.")
            return

        ctx.obj.section(AddressBook).delete(contact.name.value)
        ui.success(f"Deleted {contact.name}.")

    @contacts.command("edit")
    def edit_contact(
        ctx: typer.Context,
        name: Annotated[
            str, typer.Argument(metavar="<name>", help="the contact to change")
        ],
        new_name: Annotated[
            str | None,
            typer.Option("--name", metavar="<new>", help="rename the contact"),
        ] = None,
        email: Annotated[
            str | None,
            typer.Option(
                metavar="<email>",
                help="set the email, or clear it when given an empty value",
            ),
        ] = None,
        address: Annotated[
            str | None,
            typer.Option(
                metavar="<address>",
                help="set the address, or clear it when given an empty value",
            ),
        ] = None,
        birthday: Annotated[
            str | None,
            typer.Option(
                metavar="<DD.MM.YYYY>",
                help="set the birthday, or clear it when given an empty value",
            ),
        ] = None,
        add_phone: Annotated[
            str,
            typer.Option(
                metavar="<phone>[,<phone>]",
                help="add phone numbers, separated by commas",
            ),
        ] = "",
        remove_phone: Annotated[
            str,
            typer.Option(
                metavar="<phone>[,<phone>]",
                help="remove phone numbers, separated by commas",
            ),
        ] = "",
    ) -> None:
        """change fields of an existing contact"""
        # `email`, `address` and `birthday` default to None when omitted, so an
        # empty string still counts as provided and clears the field. `add_phone`
        # and `remove_phone` default to "" instead, since they are plain `str`,
        # so a non-empty value is what counts as provided for them.
        provided = (
            new_name is not None,
            email is not None,
            address is not None,
            birthday is not None,
            bool(add_phone),
            bool(remove_phone),
        )
        if not any(provided):
            raise ValidationError("Nothing to change: pass at least one option.")

        book = ctx.obj.section(AddressBook)
        contact = required(ctx.obj, name)

        for number in commas(remove_phone):
            contact.remove_phone(number)
        for number in commas(add_phone):
            contact.add_phone(number)

        if email is not None:
            contact.set_email(email)
        if address is not None:
            contact.set_address(address)
        if birthday is not None:
            contact.set_birthday(birthday)
        if new_name is not None:
            book.rename(contact, new_name)

        ui.success(f"Updated {contact.name}.")
        ui.render(ui.card(str(contact.name), _fields(contact)))


def _fields(contact: Contact) -> list[tuple[str, str | None]]:
    """The fields of a contact, as shown by `add`, `show` and `edit` alike."""
    return [
        ("Phones", ", ".join(str(phone) for phone in contact.phones) or None),
        ("Email", str(contact.email) if contact.email else None),
        ("Address", str(contact.address) if contact.address else None),
        ("Birthday", str(contact.birthday) if contact.birthday else None),
    ]


def _days_until(contact: Contact, today: date) -> int:
    """Days from `today` until `contact`'s next birthday greeting.

    Only meaningful once the caller has checked the contact has a birthday.
    """
    assert contact.birthday is not None
    return (contact.birthday.next_greeting(today) - today).days


def _sort_key_birthday(contact: Contact, today: date) -> date:
    """A birthday-less contact sorts after every contact with one."""
    if contact.birthday is None:
        return date.max
    return contact.birthday.next_greeting(today)


def _table(contacts: list[Contact], today: date, *, show_greeting: bool) -> Table:
    """Render contacts as rows, as shown by `list`.

    `show_greeting` adds a column for the (possibly weekend-shifted) date
    each birthday is next celebrated, since `--birthday-in` is what makes
    that date relevant (C5).
    """
    columns = ["Name", "Phones", "Email", "Address", "Birthday"]
    if show_greeting:
        columns.append("Greet on")

    rows: list[list[str]] = []
    for contact in contacts:
        row = [
            str(contact.name),
            ", ".join(str(phone) for phone in contact.phones) or "—",
            str(contact.email) if contact.email else "—",
            str(contact.address) if contact.address else "—",
            str(contact.birthday) if contact.birthday else "—",
        ]
        if show_greeting:
            birthday = contact.birthday
            greeting = birthday.next_greeting(today) if birthday else None
            row.append(greeting.strftime(BIRTHDAY_FORMAT) if greeting else "—")
        rows.append(row)

    return ui.table("Contacts", columns, rows)


def required(state: AppState, name: str) -> Contact:
    """Return the named contact, or report that the book does not hold one."""
    contact = state.section(AddressBook).find(name)
    if contact is None:
        raise NotFoundError(f"No contact named '{name}'.")
    return contact
