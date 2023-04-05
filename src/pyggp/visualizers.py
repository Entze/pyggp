"""Visualizers for consecutive states."""
import abc
from dataclasses import dataclass, field
from typing import MutableSequence, Optional

from rich import print

from pyggp.interpreters import State


@dataclass
class Visualizer(abc.ABC):
    """Base class for visualizers."""

    _states: MutableSequence[Optional[State]] = field(default_factory=list, repr=False)

    def update_state(self, state: State, ply: Optional[int] = None) -> None:
        """Update a state.

        If ply is None, it is assumed to be the next ply.

        Args:
            state: State to update
            ply: Ply to update

        """
        if ply is None:
            self._states.append(state)
            return
        if ply >= len(self._states):
            self._states.extend([None] * ((ply + 1) - len(self._states)))

        self._states[ply] = state

    # def update_result(self, result: MatchResult) -> None:
    #    raise NotImplementedError

    def update_abort(self) -> None:
        """Indicate to the visualizer that the match has been aborted."""
        raise NotImplementedError

    def draw(self) -> None:
        """Draw new information."""
        raise NotImplementedError


@dataclass
class NullVisualizer(Visualizer):  # pragma: no cover
    """Visualizer that does nothing."""

    def update_state(self, state: State, ply: Optional[int] = None) -> None:
        """Update a state.

        If ply is None, it is assumed to be the next ply.

        Args:
        state: State to update
        ply: Ply to update

        """

    # def update_result(self, result: MatchResult) -> None:
    #    pass

    def update_abort(self) -> None:
        """Indicate to the visualizer that the match has been aborted."""

    def draw(self) -> None:
        """Draw new information."""


@dataclass
class SimpleVisualizer(Visualizer):
    """Visualizer that dumps states to stdout."""

    _last_drawn_ply: int = field(default=-1, repr=False)
    _aborted: bool = field(default=False, repr=False)

    # def update_result(self, result: MatchResult) -> None:
    #    pass

    def update_abort(self) -> None:
        """Indicate to the visualizer that the match has been aborted."""
        self._aborted = True

    def draw(self) -> None:
        """Draw new information."""
        for ply in range(self._last_drawn_ply + 1, len(self._states)):
            self._draw_ply(ply)
            self._last_drawn_ply = ply

        if self._aborted:
            print("Match aborted")

    def _draw_ply(self, ply: int) -> None:
        if ply >= len(self._states) or self._states[ply] is None:
            return
        state = self._states[ply]
        assert state is not None
        print(f"{ply}: ", set(state))
