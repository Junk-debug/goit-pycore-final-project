"""Tests for the contact models and their validation rules."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from personal_assistant.errors import ValidationError
from personal_assistant.models.address import Address
from personal_assistant.models.address_book import AddressBook, SortKey
from personal_assistant.models.birthday import Birthday
from personal_assistant.models.contact import Contact
from personal_assistant.models.email import Email
from personal_assistant.models.name import Name
from personal_assistant.models.phone import Phone


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


class TestNextGreeting:
    def test_a_birthday_later_this_year_is_celebrated_this_year(self) -> None:
        # 12 May 2026 is a Tuesday, so no weekend shift applies.
        today = date(2026, 1, 1)
        birthday = Birthday("12.05.1998")

        assert birthday.next_greeting(today) == date(2026, 5, 12)

    def test_a_birthday_already_passed_this_year_rolls_to_next_year(self) -> None:
        # 12 May 2027 is a Wednesday, so no weekend shift applies.
        today = date(2026, 8, 25)
        birthday = Birthday("12.05.1998")

        assert birthday.next_greeting(today) == date(2027, 5, 12)

    def test_today_counts_as_the_next_occurrence(self) -> None:
        today = date(2026, 8, 25)
        birthday = Birthday("25.08.1998")

        assert birthday.next_greeting(today) == today

    def test_a_29_february_is_celebrated_on_1_march_in_a_non_leap_year(self) -> None:
        # 1 March 2029 is a Thursday, so no weekend shift applies.
        today = date(2029, 1, 1)
        birthday = Birthday("29.02.2000")

        assert birthday.next_greeting(today) == date(2029, 3, 1)

    def test_a_29_february_is_kept_in_a_leap_year(self) -> None:
        today = date(2027, 12, 1)
        birthday = Birthday("29.02.2000")

        assert birthday.next_greeting(today) == date(2028, 2, 29)

    @pytest.mark.parametrize(
        ("raw_birthday", "today", "greeting"),
        [
            # Saturday 8 August 2026 -> Monday 10 August 2026
            ("08.08.1990", date(2026, 8, 1), date(2026, 8, 10)),
            # Sunday 9 August 2026 -> Monday 10 August 2026
            ("09.08.1990", date(2026, 8, 1), date(2026, 8, 10)),
        ],
    )
    def test_a_weekend_birthday_is_greeted_the_following_monday(
        self, raw_birthday: str, today: date, greeting: date
    ) -> None:
        assert Birthday(raw_birthday).next_greeting(today) == greeting

    def test_a_weekday_birthday_is_not_shifted(self) -> None:
        today = date(2026, 8, 1)
        # Wednesday 12 August 2026.
        birthday = Birthday("12.08.1990")

        assert birthday.next_greeting(today) == date(2026, 8, 12)


class TestContact:
    def test_a_contact_starts_with_only_a_name(self) -> None:
        contact = Contact("John")

        assert str(contact.name) == "John"
        assert contact.phones == []
        assert contact.email is None
        assert contact.address is None
        assert contact.birthday is None

    def test_several_phones_are_kept(self) -> None:
        contact = Contact("John")
        contact.add_phone("+48111222333")
        contact.add_phone("+48999888777")

        assert [str(phone) for phone in contact.phones] == [
            "+48111222333",
            "+48999888777",
        ]

    def test_the_same_number_is_not_added_twice(self) -> None:
        contact = Contact("John")
        contact.add_phone("+48111222333")

        with pytest.raises(ValidationError):
            contact.add_phone("+48 111 222 333")

    def test_an_invalid_value_leaves_the_contact_untouched(self) -> None:
        contact = Contact("John")

        with pytest.raises(ValidationError):
            contact.set_email("not-an-email")

        assert contact.email is None

    def test_the_text_form_lists_the_fields_that_are_set(self) -> None:
        contact = Contact("John")
        contact.add_phone("+48111222333")
        contact.set_email("john@example.com")

        shown = str(contact)
        assert "John" in shown
        assert "+48111222333" in shown
        assert "john@example.com" in shown
        assert "address" not in shown


class TestMatches:
    def test_a_substring_of_the_name_matches(self) -> None:
        contact = Contact("Anna Kowalska")

        assert contact.matches("kowal")

    def test_matching_ignores_case(self) -> None:
        contact = Contact("Anna Kowalska")

        assert contact.matches("KOWALSKA")

    def test_a_substring_of_a_phone_matches(self) -> None:
        contact = Contact("John")
        contact.add_phone("+48123456789")

        assert contact.matches("123456")

    def test_a_substring_of_the_email_matches(self) -> None:
        contact = Contact("John")
        contact.set_email("john@example.com")

        assert contact.matches("@example.com")

    def test_a_substring_of_the_address_matches(self) -> None:
        contact = Contact("John")
        contact.set_address("Dluga 5, Gdansk")

        assert contact.matches("gdansk")

    def test_an_unset_field_does_not_match(self) -> None:
        contact = Contact("John")

        assert not contact.matches("@example.com")

    def test_an_unrelated_query_does_not_match(self) -> None:
        contact = Contact("John")

        assert not contact.matches("Anna")


class TestAddressBook:
    def test_a_contact_is_found_by_its_name(self) -> None:
        book = AddressBook()
        book.add(Contact("John"))

        found = book.find("John")
        assert found is not None
        assert str(found.name) == "John"

    def test_a_contact_is_found_whatever_the_case(self) -> None:
        book = AddressBook()
        book.add(Contact("John"))

        assert book.find("john") is not None
        assert book.find("JOHN") is not None

    def test_the_spelling_that_was_entered_is_the_one_kept(self) -> None:
        book = AddressBook()
        book.add(Contact("John"))

        found = book.find("john")
        assert found is not None
        assert str(found.name) == "John"

    def test_an_unknown_name_returns_nothing(self) -> None:
        assert AddressBook().find("Nobody") is None

    def test_deleting_reports_whether_a_contact_was_there(self) -> None:
        book = AddressBook()
        book.add(Contact("John"))

        assert book.delete("john") is True
        assert book.delete("john") is False
        assert book.find("John") is None

    def test_adding_a_duplicate_name_is_refused(self) -> None:
        book = AddressBook()
        book.add(Contact("John"))

        with pytest.raises(ValidationError):
            book.add(Contact("john"))
        assert len(book) == 1


class TestAddressBookSelect:
    """`AddressBook.select` backs `contact list`, shared with the web adapter."""

    TODAY = date(2026, 8, 25)  # a Tuesday

    def test_without_options_everyone_is_returned(self) -> None:
        book = AddressBook()
        book.add(Contact("John"))
        book.add(Contact("Anna"))

        assert {str(c.name) for c in book.select()} == {"John", "Anna"}

    def test_a_query_narrows_by_any_field(self) -> None:
        book = AddressBook()
        matching = Contact("John")
        matching.set_address("Dluga 5, Gdansk")
        book.add(matching)
        book.add(Contact("Anna"))

        result = book.select(query="gdansk")

        assert [str(c.name) for c in result] == ["John"]

    def test_sort_by_name_is_alphabetical_and_case_insensitive(self) -> None:
        book = AddressBook()
        book.add(Contact("zoe"))
        book.add(Contact("Anna"))

        result = book.select(sort=SortKey.NAME)

        assert [str(c.name) for c in result] == ["Anna", "zoe"]

    def test_sort_by_birthday_puts_the_soonest_first(self) -> None:
        book = AddressBook()
        later = Contact("Later")
        later.set_birthday("01.09.1990")
        sooner = Contact("Sooner")
        sooner.set_birthday("27.08.1990")
        book.add(later)
        book.add(sooner)

        result = book.select(sort=SortKey.BIRTHDAY, today=self.TODAY)

        assert [str(c.name) for c in result] == ["Sooner", "Later"]

    def test_sort_by_birthday_puts_a_birthday_less_contact_last(self) -> None:
        book = AddressBook()
        book.add(Contact("Zoe"))
        with_birthday = Contact("Anna")
        with_birthday.set_birthday("27.08.1990")
        book.add(with_birthday)

        result = book.select(sort=SortKey.BIRTHDAY, today=self.TODAY)

        assert [str(c.name) for c in result] == ["Anna", "Zoe"]

    def test_birthday_in_keeps_only_upcoming_birthdays(self) -> None:
        book = AddressBook()
        soon = Contact("Soon")
        soon.set_birthday("27.08.1990")
        far = Contact("Far")
        far.set_birthday("01.01.1990")
        book.add(soon)
        book.add(far)
        book.add(Contact("NoBirthday"))

        result = book.select(birthday_in=7, today=self.TODAY)

        assert [str(c.name) for c in result] == ["Soon"]

    def test_a_negative_window_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AddressBook().select(birthday_in=-1)

    def test_query_and_birthday_in_combine(self) -> None:
        book = AddressBook()
        matching = Contact("John")
        matching.set_birthday("27.08.1990")
        matching.set_address("Gdansk")
        book.add(matching)
        wrong_place = Contact("Anna")
        wrong_place.set_birthday("27.08.1990")
        book.add(wrong_place)

        result = book.select(query="gdansk", birthday_in=7, today=self.TODAY)

        assert [str(c.name) for c in result] == ["John"]

    def test_an_unknown_sort_key_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AddressBook().select(sort="nonsense")
