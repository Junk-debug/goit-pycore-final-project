"""Assembly of the command tree and the registry of command groups.

Every group lives in its own module and exposes a single function:

    def register(subparsers) -> None

It adds its own sub-parsers there and attaches a handler to each of them with
`set_defaults(handler=...)`. A group therefore never edits a shared file, which
keeps the developers of different groups out of each other's way.

A handler has the signature

    handler(args: argparse.Namespace, state: AppState) -> Renderable

and returns what should be shown, or None. Handlers never print: the value
they return is rendered by `personal_assistant.ui`, so the same handlers can
later serve the web interface (D8).
"""

from __future__ import annotations

import argparse
import importlib
from types import ModuleType

from personal_assistant.parser import ReplArgumentParser
from personal_assistant.types import SubParsers

GROUP_MODULES = ("common", "contacts", "notes")

_root: ReplArgumentParser | None = None
_groups: SubParsers | None = None

DESCRIPTION = "Personal assistant: an address book and notes."
EPILOG = "Run without arguments to start the interactive session."


def _load(name: str) -> ModuleType | None:
    """Import a group module, or return None while it does not exist yet."""
    try:
        return importlib.import_module(f"personal_assistant.commands.{name}")
    except ImportError:
        return None


def build_parser() -> ReplArgumentParser:
    """Build the parser shared by the loop and the single-command mode."""
    global _root, _groups

    parser = ReplArgumentParser(
        prog="assistant", description=DESCRIPTION, epilog=EPILOG
    )
    groups = parser.add_subparsers(dest="entity", metavar="<command>")

    for name in GROUP_MODULES:
        module = _load(name)
        if module is not None:
            module.register(groups)

    _root, _groups = parser, groups
    return parser


def root_parser() -> ReplArgumentParser:
    """Return the parser built last, building one if needed."""
    return _root if _root is not None else build_parser()


def group_names() -> list[str]:
    """Names of every registered top-level command, in registration order."""
    return list(_groups.choices) if _groups is not None else []


def group_parser(name: str) -> argparse.ArgumentParser | None:
    """Return the parser of one top-level command, or None if unknown."""
    if _groups is None:
        return None
    return _groups.choices.get(name)
