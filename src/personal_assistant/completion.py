"""Tab completion for the interactive session.

The candidates are read from the command tree the assistant was built from,
never from a list kept beside it. A group that adds a command therefore gets
completion for it for free, and the proposals cannot drift away from what the
assistant actually accepts, which is what makes them worth offering at all
(criterion 7).

`prompt_toolkit` is optional: importing this module fails when it is
missing, and the interactive session then reads plain lines instead.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from typing import TypeAlias

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from typer.core import TyperCommand, TyperGroup, TyperOption

from personal_assistant.models.note_book import NoteBook
from personal_assistant.state import AppState

# Every command in the tree is one of these two: typer builds a group for
# each `add_typer` and a command for each function below it.
AnyCommand: TypeAlias = "TyperCommand | TyperGroup"

LONG_OPTION = "--"

# The topic of `help` is a path through the command tree rather than a value
# of its own, so completing it is completing that path once more.
HELP = "help"


def known_tags(state: AppState) -> Sequence[str]:
    """The tags already in use, so `--tag` proposes real ones."""
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

    def __init__(self, root: TyperGroup, state: AppState) -> None:
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

        command, rest = self._walk(given)
        if not rest:
            below = _commands_below(command)
            if below:
                return below
        elif rest[-1] in VALUE_SOURCES:
            return [(value, "") for value in VALUE_SOURCES[rest[-1]](self.state)]
        return _options_of(command, rest)

    def _walk(self, given: Sequence[str]) -> tuple[AnyCommand, Sequence[str]]:
        """Descend the command tree as far as the entered words reach."""
        command: AnyCommand = self.root
        rest = list(given)
        while rest:
            below = _named(command, rest[0])
            if below is None:
                break
            command, rest = below, rest[1:]
        return command, rest


def build_completer(root: TyperGroup, state: AppState) -> Completer:
    return CommandCompleter(root, state)


def _named(command: AnyCommand, name: str) -> AnyCommand | None:
    """The command registered under that name, when one command holds others."""
    if not isinstance(command, TyperGroup):
        return None
    below = command.commands.get(name)
    return below if isinstance(below, TyperCommand | TyperGroup) else None


def _commands_below(command: AnyCommand) -> list[tuple[str, str]]:
    """The commands directly below this one, with their descriptions.

    A hidden command is left out, which is how the `quit` and `close` aliases
    stay out of the proposals without this file having to know they exist.
    """
    if not isinstance(command, TyperGroup):
        return []
    return [
        (name, below.get_short_help_str())
        for name, below in command.commands.items()
        if not below.hidden
    ]


def _options_of(command: AnyCommand, given: Sequence[str]) -> list[tuple[str, str]]:
    """The options this command still accepts, with their help text.

    `--help` is not in `command.params`: click attaches it lazily through
    `get_params`, on a context, rather than declaring it as a regular option.
    Building that context is how the same completions include it too.
    """
    offered: list[tuple[str, str]] = []
    context = command.make_context(command.name or "", [], resilient_parsing=True)
    for parameter in command.get_params(context):
        if not isinstance(parameter, TyperOption) or parameter.hidden:
            continue
        names = [name for name in parameter.opts if name.startswith(LONG_OPTION)]
        if not names or (not parameter.multiple and _already_given(names, given)):
            continue
        offered.extend((name, parameter.help or "") for name in names)
    return offered


def _already_given(names: Sequence[str], given: Sequence[str]) -> bool:
    """Whether an option is spent, and so not worth proposing again."""
    return any(name in given for name in names)
