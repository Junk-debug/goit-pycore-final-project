"""Tests for the contact commands."""

from __future__ import annotations

import pytest
import typer
from typer.core import TyperGroup

from personal_assistant import cli
from personal_assistant.commands import build_app
from personal_assistant.models.address_book import AddressBook
from personal_assistant.state import AppState


@pytest.fixture
def command() -> TyperGroup:
    built = typer.main.get_command(build_app())
    assert isinstance(built, TyperGroup)
    return built


@pytest.fixture
def state() -> AppState:
    return AppState.empty()


def run(command, state, *argv: str) -> int:
    return cli.dispatch(command, list(argv), state)


def test_a_contact_is_created(command, state) -> None:
    assert run(command, state, "contact", "add", "John") == 0
    assert state.section(AddressBook).find("John") is not None


def test_every_field_is_stored(command, state) -> None:
    run(
        command,
        state,
        "contact",
        "add",
        "John",
        "--phone",
        "+48123456789",
        "--email",
        "john@example.com",
        "--address",
        "Dluga 5",
        "--birthday",
        "12.05.1998",
    )

    contact = state.section(AddressBook).find("John")
    assert contact is not None
    assert str(contact.email) == "john@example.com"
    assert str(contact.address) == "Dluga 5"
    assert str(contact.birthday) == "12.05.1998"


def test_commas_separate_several_numbers(command, state) -> None:
    run(
        command, state, "contact", "add", "John", "--phone", "+48123456789,+48999888777"
    )

    contact = state.section(AddressBook).find("John")
    assert contact is not None
    assert [str(phone) for phone in contact.phones] == ["+48123456789", "+48999888777"]


def test_spaces_around_the_commas_are_ignored(command, state) -> None:
    run(
        command,
        state,
        "contact",
        "add",
        "John",
        "--phone",
        "+48123456789, +48999888777",
    )

    contact = state.section(AddressBook).find("John")
    assert contact is not None
    assert len(contact.phones) == 2


def test_a_duplicate_name_is_refused(command, state, capsys) -> None:
    run(command, state, "contact", "add", "John")

    assert run(command, state, "contact", "add", "john") == 1
    assert "already exists" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--phone", "123"),
        ("--email", "not-an-email"),
        ("--birthday", "31.02.1990"),
        ("--birthday", "1990-01-01"),
    ],
)
def test_an_invalid_value_is_reported_without_storing_anything(
    command, state, option, value
) -> None:
    assert run(command, state, "contact", "add", "Bad", option, value) == 1
    assert state.section(AddressBook).find("Bad") is None


def test_one_bad_number_among_several_is_reported(command, state, capsys) -> None:
    assert (
        run(command, state, "contact", "add", "Bad", "--phone", "+48123456789,oops")
        == 1
    )
    assert "oops" in capsys.readouterr().out
