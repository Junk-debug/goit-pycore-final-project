"""Tests for the shared parser and the two interface modes.

These cover acceptance criteria 8, 10 and 11: the loop runs until an exit
command, and neither an unknown command nor bad input ends the program.
"""

from __future__ import annotations

import pytest

from personal_assistant import cli
from personal_assistant.commands import build_parser, group_names
from personal_assistant.errors import CommandError, ExitLoop
from personal_assistant.parser import ReplArgumentParser
from personal_assistant.state import AppState


@pytest.fixture
def parser() -> ReplArgumentParser:
    return build_parser()


@pytest.fixture
def state() -> AppState:
    return AppState.empty()


def test_global_commands_are_registered(parser) -> None:
    for name in ("help", "exit", "web"):
        assert name in group_names()


def test_a_parse_error_is_raised_instead_of_exiting(parser) -> None:
    with pytest.raises(CommandError):
        parser.parse_args(["nonsense"])


def test_help_is_raised_instead_of_exiting(parser, capsys) -> None:
    with pytest.raises(CommandError):
        parser.parse_args(["--help"])


def test_an_unknown_command_is_reported_and_survives(parser, state) -> None:
    assert cli.dispatch(parser, ["nonsense"], state) == 2


def test_a_known_command_succeeds(parser, state) -> None:
    assert cli.dispatch(parser, ["web"], state) == 0


def test_help_of_one_command_is_shown(parser, state, capsys) -> None:
    assert cli.dispatch(parser, ["help", "web"], state) == 0
    assert "web" in capsys.readouterr().out


def test_help_of_an_unknown_command_is_reported(parser, state) -> None:
    assert cli.dispatch(parser, ["help", "nonsense"], state) == 1


def test_exit_leaves_the_loop(parser, state) -> None:
    with pytest.raises(ExitLoop):
        cli.dispatch(parser, ["exit"], state)


@pytest.mark.parametrize("alias", ["exit", "quit", "close"])
def test_every_exit_alias_leaves_the_loop(parser, state, alias) -> None:
    with pytest.raises(ExitLoop):
        cli.dispatch(parser, [alias], state)


def _feed(monkeypatch, lines) -> None:
    """Make the loop read a fixed list of lines, then report end of input."""
    remaining = list(lines)

    def read():
        if not remaining:
            raise EOFError
        return remaining.pop(0)

    monkeypatch.setattr(cli, "_make_reader", lambda: read)


def test_the_loop_runs_until_the_exit_command(
    parser, state, monkeypatch, capsys
) -> None:
    _feed(monkeypatch, ["web", "exit", "web"])

    assert cli.run_loop(parser, state) == 0
    output = capsys.readouterr().out
    assert output.count("not implemented yet") == 1
    assert cli.FAREWELL in output


def test_the_loop_survives_bad_input(parser, state, monkeypatch, capsys) -> None:
    _feed(monkeypatch, ["nonsense", 'contact add "John', "", "   ", "exit"])

    assert cli.run_loop(parser, state) == 0
    assert cli.FAREWELL in capsys.readouterr().out


def test_the_loop_leaves_on_end_of_input(parser, state, monkeypatch, capsys) -> None:
    _feed(monkeypatch, [])

    assert cli.run_loop(parser, state) == 0
    assert cli.FAREWELL in capsys.readouterr().out


@pytest.mark.parametrize(
    ("mistyped", "expected"),
    [("halp", "help"), ("exti", "exit"), ("wbe", "web")],
)
def test_a_mistyped_command_is_answered_with_the_closest_one(
    parser, mistyped, expected
) -> None:
    with pytest.raises(CommandError) as reported:
        parser.parse_args([mistyped])

    assert f"Did you mean '{expected}'" in str(reported.value)


def test_nothing_is_proposed_for_an_unrecognisable_command(parser) -> None:
    with pytest.raises(CommandError) as reported:
        parser.parse_args(["zzzzzzzz"])

    assert "Did you mean" not in str(reported.value)


def test_help_of_one_command_shows_its_own_arguments(parser, state, capsys) -> None:
    assert cli.dispatch(parser, ["help", "help"], state) == 0
    assert "<command>" in capsys.readouterr().out


def test_an_unknown_step_in_a_help_path_is_reported(parser, state) -> None:
    assert cli.dispatch(parser, ["help", "web", "nope"], state) == 1
