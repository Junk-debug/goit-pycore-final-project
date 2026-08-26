"""Tests for the command tree and the two interface modes.

These cover acceptance criteria 8, 10 and 11: the loop runs until an exit
command, and neither an unknown command nor bad input ends the program.
"""

from __future__ import annotations

import pytest
import typer
from typer.core import TyperGroup

from personal_assistant import cli
from personal_assistant.commands import build_app
from personal_assistant.errors import ExitLoop
from personal_assistant.state import AppState


@pytest.fixture
def command() -> TyperGroup:
    built = typer.main.get_command(build_app())
    assert isinstance(built, TyperGroup)
    return built


@pytest.fixture
def state() -> AppState:
    return AppState.empty()


def test_global_commands_are_registered(command) -> None:
    for name in ("help", "exit", "web"):
        assert name in command.commands


def _stub_web(monkeypatch) -> None:
    """Keep 'web' from opening a browser or binding a real port."""
    monkeypatch.setattr("webbrowser.open", lambda url: True)
    monkeypatch.setattr("flask.Flask.run", lambda self, **kwargs: None)


def test_a_known_command_succeeds(command, state, monkeypatch) -> None:
    _stub_web(monkeypatch)
    assert cli.dispatch(command, ["web"], state) == 0


def test_an_unknown_command_is_reported_and_survives(command, state, capsys) -> None:
    assert cli.dispatch(command, ["nonsense"], state) == 2
    assert "No such command" in capsys.readouterr().out


def test_a_mistyped_command_is_answered_with_the_closest_one(
    command, state, capsys
) -> None:
    cli.dispatch(command, ["halp"], state)
    assert "Did you mean 'help'" in capsys.readouterr().out


def test_help_lists_the_commands(command, state, capsys) -> None:
    assert cli.dispatch(command, ["help"], state) == 0
    assert "contact" in capsys.readouterr().out


def test_help_reaches_a_command_by_path(command, state, capsys) -> None:
    assert cli.dispatch(command, ["help", "contact", "add"], state) == 0
    assert "--phone" in capsys.readouterr().out


def test_an_unknown_help_topic_is_reported(command, state) -> None:
    assert cli.dispatch(command, ["help", "nonsense"], state) == 2


@pytest.mark.parametrize("alias", ["exit", "quit", "close"])
def test_every_exit_alias_leaves_the_loop(command, state, alias) -> None:
    with pytest.raises(ExitLoop):
        cli.dispatch(command, [alias], state)


def _feed(monkeypatch, lines) -> None:
    """Make the loop read a fixed list of lines, then report end of input."""
    remaining = list(lines)

    def read() -> str:
        if not remaining:
            raise EOFError
        return str(remaining.pop(0))

    monkeypatch.setattr(cli, "_make_reader", lambda command, state: read)


def test_the_loop_runs_until_the_exit_command(
    command, state, monkeypatch, capsys
) -> None:
    _stub_web(monkeypatch)
    _feed(monkeypatch, ["web", "exit", "web"])

    assert cli.run_loop(command, state) == 0
    printed = capsys.readouterr().out
    assert printed.count("Serving on") == 1
    assert cli.FAREWELL in printed


def test_the_loop_survives_bad_input(command, state, monkeypatch, capsys) -> None:
    _feed(monkeypatch, ["nonsense", 'contact add "John', "", "   ", "exit"])

    assert cli.run_loop(command, state) == 0
    assert cli.FAREWELL in capsys.readouterr().out


def test_the_loop_leaves_on_end_of_input(command, state, monkeypatch, capsys) -> None:
    _feed(monkeypatch, [])

    assert cli.run_loop(command, state) == 0
    assert cli.FAREWELL in capsys.readouterr().out


def test_a_confirmation_prompt_that_cannot_be_answered_declines(monkeypatch) -> None:
    """Regression: EOFError from `console.input` used to leak past typer as
    `Abort`, which our dispatcher did not recognise and re-raised, crashing the
    whole session on Ctrl-D at a y/N prompt (criterion 11)."""
    import sys

    from personal_assistant import ui

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(ui._console, "input", lambda _: (_ for _ in ()).throw(EOFError))

    assert ui.confirm("Delete it?") is False
