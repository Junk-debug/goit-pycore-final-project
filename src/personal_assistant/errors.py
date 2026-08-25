"""Exceptions the assistant reports to the user.

Everything raised from this module is expected: it describes invalid input or
a missing contact. Such an error is turned into a message and never terminates
the program, as required by acceptance criterion 11.
"""


class AssistantError(Exception):
    """Base class for every error that is shown to the user as a message."""


class ValidationError(AssistantError):
    """A value does not satisfy the validation rule of its field."""


class NotFoundError(AssistantError):
    """The requested contact does not exist."""


class CommandError(AssistantError):
    """A command was invoked incorrectly."""


class ExitLoop(Exception):
    """Raised by the exit command to leave the interactive loop.

    Not an `AssistantError`: leaving is a normal outcome, not a failure.
    """
