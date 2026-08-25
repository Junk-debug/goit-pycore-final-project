"""Tests for persistence: requirements P1 and P2."""

from __future__ import annotations

import pickle
from pathlib import Path

import pytest

from personal_assistant.state import AppState
from personal_assistant.storage import DATA_FILE, ENV_DATA_FILE, Storage


@pytest.fixture
def storage(tmp_path):
    """A storage writing into a temporary directory, never the real home."""
    return Storage(tmp_path / "data.pkl")


def test_default_location_is_inside_the_user_home():
    assert DATA_FILE.parent == Path.home() / ".personal_assistant"


def test_loading_without_a_file_returns_an_empty_state(storage):
    assert isinstance(storage.load(), AppState)


def test_saved_state_is_restored(storage):
    state = AppState.empty()
    state.contacts = {"John": "kept"}

    storage.save(state)

    assert storage.load().contacts == {"John": "kept"}


def test_saving_creates_missing_directories(tmp_path):
    storage = Storage(tmp_path / "deep" / "deeper" / "data.pkl")

    storage.save(AppState.empty())

    assert storage.path.exists()


def test_a_corrupted_file_does_not_raise(storage):
    storage.path.write_bytes(b"this is not a pickle")

    assert isinstance(storage.load(), AppState)


def test_a_corrupted_file_is_kept_aside_instead_of_being_lost(storage):
    storage.path.write_bytes(b"this is not a pickle")

    storage.load()

    quarantined = storage.path.with_name(storage.path.name + ".corrupt")
    assert quarantined.read_bytes() == b"this is not a pickle"


def test_a_file_holding_something_else_is_rejected(storage):
    storage.path.write_bytes(pickle.dumps({"unexpected": True}))

    assert isinstance(storage.load(), AppState)


def test_no_temporary_file_is_left_behind(storage):
    storage.save(AppState.empty())

    assert list(storage.path.parent.glob("*.tmp")) == []


def test_the_environment_variable_overrides_the_location(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_DATA_FILE, str(tmp_path / "dev.pkl"))

    assert Storage().path == tmp_path / "dev.pkl"


def test_without_the_variable_the_home_location_is_used(monkeypatch):
    monkeypatch.delenv(ENV_DATA_FILE, raising=False)

    assert Storage().path == DATA_FILE
