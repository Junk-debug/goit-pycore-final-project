"""The argument parser shared by both interface modes.

One parser is built once and serves the single-command mode and the
interactive loop alike, so the two can never drift apart (D5, D21).
"""

from __future__ import annotations

import argparse
import difflib
import re
from typing import NoReturn

from personal_assistant.errors import CommandError

INVALID_CHOICE = re.compile(r"invalid choice: '([^']*)'")
SIMILARITY = 0.5


class ReplArgumentParser(argparse.ArgumentParser):
    """An argument parser that reports errors instead of ending the process.

    `argparse` is written for one-shot programs: a bad argument makes it print
    a message and call `sys.exit`. Inside the interactive loop that would close
    the assistant on a typo, which acceptance criterion 11 forbids. Both exit
    paths are therefore turned into exceptions the loop can catch.
    """

    def error(self, message: str) -> NoReturn:
        """Raise instead of terminating, keeping the usage line in the text."""
        raise CommandError(
            f"{message}{self._suggestion(message)}\n\n{self.format_usage().strip()}"
        )

    def _suggestion(self, message: str) -> str:
        """Propose the closest known command when an unknown one was typed."""
        mistyped = INVALID_CHOICE.search(message)
        if mistyped is None:
            return ""

        close = difflib.get_close_matches(
            mistyped.group(1), self._known_commands(), n=1, cutoff=SIMILARITY
        )
        return f"\n\nDid you mean '{close[0]}'?" if close else ""

    def _known_commands(self) -> list[str]:
        """The commands this parser accepts at its own level."""
        choices = self._choices()
        return list(choices) if choices else []

    def child(self, name: str) -> argparse.ArgumentParser | None:
        """Return the parser of one command below this one, or None."""
        choices = self._choices()
        return choices.get(name) if choices else None

    def _choices(self) -> dict[str, argparse.ArgumentParser] | None:
        for action in self._actions:
            if isinstance(action, argparse._SubParsersAction):
                return action.choices
        return None

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        """Raise instead of terminating.

        Reached when `--help` has already printed its output, so the message is
        empty and the loop simply continues.
        """
        raise CommandError(message.strip() if message else "")
