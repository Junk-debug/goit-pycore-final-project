"""Entry point of the command-line interface.

Two modes share one parser and one set of handlers, as decided in D5:

    assistant                       the interactive loop, the default
    assistant contact add John      a single command, then exit

The only difference between them is where the words come from: the loop splits
a line read from the keyboard, the single-command mode takes `sys.argv`.
"""

from __future__ import annotations

import shlex
import sys
from collections.abc import Callable

from personal_assistant import ui
from personal_assistant.commands import build_parser
from personal_assistant.errors import AssistantError, CommandError, ExitLoop
from personal_assistant.parser import ReplArgumentParser
from personal_assistant.state import AppState
from personal_assistant.storage import Storage

PROMPT = "assistant> "
WELCOME = "Personal assistant. Type 'help' to see the commands, 'exit' to leave."
FAREWELL = "Good bye!"


def dispatch(parser: ReplArgumentParser, argv: list[str], state: AppState) -> int:
    """Run one command and show its result. Returns a process exit code.

    Every expected failure is reported as a message, so neither an invalid
    command nor invalid data ends the program (criterion 11).
    """
    try:
        args = parser.parse_args(argv)
    except CommandError as error:
        message = str(error)
        if not message:
            # `--help` has already printed its output and asked to exit.
            return 0
        ui.failure(message)
        return 2

    handler: Callable | None = getattr(args, "handler", None)
    if handler is None:
        ui.failure(parser.format_usage().strip())
        return 2

    try:
        ui.render(handler(args, state))
    except AssistantError as error:
        ui.failure(str(error))
        return 1
    return 0


def _make_reader() -> Callable[[], str]:
    """Return a function that reads one line from the user.

    Uses `prompt_toolkit` for completion and history when it is installed and
    the input really comes from a terminal, and falls back to `input` in every
    other case, per D21. The terminal check matters when the commands are piped
    in, which is how the tests and any scripted demo drive the assistant.
    """
    if not sys.stdin.isatty():
        return lambda: input()

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
    except ImportError:
        return lambda: input(PROMPT)

    completer = None
    try:
        from personal_assistant.completion import build_completer

        completer = build_completer()
    except ImportError:
        pass

    session = PromptSession(history=InMemoryHistory(), completer=completer)
    return lambda: session.prompt(PROMPT)


def run_loop(parser: ReplArgumentParser, state: AppState) -> int:
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
            dispatch(parser, argv, state)
        except ExitLoop:
            break

    ui.render(FAREWELL)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the assistant and return a process exit code."""
    parser = build_parser()
    words = list(sys.argv[1:] if argv is None else argv)

    storage = Storage()
    state = storage.load()
    try:
        if words:
            try:
                return dispatch(parser, words, state)
            except ExitLoop:
                return 0
        return run_loop(parser, state)
    finally:
        storage.save(state)


if __name__ == "__main__":
    sys.exit(main())
