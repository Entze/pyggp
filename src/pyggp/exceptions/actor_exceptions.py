"""Exceptions regarding actors."""
from typing import Optional

from pyggp._logging import format_timedelta
from pyggp.interpreters import Move, Role


class ActorError(Exception):
    """Base class for all exceptions regarding actors."""


class PlayclockIsNoneActorError(ActorError):
    """Accessed playclock when it was None."""

    def __init__(self, context: Optional[str] = None) -> None:
        """Initializes ActorPlayclockIsNone.

        Args:
            context: Context in which the playclock was accessed

        """
        context_message = f" during {context}" if context is not None else ""
        message = f"Accessed playclock when it was None{context_message}"
        super().__init__(message)


class TimeoutActorError(ActorError):
    """Gameclock timed out."""

    def __init__(self, delta: Optional[float] = None, available_time: Optional[float] = None) -> None:
        """Initializes ActorTimeoutError.

        Args:
            delta: Seconds elapsed
            available_time: Seconds that were available

        """
        delta_message = f" procedure finished after {format_timedelta(delta)}" if delta is not None else ""
        available_time_message = (
            f" exceeding the available time of {format_timedelta(available_time)}" if available_time is not None else ""
        )
        message = f"Timeout{delta_message}{available_time_message}"
        super().__init__(message)


class IllegalMoveActorError(ActorError):
    """Illegal move was played."""

    def __init__(
        self,
        move: Optional[Move] = None,
        role: Optional[Role] = None,
        ply: Optional[int] = None,
    ) -> None:
        """Initializes ActorIllegalMoveError.

        Args:
            move: Move that was played
            role: Role that played the move
            ply: Ply on which the move was played

        """
        role_message = f" by role {role}" if role is not None else ""
        ply_message = f" on ply {ply}" if ply is not None else ""
        move_message = f" {move}" if move is not None else ""
        message = f"Illegal move{move_message}{role_message}{ply_message}"
        super().__init__(message)


class AgentIsNoneLocalActorError(ActorError):
    """Agent is None."""
