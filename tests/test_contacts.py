"""Tests for the contact commands."""

from __future__ import annotations

from datetime import date

import pytest
import typer
from typer.core import TyperGroup

from personal_assistant import cli
from personal_assistant.commands import build_app
from personal_assistant.commands import contacts as contacts_module
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


class TestShow:
    def test_every_field_is_printed(self, command, state, capsys) -> None:
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
        capsys.readouterr()

        assert run(command, state, "contact", "show", "John") == 0

        printed = capsys.readouterr().out
        for expected in (
            "John",
            "+48123456789",
            "john@example.com",
            "Dluga 5",
            "12.05.1998",
        ):
            assert expected in printed

    def test_a_field_that_is_not_set_is_marked_as_empty(
        self, command, state, capsys
    ) -> None:
        run(command, state, "contact", "add", "Zoe")
        capsys.readouterr()

        run(command, state, "contact", "show", "Zoe")

        assert "—" in capsys.readouterr().out

    def test_the_name_is_matched_whatever_the_case(self, command, state) -> None:
        run(command, state, "contact", "add", "John")

        assert run(command, state, "contact", "show", "john") == 0

    def test_an_unknown_name_is_reported(self, command, state, capsys) -> None:
        assert run(command, state, "contact", "show", "Nobody") == 1
        assert "No contact named 'Nobody'" in capsys.readouterr().out


class TestDelete:
    def test_a_contact_is_removed_with_force(self, command, state) -> None:
        run(command, state, "contact", "add", "John")

        assert run(command, state, "contact", "delete", "John", "--force") == 0
        assert state.section(AddressBook).find("John") is None

    def test_without_force_and_without_a_terminal_nothing_is_removed(
        self, command, state, capsys
    ) -> None:
        run(command, state, "contact", "add", "John")
        capsys.readouterr()

        assert run(command, state, "contact", "delete", "John") == 0

        assert state.section(AddressBook).find("John") is not None
        assert "Cancelled" in capsys.readouterr().out

    def test_an_unknown_name_is_reported(self, command, state, capsys) -> None:
        assert run(command, state, "contact", "delete", "Nobody", "--force") == 1
        assert "No contact named 'Nobody'" in capsys.readouterr().out

    def test_the_name_is_matched_whatever_the_case(self, command, state) -> None:
        run(command, state, "contact", "add", "John")

        assert run(command, state, "contact", "delete", "john", "--force") == 0
        assert state.section(AddressBook).find("John") is None


class TestEdit:
    def _add_john(self, command, state) -> None:
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

    def test_a_single_field_is_replaced(self, command, state) -> None:
        self._add_john(command, state)

        run(command, state, "contact", "edit", "John", "--email", "new@example.com")

        contact = state.section(AddressBook).find("John")
        assert contact is not None
        assert str(contact.email) == "new@example.com"

    def test_an_empty_value_clears_an_optional_field(self, command, state) -> None:
        self._add_john(command, state)

        run(command, state, "contact", "edit", "John", "--address", "")

        contact = state.section(AddressBook).find("John")
        assert contact is not None
        assert contact.address is None

    def test_a_phone_is_added(self, command, state) -> None:
        self._add_john(command, state)

        run(command, state, "contact", "edit", "John", "--add-phone", "+48999888777")

        contact = state.section(AddressBook).find("John")
        assert contact is not None
        assert [str(p) for p in contact.phones] == ["+48123456789", "+48999888777"]

    def test_several_phones_are_added_at_once(self, command, state) -> None:
        self._add_john(command, state)

        run(
            command,
            state,
            "contact",
            "edit",
            "John",
            "--add-phone",
            "+48999888777,+48111222333",
        )

        contact = state.section(AddressBook).find("John")
        assert contact is not None
        assert len(contact.phones) == 3

    def test_replacing_a_phone_is_one_atomic_edit(self, command, state) -> None:
        self._add_john(command, state)

        run(
            command,
            state,
            "contact",
            "edit",
            "John",
            "--remove-phone",
            "+48123456789",
            "--add-phone",
            "+48111222333",
        )

        contact = state.section(AddressBook).find("John")
        assert contact is not None
        assert [str(p) for p in contact.phones] == ["+48111222333"]

    def test_removing_a_number_the_contact_does_not_have_is_reported(
        self, command, state, capsys
    ) -> None:
        self._add_john(command, state)
        capsys.readouterr()

        failed = run(
            command, state, "contact", "edit", "John", "--remove-phone", "+48000000000"
        )

        assert failed == 1
        assert "has no number" in capsys.readouterr().out

    def test_the_contact_is_renamed(self, command, state) -> None:
        self._add_john(command, state)

        run(command, state, "contact", "edit", "John", "--name", "John Doe")

        book = state.section(AddressBook)
        assert book.find("John") is None
        assert book.find("John Doe") is not None

    def test_renaming_onto_an_existing_name_is_refused(
        self, command, state, capsys
    ) -> None:
        self._add_john(command, state)
        run(command, state, "contact", "add", "Anna")
        capsys.readouterr()

        failed = run(command, state, "contact", "edit", "John", "--name", "Anna")

        assert failed == 1
        assert "already exists" in capsys.readouterr().out
        assert state.section(AddressBook).find("John") is not None

    def test_an_invalid_new_value_is_reported_without_changing_anything(
        self, command, state
    ) -> None:
        self._add_john(command, state)

        assert run(command, state, "contact", "edit", "John", "--email", "oops") == 1

        contact = state.section(AddressBook).find("John")
        assert contact is not None
        assert str(contact.email) == "john@example.com"

    def test_an_unknown_name_is_reported(self, command, state, capsys) -> None:
        assert (
            run(command, state, "contact", "edit", "Nobody", "--email", "a@b.com") == 1
        )
        assert "No contact named 'Nobody'" in capsys.readouterr().out


class TestList:
    """Tests for filtering, sorting and the upcoming-birthday window."""

    # A fixed Tuesday, so a birthday falling on the following Saturday or
    # Sunday reliably exercises the weekend shift regardless of when the
    # suite actually runs.
    TODAY = date(2026, 8, 25)

    @pytest.fixture(autouse=True)
    def _frozen_today(self, monkeypatch) -> None:
        class FixedToday(date):
            @classmethod
            def today(cls) -> date:  # type: ignore[override]
                return TestList.TODAY

        monkeypatch.setattr(contacts_module, "date", FixedToday)

    def test_an_empty_book_says_so(self, command, state, capsys) -> None:
        assert run(command, state, "contact", "list") == 0
        assert "No contacts yet." in capsys.readouterr().out

    def test_every_contact_is_listed_without_options(
        self, command, state, capsys
    ) -> None:
        run(command, state, "contact", "add", "John")
        run(command, state, "contact", "add", "Anna")
        capsys.readouterr()

        assert run(command, state, "contact", "list") == 0

        printed = capsys.readouterr().out
        assert "John" in printed
        assert "Anna" in printed

    def test_query_matches_any_field(self, command, state, capsys) -> None:
        run(command, state, "contact", "add", "John", "--address", "Dluga 5, Gdansk")
        run(command, state, "contact", "add", "Anna")
        capsys.readouterr()

        run(command, state, "contact", "list", "--query", "gdansk")

        printed = capsys.readouterr().out
        assert "John" in printed
        assert "Anna" not in printed

    def test_a_query_matching_nobody_is_distinct_from_an_empty_book(
        self, command, state, capsys
    ) -> None:
        run(command, state, "contact", "add", "John")
        capsys.readouterr()

        run(command, state, "contact", "list", "--query", "nobody")

        assert "No contacts match." in capsys.readouterr().out

    def test_sort_by_name_is_alphabetical_and_case_insensitive(
        self, command, state, capsys
    ) -> None:
        run(command, state, "contact", "add", "zoe")
        run(command, state, "contact", "add", "Anna")
        capsys.readouterr()

        run(command, state, "contact", "list", "--sort", "name")

        printed = capsys.readouterr().out
        assert printed.index("Anna") < printed.index("zoe")

    def test_sort_by_birthday_puts_the_soonest_first(
        self, command, state, capsys
    ) -> None:
        run(command, state, "contact", "add", "Later", "--birthday", "01.09.1990")
        run(command, state, "contact", "add", "Sooner", "--birthday", "27.08.1990")
        capsys.readouterr()

        run(command, state, "contact", "list", "--sort", "birthday")

        printed = capsys.readouterr().out
        assert printed.index("Sooner") < printed.index("Later")

    def test_sort_by_birthday_puts_a_birthday_less_contact_last(
        self, command, state, capsys
    ) -> None:
        run(command, state, "contact", "add", "Zoe")
        run(command, state, "contact", "add", "Anna", "--birthday", "27.08.1990")
        capsys.readouterr()

        run(command, state, "contact", "list", "--sort", "birthday")

        printed = capsys.readouterr().out
        assert printed.index("Anna") < printed.index("Zoe")

    def test_birthday_in_keeps_only_upcoming_birthdays(
        self, command, state, capsys
    ) -> None:
        run(command, state, "contact", "add", "Soon", "--birthday", "27.08.1990")
        run(command, state, "contact", "add", "Far", "--birthday", "01.01.1990")
        run(command, state, "contact", "add", "NoBirthday")
        capsys.readouterr()

        run(command, state, "contact", "list", "--birthday-in", "7")

        printed = capsys.readouterr().out
        assert "Soon" in printed
        assert "Far" not in printed
        assert "NoBirthday" not in printed

    def test_birthday_in_shows_the_greeting_date_shifted_off_a_weekend(
        self, command, state, capsys
    ) -> None:
        # 30.08.1990 falls on a Sunday relative to TODAY (25.08.2026, a
        # Tuesday); the greeting must move to the Monday.
        run(command, state, "contact", "add", "Anna", "--birthday", "30.08.1990")
        capsys.readouterr()

        run(command, state, "contact", "list", "--birthday-in", "7")

        printed = capsys.readouterr().out
        assert "Greet on" in printed
        assert "31.08.2026" in printed

    def test_birthday_in_is_absent_from_the_table_without_the_option(
        self, command, state, capsys
    ) -> None:
        run(command, state, "contact", "add", "John", "--birthday", "27.08.1990")
        capsys.readouterr()

        run(command, state, "contact", "list")

        assert "Greet on" not in capsys.readouterr().out

    def test_a_negative_window_is_rejected(self, command, state, capsys) -> None:
        assert run(command, state, "contact", "list", "--birthday-in", "-1") == 1
        assert "must not be negative" in capsys.readouterr().out
