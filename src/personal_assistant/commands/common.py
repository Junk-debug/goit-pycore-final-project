"""Commands that belong to no entity: help, exit and the web interface."""

from __future__ import annotations

import argparse
from typing import Any

from personal_assistant.errors import CommandError, ExitLoop
from personal_assistant.state import AppState


def register(groups: argparse._SubParsersAction) -> None:
    """Add the global commands to the command tree."""
    help_parser = groups.add_parser("help", help="show the available commands")
    help_parser.add_argument(
        "topic", nargs="?", metavar="<command>", help="show the help of one command"
    )
    help_parser.set_defaults(handler=show_help)

    exit_parser = groups.add_parser(
        "exit", aliases=["quit", "close"], help="leave the interactive session"
    )
    exit_parser.set_defaults(handler=leave)

    web_parser = groups.add_parser("web", help="start the web interface")
    web_parser.set_defaults(handler=start_web)


def show_help(args: argparse.Namespace, state: AppState) -> Any:
    """Print the whole command tree, or the help of one command."""
    from personal_assistant import commands

    if args.topic is None:
        return commands.root_parser().format_help().rstrip()

    parser = commands.group_parser(args.topic)
    if parser is None:
        known = ", ".join(commands.group_names())
        raise CommandError(f"Unknown command '{args.topic}'. Available: {known}.")
    return parser.format_help().rstrip()


def leave(args: argparse.Namespace, state: AppState) -> Any:
    """Leave the interactive session; data is saved by the caller."""
    raise ExitLoop


def start_web(args: argparse.Namespace, state: AppState) -> Any:
    """Start the web interface once it exists (D8)."""
    return "The web interface is not implemented yet."
