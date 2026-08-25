"""Entry point of the command-line interface.

Two modes share one application and one set of commands, as decided in D5:

    assistant                       the interactive loop, the default
    assistant contact add John      a single command, then exit

The only difference between them is where the words come from: the loop splits
a line read from the keyboard, the single-command mode takes `sys.argv`.
"""

from __future__ import annotations

import shlex
import sys
from collections.abc import Callable

import typer
from typer.core import TyperGroup

from personal_assistant import ui
from personal_assistant.commands import build_app
from personal_assistant.commands.common import ShowHelp
from personal_assistant.errors import AssistantError, ExitLoop
from personal_assistant.state import AppState
from personal_assistant.storage import Storage

PROMPT = "assistant> "
# Bold cyan, reset after: the same escape sequence works whether it reaches
# the terminal through the plain `input` fallback or through prompt_toolkit,
# which renders raw ANSI codes wrapped in `ANSI(...)` as-is.
PROMPT_DISPLAY = f"\033[1;36m{PROMPT}\033[0m"
WELCOME = "Personal assistant. Type 'help' to see the commands, 'exit' to leave."
FAREWELL = "Good bye!"
PROGRAM = "assistant"


def dispatch(command: TyperGroup, argv: list[str], state: AppState) -> int:
    """Run one command and show its result. Returns a process exit code.

    Every expected failure is reported as a message, so neither an unknown
    command nor invalid data ends the program (criterion 11).
    """
    try:
        command.main(args=argv, standalone_mode=False, prog_name=PROGRAM, obj=state)
    except ExitLoop:
        raise
    except ShowHelp as asked:
        return dispatch(command, [*asked.topic, "--help"], state)
    except AssistantError as error:
        ui.failure(str(error))
        return 1
    except typer.Exit as leaving:
        return int(leaving.exit_code)
    except Exception as error:
        # Typer reports a parse error this way; anything else is a real defect
        # and must not be swallowed.
        reported = getattr(error, "format_message", None)
        if reported is None:
            raise
        ui.failure(reported())
        return 2
    return 0


def _make_reader() -> Callable[[], str]:
    """Return a function that reads one line from the user.

    Uses `prompt_toolkit` for completion and history when it is installed and
    the input really comes from a terminal, and falls back to `input` in every
    other case, per D21. The terminal check matters when the commands are piped
    in, which is how the tests and any scripted demo drive the assistant.
    """
    if not sys.stdin.isatty():
        return input

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
    except ImportError:
        return lambda: input(PROMPT_DISPLAY)

    from prompt_toolkit.formatted_text import ANSI

    session: PromptSession[str] = PromptSession(history=InMemoryHistory())
    return lambda: session.prompt(ANSI(PROMPT_DISPLAY))


def run_loop(command: TyperGroup, state: AppState) -> int:
    """Read commands until the user leaves (criterion 8)."""
    read = _make_reader()
    ui.render(WELCOME)

    while True:
        try:
            line = read()
        except (EOFError, KeyboardInterrupt):
            break

        if not line.strip():
            continue

        try:
            argv = shlex.split(line)
        except ValueError as error:
            ui.failure(f"Could not read the command: {error}")
            continue

        try:
            dispatch(command, argv, state)
        except ExitLoop:
            break

    ui.render(FAREWELL)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the assistant and return a process exit code."""
    command = typer.main.get_command(build_app())
    # The app is always a tree of groups, never a single bare command.
    assert isinstance(command, TyperGroup)
    words = list(sys.argv[1:] if argv is None else argv)

    storage = Storage()
    state = storage.load()
    try:
        if words:
            try:
                return dispatch(command, words, state)
            except ExitLoop:
                return 0
        return run_loop(command, state)
    finally:
        storage.save(state)


if __name__ == "__main__":
    sys.exit(main())
