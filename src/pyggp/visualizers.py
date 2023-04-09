"""Visualizers for consecutive states."""
import abc
from dataclasses import dataclass, field
from typing import ClassVar, Mapping, MutableSequence, Optional, Sequence, Union

from rich import print

from pyggp.interpreters import Role, State
from pyggp.match import Disqualification, Match


@dataclass
class Visualizer(abc.ABC):
    """Base class for visualizers."""

    states: MutableSequence[Optional[State]] = field(default_factory=list)
    utilities: Mapping[Role, Union[int, None, Disqualification]] = field(default_factory=dict)
    aborted: bool = field(default=False)

    def update_state(self, state: State, ply: Optional[int] = None) -> None:
        """Update a state.

        If ply is None, it is assumed to be the next ply.

        Args:
            state: State to update
            ply: Ply to update

        """
        if ply is None:
            self.states.append(state)
            return
        if ply >= len(self.states):
            self.states.extend([None] * ((ply + 1) - len(self.states)))

        self.states[ply] = state

    def update_result(self, utilities: Mapping[Role, Union[int, None, Disqualification]]) -> None:
        """Update the result of the match.

        Args:
            utilities: Goals (utility values) for each role

        """
        raise NotImplementedError

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

    def update_result(self, utilities: Mapping[Role, Union[int, None, Disqualification]]) -> None:
        """Update the result of the match.

        Args:
            utilities: Goals (utility values) for each role

        """

    def update_abort(self) -> None:
        """Indicate to the visualizer that the match has been aborted."""

    def draw(self) -> None:
        """Draw new information."""


@dataclass
class SimpleVisualizer(Visualizer):
    """Visualizer that dumps states to stdout."""

    last_drawn_ply: int = field(default=-1)

    utility_colors: ClassVar[Sequence[str]] = (
        "green3",
        "cyan3",
        "sky_blue_3",
        "blue3",
        "yellow3",
        "orange3",
        "gold3",
        "magenta3",
        "pink3",
        "red3",
    )

    def update_result(self, utilities: Mapping[Role, Union[int, None, Disqualification]]) -> None:
        """Update the result of the match.

        Args:
            utilities: Goals (utility values) for each role

        """
        self.utilities = utilities

    def update_abort(self) -> None:
        """Indicate to the visualizer that the match has been aborted."""
        self.aborted = True

    def draw(self) -> None:
        """Draw new information."""
        for ply in range(self.last_drawn_ply + 1, len(self.states)):
            self._draw_ply(ply)
            self.last_drawn_ply = ply

        if self.aborted:
            print("Match aborted!")

        if self.utilities:
            self._draw_utility()

    def _draw_ply(self, ply: int) -> None:
        if ply >= len(self.states) or self.states[ply] is None:
            return
        state = self.states[ply]
        assert state is not None
        print(f"{ply}: {'{'} ", end="")
        for n, symbol in enumerate(sorted(state)):
            print(symbol, end="")
            if n < len(state) - 1:
                print(", ", end="")
        print(" }")

    def _draw_utility(self) -> None:
        print("Utilities: { ", end="")
        role_rank_map = Match.get_rank(self.utilities)
        utility_colors_max_index = len(self.utility_colors) - 1
        assert utility_colors_max_index >= 0
        for n, (role, utility) in enumerate(sorted(self.utilities.items())):
            if utility is not None:
                utility_index = role_rank_map[role]
                percentile = utility_index / (len(self.utilities) - 1)
                color_index = int(percentile * utility_colors_max_index)
                color = self.utility_colors[color_index]
                pre = f"[{color}]"
                post = f"[/{color}]"
            else:
                pre = ""
                post = ""
            print(f"[yellow italic]{role}[/yellow italic]: {pre}{utility}{post}", end="")
            if n < len(self.utilities) - 1:
                print(", ", end="")
        print(" }")
