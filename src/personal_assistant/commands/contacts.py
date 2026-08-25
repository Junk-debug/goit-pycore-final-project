"""The `contact` command group."""

from __future__ import annotations

from typing import Annotated

import typer

from personal_assistant import ui
from personal_assistant.errors import NotFoundError, ValidationError
from personal_assistant.models.address_book import AddressBook
from personal_assistant.models.contact import Contact
from personal_assistant.state import AppState
from personal_assistant.values import commas

EMPTY = "—"


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
        ui.success(f"Added {contact}.")

    @contacts.command("show")
    def show_contact(
        ctx: typer.Context,
        name: Annotated[
            str, typer.Argument(metavar="<name>", help="the name of the contact")
        ],
    ) -> None:
        """print one contact in full"""
        contact = required(ctx.obj, name)
        rows = [
            ("Phones", ", ".join(str(phone) for phone in contact.phones) or EMPTY),
            ("Email", str(contact.email) if contact.email else EMPTY),
            ("Address", str(contact.address) if contact.address else EMPTY),
            ("Birthday", str(contact.birthday) if contact.birthday else EMPTY),
        ]
        ui.render(ui.table(str(contact.name), ("Field", "Value"), rows))


def required(state: AppState, name: str) -> Contact:
    """Return the named contact, or report that the book does not hold one."""
    contact = state.section(AddressBook).find(name)
    if contact is None:
        raise NotFoundError(f"No contact named '{name}'.")
    return contact
