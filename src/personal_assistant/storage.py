"""Persistence of the application state.

The whole state is serialised with pickle into a single file inside the user's
home directory, as decided in D11 and required by P1. The working directory is
deliberately not used: the command is callable from anywhere, so it is not a
stable location.
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path

from personal_assistant.state import AppState

DATA_DIR = Path.home() / ".personal_assistant"
DATA_FILE = DATA_DIR / "data.pkl"


class Storage:
    """Reads and writes the application state as one pickle file."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else DATA_FILE

    def load(self) -> AppState:
        """Return the stored state, or an empty one when it cannot be read.

        A file that cannot be unpickled is moved aside rather than deleted, so
        that a user never silently loses data, and the assistant starts from an
        empty state instead of crashing.
        """
        try:
            with self.path.open("rb") as handle:
                state = pickle.load(handle)
        except FileNotFoundError:
            return AppState.empty()
        except Exception:
            # Unpickling a damaged file raises almost anything, so the guard
            # is intentionally broad.
            self._quarantine()
            return AppState.empty()

        if not isinstance(state, AppState):
            self._quarantine()
            return AppState.empty()
        return state

    def save(self, state: AppState) -> None:
        """Write the state, replacing the previous file atomically.

        The data is written to a temporary file first and moved into place
        afterwards, so an interruption cannot leave a half-written file behind.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        with temporary.open("wb") as handle:
            pickle.dump(state, handle)
        os.replace(temporary, self.path)

    def _quarantine(self) -> None:
        """Move an unreadable file aside so that it is not overwritten."""
        try:
            os.replace(self.path, self.path.with_name(self.path.name + ".corrupt"))
        except OSError:
            pass
