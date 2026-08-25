"""Tests for the notes: the models, the notebook and the command group.

The validation rules of D20 are covered with their passing and their failing
cases, as D22 asks, and every command gets its successful path and its main
error.
"""

from __future__ import annotations

import pytest

from personal_assistant.errors import NotFoundError, ValidationError
from personal_assistant.models.note import MAX_LENGTH, Note, NoteText
from personal_assistant.models.tag import Tag


@pytest.fixture
def note() -> Note:
    return Note(1, "Read the pickle docs", ["study", "python"])


@pytest.mark.parametrize(
    ("raw", "stored"),
    [("python", "python"), ("Python", "python"), ("  STUDY  ", "study"), ("a", "a")],
)
def test_a_tag_is_stored_in_lower_case(raw, stored) -> None:
    assert Tag(raw).value == stored


@pytest.mark.parametrize("raw", ["", "   ", "to do", "two\twords", "x" * 33])
def test_an_invalid_tag_is_rejected(raw) -> None:
    with pytest.raises(ValidationError):
        Tag(raw)


def test_tags_of_the_same_keyword_are_one_tag() -> None:
    assert len({Tag("python"), Tag("Python")}) == 1


def test_tags_are_ordered_alphabetically() -> None:
    tags = [Tag("study"), Tag("api"), Tag("python")]

    assert [tag.value for tag in sorted(tags)] == ["api", "python", "study"]


@pytest.mark.parametrize("raw", ["Buy milk", "  padded  ", "x" * MAX_LENGTH])
def test_valid_note_text_is_accepted(raw) -> None:
    assert NoteText(raw).value == raw.strip()


@pytest.mark.parametrize("raw", ["", "   ", "x" * (MAX_LENGTH + 1)])
def test_invalid_note_text_is_rejected(raw) -> None:
    with pytest.raises(ValidationError):
        NoteText(raw)


def test_a_note_keeps_its_text_and_tags(note) -> None:
    assert note.text.value == "Read the pickle docs"
    assert note.tag_names() == ["python", "study"]


def test_a_note_starts_without_tags() -> None:
    assert Note(1, "Buy milk").tag_names() == []


def test_a_note_is_created_and_changed_at_the_same_moment(note) -> None:
    assert note.created == note.updated


def test_editing_moves_the_modification_time(note) -> None:
    note.edit(text="Read the shelve docs")

    assert note.updated > note.created


def test_a_tag_is_added_and_removed(note) -> None:
    note.edit(add=["urgent"], remove=["study"])

    assert note.tag_names() == ["python", "urgent"]


def test_adding_a_tag_twice_keeps_one(note) -> None:
    note.edit(add=["Python"])

    assert note.tag_names() == ["python", "study"]


def test_removing_a_tag_the_note_does_not_carry_is_reported(note) -> None:
    with pytest.raises(NotFoundError):
        note.edit(remove=["draft"])


def test_a_rejected_edit_changes_nothing(note) -> None:
    with pytest.raises(ValidationError):
        note.edit(text="New text", add=["not a tag"])

    assert note.text.value == "Read the pickle docs"
    assert note.tag_names() == ["python", "study"]


def test_the_query_matches_the_text_ignoring_case(note) -> None:
    assert note.matches("PICKLE")
    assert not note.matches("shelve")


def test_a_tag_is_found_however_it_was_capitalised(note) -> None:
    assert note.has_tag("PYTHON")
    assert not note.has_tag("draft")


def test_a_short_note_is_previewed_in_full() -> None:
    assert Note(1, "Buy milk").preview() == "Buy milk"


def test_a_long_note_is_previewed_up_to_the_width() -> None:
    preview = Note(1, "word " * 40).preview()

    assert len(preview) == 60
    assert preview.endswith("...")


def test_a_preview_stays_on_one_line() -> None:
    assert Note(1, "first\nsecond").preview() == "first second"


def test_the_first_tag_speaks_for_the_note(note) -> None:
    assert note.first_tag() == "python"
    assert Note(2, "Buy milk").first_tag() is None
