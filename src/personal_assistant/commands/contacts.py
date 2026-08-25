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
        fields = [
            ("Phones", ", ".join(str(phone) for phone in contact.phones) or None),
            ("Email", str(contact.email) if contact.email else None),
            ("Address", str(contact.address) if contact.address else None),
            ("Birthday", str(contact.birthday) if contact.birthday else None),
        ]
        ui.render(ui.card(str(contact.name), fields))

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

        ui.success(f"Updated {contact}.")


def required(state: AppState, name: str) -> Contact:
    """Return the named contact, or report that the book does not hold one."""
    contact = state.section(AddressBook).find(name)
    if contact is None:
        raise NotFoundError(f"No contact named '{name}'.")
    return contact
