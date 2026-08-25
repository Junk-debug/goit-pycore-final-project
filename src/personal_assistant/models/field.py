"""Base class for every validated field of a contact or a note."""

from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class Field(Generic[T]):
    """A single value that is validated the moment it is created.

    Subclasses implement `parse`, which receives the raw text entered by the
    user and returns the value to store, or raises `ValidationError`. Because
    that is the only way to build a field, an existing instance is always
    valid, and validation lives in exactly one place per field as required by
    acceptance criterion 13.
    """

    def __init__(self, raw: str) -> None:
        self.value: T = self.parse(str(raw).strip())

    def parse(self, raw: str) -> T:
        """Validate the raw input and return the value to store."""
        raise NotImplementedError

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Field):
            return type(self) is type(other) and self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash((type(self), self.value))
