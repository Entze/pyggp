"""Exceptions regarding matches."""
from typing import Optional

from pyggp.actors import Actor
from pyggp.interpreters import Move, Role


class MatchError(Exception):
    """Base class for all exceptions regarding matches."""


class AbortedMatchError(MatchError):
    """Base class for all exceptions regarding aborted matches."""


class DidNotStartMatchError(AbortedMatchError):
    """Match did not start."""

    def __init__(self, *, actor: Optional[Actor], role: Optional[Role] = None) -> None:
        """Initializes DidNotStartMatchError.

        Args:
            actor: Actor that caused the match to not start
            role: Role inhabited by actor that caused the match to not start

        """
        role_message = f" caused by role {role}" if role is not None else ""
        actor_message = f" caused by actor {actor}" if actor is not None else ""
        message = f"Match did not start{actor_message}{role_message}"
        super().__init__(message)


class DidNotFinishMatchError(AbortedMatchError):
    """Match did not finish."""

    def __init__(
        self,
        *,
        actor: Optional[Actor] = None,
        ply: Optional[int] = None,
        reason: Optional[str] = None,
        role: Optional[Role] = None,
    ) -> None:
        """Initializes DidNotFinishMatchError.

        Args:
            actor: Actor that caused the match to not finish
            ply: Current ply
            reason: Reason why the match did not finish
            role: Role inhabited by actor that caused the match to not finish

        """
        ply_message = f" during ply {ply}" if ply is not None else ""
        actor_message = f" caused by actor {actor}" if actor is not None else ""
        reason_message = f" because {reason}" if reason is not None else ""
        role_message = f" caused by role {role}" if role is not None else ""
        message = f"Match did not finish{reason_message}{ply_message}{actor_message}{role_message}"
        super().__init__(message)


class TimeoutMatchError(DidNotFinishMatchError):
    """Match timed out."""

    def __init__(
        self,
        *,
        actor: Optional[Actor] = None,
        ply: Optional[int] = None,
        role: Optional[Role] = None,
    ) -> None:
        """Initializes MatchTimeoutError.

        Args:
            actor: Actor that caused the match to time out
            ply: Current ply
            role: Role inhabited by actor that caused the match to time out

        """
        super().__init__(actor=actor, ply=ply, reason="timeout", role=role)


class IllegalMoveMatchError(DidNotFinishMatchError):
    """Illegal move attempted to be played."""

    def __init__(
        self,
        *,
        actor: Optional[Actor] = None,
        move: Optional[Move] = None,
        ply: Optional[int] = None,
        role: Optional[Role] = None,
    ) -> None:
        """Initializes IllegalMoveMatchError.

        Args:
            actor: Actor that attempted to play the illegal move
            move: Illegal move
            ply: Current ply
            role: Role inhabited by actor that attempted to play the illegal move

        """
        super().__init__(actor=actor, ply=ply, reason=f"illegal move({move})", role=role)
