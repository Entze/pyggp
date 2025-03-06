"""Exceptions regarding gameclocks."""

from typing import Optional


class GameClockError(Exception):
    """Base exception for game clocks."""


class GameClockConfigurationError(GameClockError):
    """Exception for game clock configuration."""


class MalformedStringGameClockConfigurationError(GameClockConfigurationError):
    """Tried to parse a malformed game clock configuration string."""

    def __init__(self, /, reason: Optional[str] = None, string: Optional[str] = None) -> None:
        """Initializes MalformedStringGameClockConfigurationError.

        Args:
            reason: Additional information about the reason for the error.
            string: The malformed string.

        """
        reason_message = f"({reason})" if reason is not None else ""
        string_message = f" '{string}'" if string is not None else ""

        super().__init__(f"Malformed game clock configuration string{reason_message}{string_message}")


class MissingTotalTimeGameClockConfigurationError(MalformedStringGameClockConfigurationError):
    """Tried to parse a game clock configuration string without total time."""

    def __init__(self, string: Optional[str] = None) -> None:
        """Initializes MissingTotalTimeGameClockConfigurationError.

        Args:
            string: The malformed string.

        """
        super().__init__(reason="total_time missing", string=string)


class TotalTimeInvalidFloatGameClockConfigurationError(MalformedStringGameClockConfigurationError):
    """Tried to parse a game clock configuration string with an invalid total time."""

    def __init__(self, string: Optional[str] = None) -> None:
        """Initializes TotalTimeNotInvalidFloatGameClockConfigurationError.

        Args:
            string: The malformed string.

        """
        super().__init__(reason="total_time not a float", string=string)


class IncrementInvalidFloatGameClockConfigurationError(MalformedStringGameClockConfigurationError):
    """Tried to parse a game clock configuration string with an invalid increment."""

    def __init__(self, string: Optional[str] = None) -> None:
        """Initializes IncrementInvalidFloatGameClockConfigurationError.

        Args:
            string: The malformed string.

        """
        super().__init__(reason="increment not a float", string=string)


class DelayInvalidFloatGameClockConfigurationError(MalformedStringGameClockConfigurationError):
    """Tried to parse a game clock configuration string with an invalid delay."""

    def __init__(self, string: Optional[str] = None) -> None:
        """Initializes DelayInvalidFloatGameClockConfigurationError.

        Args:
            string: The malformed string.

        """
        super().__init__(reason="delay not a float", string=string)
