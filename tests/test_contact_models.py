"""Tests for the contact models and their validation rules (D20)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from personal_assistant.errors import ValidationError
from personal_assistant.models.address import Address
from personal_assistant.models.address_book import AddressBook
from personal_assistant.models.birthday import Birthday
from personal_assistant.models.email import Email
from personal_assistant.models.name import Name
from personal_assistant.models.phone import Phone
from personal_assistant.models.record import Record


class TestName:
    def test_a_plain_name_is_accepted(self) -> None:
        assert Name("John").value == "John"

    def test_surrounding_spaces_are_removed(self) -> None:
        assert Name("  John  ").value == "John"

    @pytest.mark.parametrize("raw", ["", "   ", "x" * 65])
    def test_an_unusable_name_is_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError):
            Name(raw)


class TestPhone:
    @pytest.mark.parametrize(
        ("typed", "stored"),
        [
            ("+48123456789", "+48123456789"),
            ("+48 123-456-789", "+48123456789"),
            ("(048) 123.456.789", "048123456789"),
            ("123456789", "123456789"),
        ],
    )
    def test_separators_are_removed_before_storing(
        self, typed: str, stored: str
    ) -> None:
        assert Phone(typed).value == stored

    @pytest.mark.parametrize("raw", ["123", "1" * 16, "+", "abcdefghi", ""])
    def test_an_invalid_number_is_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError):
            Phone(raw)

    def test_the_same_number_typed_differently_compares_equal(self) -> None:
        assert Phone("+48 123 456 789") == Phone("+48123456789")


class TestEmail:
    @pytest.mark.parametrize(
        "raw", ["john@example.com", "a.b+c@mail.example.co.uk", "x_1@a-b.pl"]
    )
    def test_a_well_formed_address_is_accepted(self, raw: str) -> None:
        assert Email(raw).value == raw

    @pytest.mark.parametrize(
        "raw", ["", "john", "john@", "@example.com", "john@example", "a b@c.com"]
    )
    def test_a_malformed_address_is_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError):
            Email(raw)


class TestAddress:
    def test_a_street_address_is_accepted(self) -> None:
        assert Address("Dluga 5, Gdansk").value == "Dluga 5, Gdansk"

    @pytest.mark.parametrize("raw", ["", "   ", "x" * 129])
    def test_an_unusable_address_is_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError):
            Address(raw)


class TestBirthday:
    def test_a_date_is_parsed_and_shown_back_in_the_same_format(self) -> None:
        birthday = Birthday("12.05.1998")

        assert birthday.value == date(1998, 5, 12)
        assert str(birthday) == "12.05.1998"

    def test_the_29th_of_february_of_a_leap_year_is_accepted(self) -> None:
        assert Birthday("29.02.2000").value == date(2000, 2, 29)

    @pytest.mark.parametrize(
        "raw",
        [
            "31.02.1990",  # no such day
            "29.02.1999",  # not a leap year
            "1990-01-01",  # wrong format
            "12/05/1998",  # wrong separator
            "",
            "tomorrow",
        ],
    )
    def test_a_date_that_does_not_exist_is_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError):
            Birthday(raw)

    def test_a_date_in_the_future_is_rejected(self) -> None:
        tomorrow = date.today() + timedelta(days=1)

        with pytest.raises(ValidationError):
            Birthday(tomorrow.strftime("%d.%m.%Y"))

    def test_today_is_still_a_valid_birthday(self) -> None:
        assert Birthday(date.today().strftime("%d.%m.%Y")).value == date.today()

    def test_a_date_before_the_earliest_year_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Birthday("01.01.1899")


class TestRecord:
    def test_a_record_starts_with_only_a_name(self) -> None:
        record = Record("John")

        assert str(record.name) == "John"
        assert record.phones == []
        assert record.email is None
        assert record.address is None
        assert record.birthday is None

    def test_several_phones_are_kept(self) -> None:
        record = Record("John")
        record.add_phone("+48111222333")
        record.add_phone("+48999888777")

        assert [str(phone) for phone in record.phones] == [
            "+48111222333",
            "+48999888777",
        ]

    def test_the_same_number_is_not_added_twice(self) -> None:
        record = Record("John")
        record.add_phone("+48111222333")

        with pytest.raises(ValidationError):
            record.add_phone("+48 111 222 333")

    def test_an_invalid_value_leaves_the_record_untouched(self) -> None:
        record = Record("John")

        with pytest.raises(ValidationError):
            record.set_email("not-an-email")

        assert record.email is None

    def test_the_text_form_lists_the_fields_that_are_set(self) -> None:
        record = Record("John")
        record.add_phone("+48111222333")
        record.set_email("john@example.com")

        shown = str(record)
        assert "John" in shown
        assert "+48111222333" in shown
        assert "john@example.com" in shown
        assert "address" not in shown


class TestAddressBook:
    def test_a_record_is_found_by_its_name(self) -> None:
        book = AddressBook()
        book.add_record(Record("John"))

        found = book.find("John")
        assert found is not None
        assert str(found.name) == "John"

    def test_a_record_is_found_whatever_the_case(self) -> None:
        book = AddressBook()
        book.add_record(Record("John"))

        assert book.find("john") is not None
        assert book.find("JOHN") is not None

    def test_the_spelling_that_was_entered_is_the_one_kept(self) -> None:
        book = AddressBook()
        book.add_record(Record("John"))

        found = book.find("john")
        assert found is not None
        assert str(found.name) == "John"

    def test_an_unknown_name_returns_nothing(self) -> None:
        assert AddressBook().find("Nobody") is None

    def test_deleting_reports_whether_a_record_was_there(self) -> None:
        book = AddressBook()
        book.add_record(Record("John"))

        assert book.delete("john") is True
        assert book.delete("john") is False
        assert book.find("John") is None
