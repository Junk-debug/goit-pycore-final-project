"""Tests for the candidates offered on Tab.

What `prompt_toolkit` draws on the screen is out of scope by D22. What the
assistant proposes is not: the candidates come from the parser, so a wrong
answer here means the interface promises a command it does not have.
"""

from __future__ import annotations

import pytest

pytest.importorskip("prompt_toolkit")

from prompt_toolkit.completion import CompleteEvent  # noqa: E402
from prompt_toolkit.document import Document  # noqa: E402

from personal_assistant.commands import build_parser  # noqa: E402
from personal_assistant.completion import build_completer  # noqa: E402
from personal_assistant.models.note_book import NoteBook  # noqa: E402
from personal_assistant.state import AppState  # noqa: E402


@pytest.fixture
def completer():
    """A completer over the real command tree and two tagged notes."""
    build_parser()
    state = AppState.empty()
    book = state.section(NoteBook)
    book.add("Read the pickle docs", ["study", "python"])
    book.add("Ship the release", ["work"])
    return build_completer(state)


def offered(completer, line) -> list[str]:
    """The candidates the completer proposes for a half-written line."""
    document = Document(line, len(line))
    return [
        completion.text
        for completion in completer.get_completions(document, CompleteEvent())
    ]


def test_the_command_groups_are_proposed_first(completer) -> None:
    assert "note" in offered(completer, "")


def test_an_alias_is_not_proposed_beside_the_command_it_stands_for(completer) -> None:
    proposed = offered(completer, "")

    assert "exit" in proposed
    assert "quit" not in proposed


def test_a_group_proposes_its_own_actions(completer) -> None:
    assert offered(completer, "note ") == ["add", "show", "list", "edit", "delete"]


def test_what_is_typed_narrows_the_proposals(completer) -> None:
    assert offered(completer, "note li") == ["list"]


def test_an_action_proposes_its_options(completer) -> None:
    proposed = offered(completer, "note list ")

    assert "--query" in proposed and "--sort" in proposed


def test_an_option_already_given_is_not_proposed_again(completer) -> None:
    assert "--query" not in offered(completer, "note list --query pickle ")


def test_an_option_that_may_repeat_is_proposed_again(completer) -> None:
    assert "--tag" in offered(completer, 'note add "Buy milk" --tag home ')


def test_the_tags_in_use_are_proposed_as_values(completer) -> None:
    assert offered(completer, "note list --tag ") == ["python", "study", "work"]


def test_a_tag_is_proposed_for_every_option_that_takes_one(completer) -> None:
    assert offered(completer, "note edit 1 --remove-tag stu") == ["study"]


def test_the_topic_of_help_is_completed_as_a_path(completer) -> None:
    assert "note" in offered(completer, "help ")
    assert offered(completer, "help note li") == ["list"]
