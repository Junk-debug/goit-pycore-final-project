"""Commands that belong to no entity: help, exit and the web interface."""

from __future__ import annotations

import argparse

from personal_assistant.errors import CommandError, ExitLoop
from personal_assistant.parser import ReplArgumentParser
from personal_assistant.state import AppState
from personal_assistant.types import Renderable, SubParsers


def register(groups: SubParsers) -> None:
    """Add the global commands to the command tree."""
    help_parser = groups.add_parser("help", help="show the available commands")
    help_parser.add_argument(
        "topic",
        nargs="*",
        metavar="<command>",
        help="show the help of one command, for example 'help contact add'",
    )
    help_parser.set_defaults(handler=show_help)

    exit_parser = groups.add_parser(
        "exit", aliases=["quit", "close"], help="leave the interactive session"
    )
    exit_parser.set_defaults(handler=leave)

    web_parser = groups.add_parser("web", help="start the web interface")
    web_parser.set_defaults(handler=start_web)


def show_help(args: argparse.Namespace, state: AppState) -> Renderable:
    """Print the whole command tree, or the help of one command.

    The topic is a path, so `help contact add` reaches an action and shows the
    options it accepts, which the group listing only names.
    """
    from personal_assistant import commands

    parser: argparse.ArgumentParser = commands.root_parser()
    walked: list[str] = []

    for step in args.topic:
        child = parser.child(step) if isinstance(parser, ReplArgumentParser) else None
        if child is None:
            place = " ".join(walked) or "the assistant"
            raise CommandError(f"'{step}' is not a command of {place}.")
        parser = child
        walked.append(step)

    return parser.format_help().rstrip()


def leave(args: argparse.Namespace, state: AppState) -> Renderable:
    """Leave the interactive session; data is saved by the caller."""
    raise ExitLoop


def start_web(args: argparse.Namespace, state: AppState) -> Renderable:
    """Start the web interface once it exists (D8)."""
    return "The web interface is not implemented yet."
