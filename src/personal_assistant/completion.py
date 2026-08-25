"""Tab completion for the interactive session.

The candidates are read from the parser that the commands were registered in,
never from a list kept beside it. A group that adds a command therefore gets
completion for it for free, and the proposals cannot drift away from what the
assistant actually accepts, which is what makes them worth offering at all
(criterion 7).

`prompt_toolkit` is optional by D21: importing this module fails when it is
missing, and the interactive session then reads plain lines instead.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator, Sequence

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from personal_assistant import commands
from personal_assistant.models.note_book import NoteBook
from personal_assistant.parser import ReplArgumentParser
from personal_assistant.state import AppState

LONG_OPTION = "--"

# The topic of `help` is a path through the command tree rather than a value
# of its own (D25), so completing it is completing that path once more.
HELP = "help"


def known_tags(state: AppState) -> Sequence[str]:
    """The tags already in use, so `--tag` proposes real ones (T2, T3)."""
    return state.section(NoteBook).tags()


# Options whose value is worth proposing, and where those values come from.
# A group extends this with its own option and its own source.
VALUE_SOURCES: dict[str, Callable[[AppState], Sequence[str]]] = {
    "--tag": known_tags,
    "--add-tag": known_tags,
    "--remove-tag": known_tags,
}


class CommandCompleter(Completer):
    """Proposes the command, the option or the value that fits what is typed.

    Which of the three it is follows from the position in the line: the first
    words name a command as long as they match one, what comes after it is
    made of options, and the word after an option is its value.
    """

    def __init__(self, root: ReplArgumentParser, state: AppState) -> None:
        self.root = root
        self.state = state

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterator[Completion]:
        """Answer one request for completions from `prompt_toolkit`."""
        typed = document.text_before_cursor
        words = typed.split()
        started = bool(words) and not typed[-1].isspace()
        fragment = words[-1] if started else ""
        given = words[:-1] if started else words

        for value, description in self.candidates(given):
            if value.lower().startswith(fragment.lower()):
                yield Completion(
                    value, start_position=-len(fragment), display_meta=description
                )

    def candidates(self, given: Sequence[str]) -> list[tuple[str, str]]:
        """What may follow the words already entered, each with its help."""
        if given and given[0] == HELP:
            return self.candidates(given[1:])

        parser, rest = self._walk(given)
        if not rest:
            below = _commands_below(parser)
            if below:
                return below
        elif rest[-1] in VALUE_SOURCES:
            return [(value, "") for value in VALUE_SOURCES[rest[-1]](self.state)]
        return _options_of(parser, rest)

    def _walk(
        self, given: Sequence[str]
    ) -> tuple[argparse.ArgumentParser, Sequence[str]]:
        """Descend the command tree as far as the entered words reach."""
        parser: argparse.ArgumentParser = self.root
        rest = list(given)
        while rest:
            below = (
                parser.child(rest[0])
                if isinstance(parser, ReplArgumentParser)
                else None
            )
            if below is None:
                break
            parser, rest = below, rest[1:]
        return parser, rest


def build_completer(state: AppState) -> Completer:
    """The completer the interactive session installs (D21)."""
    return CommandCompleter(commands.root_parser(), state)


def _commands_below(parser: argparse.ArgumentParser) -> list[tuple[str, str]]:
    """The commands directly below this one, with their descriptions.

    An alias shares the parser of the command it stands for, so keeping one
    name per parser leaves `quit` and `close` out of the proposals without
    this file having to know that they exist.
    """
    found: dict[int, tuple[str, str]] = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, below in action.choices.items():
                found.setdefault(id(below), (name, below.description or ""))
    return list(found.values())


def _options_of(
    parser: argparse.ArgumentParser, given: Sequence[str]
) -> list[tuple[str, str]]:
    """The options this command still accepts, with their help text."""
    offered: list[tuple[str, str]] = []
    for action in parser._actions:
        names = [name for name in action.option_strings if name.startswith(LONG_OPTION)]
        if not names or (_once_only(action) and any(name in given for name in names)):
            continue
        offered.extend((name, action.help or "") for name in names)
    return offered


def _once_only(action: argparse.Action) -> bool:
    """Whether the option is spent once given, and not worth proposing again."""
    return not isinstance(action, argparse._AppendAction)
