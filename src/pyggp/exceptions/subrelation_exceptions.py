"""Exceptions regarding subrelations."""
from typing import Optional


class SubrelationError(Exception):
    """Base class for exceptions regarding subrelations."""


class MalformedTreeSubrelationError(SubrelationError):
    """Tree is malformed."""


class ParsingSubrelationError(SubrelationError):
    """Parsing failed."""

    def __init__(self, string: Optional[str] = None) -> None:
        """Initializes ParsingSubrelationError."""
        string_message = f" '{string}'" if string is not None else ""
        super().__init__(f"Failed to parse{string_message}.")
