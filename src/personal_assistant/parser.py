"""The argument parser shared by both interface modes.

One parser is built once and serves the single-command mode and the
interactive loop alike, so the two can never drift apart (D5, D21).
"""

from __future__ import annotations

import argparse
from typing import NoReturn

from personal_assistant.errors import CommandError


class ReplArgumentParser(argparse.ArgumentParser):
    """An argument parser that reports errors instead of ending the process.

    `argparse` is written for one-shot programs: a bad argument makes it print
    a message and call `sys.exit`. Inside the interactive loop that would close
    the assistant on a typo, which acceptance criterion 11 forbids. Both exit
    paths are therefore turned into exceptions the loop can catch.
    """

    def error(self, message: str) -> NoReturn:
        """Raise instead of terminating, keeping the usage line in the text."""
        raise CommandError(f"{message}\n\n{self.format_usage().strip()}")

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        """Raise instead of terminating.

        Reached when `--help` has already printed its output, so the message is
        empty and the loop simply continues.
        """
        raise CommandError(message.strip() if message else "")
