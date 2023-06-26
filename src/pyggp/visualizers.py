"""Visualizers for consecutive states."""
import abc
import functools
import re
from dataclasses import dataclass, field
from typing import (
    Callable,
    ClassVar,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    ParamSpec,
    Self,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

import clingo
from rich import print

import pyggp._clingo as clingo_helper
import pyggp.game_description_language as gdl
from pyggp._clingo_interpreter.base import _get_ctl, _get_model, _transform_model
from pyggp._clingo_interpreter.control_containers import ControlContainer, _set_state
from pyggp.engine_primitives import Role, State
from pyggp.match import Disqualification, Match

_P = ParamSpec("_P")
_V = TypeVar("_V", bound="Visualizer")

visualizer_str_re = re.compile(r"^(?P<name>\w+)\s*\((?P<args>.*)\)?$")


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

    @staticmethod
    def parse_str(visualizer_str: str) -> Tuple[Callable[_P, _V], Tuple[str, ...], Mapping[str, str]]:
        visualizer_str_match = visualizer_str_re.match(visualizer_str)
        if visualizer_str_match is None:
            raise
        visualizer_name = visualizer_str_match.group("name")
        visualizer_factory = None
        if visualizer_name.casefold() not in ("null", "simple", "clingostring"):
            raise
        if visualizer_name.casefold() == "null":
            visualizer_factory = NullVisualizer.from_cli
        elif visualizer_name.casefold() == "simple":
            visualizer_factory = SimpleVisualizer.from_cli
        elif visualizer_name.casefold() == "clingostring":
            visualizer_factory = ClingoStringVisualizer.from_cli
        else:
            message = f"Accepted but unhandled visualizer name: {visualizer_name}"
            raise AssertionError(message)

        visualizer_args_str = visualizer_str_match.group("args")
        visualizer_args = visualizer_args_str.split(",")
        visualizer_kwargs = {}


@dataclass
class NullVisualizer(Visualizer):  # pragma: no cover
    """Visualizer that does nothing."""

    @classmethod
    def from_cli(cls, *args: str, **kwargs: str) -> Self:
        return cls()

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

    @classmethod
    def from_cli(cls, *args: str, **kwargs: str) -> Self:
        return cls()

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
            if len(self.utilities) > 1:
                self._draw_utility()
            else:
                for role, utility in self.utilities.items():
                    print("{[yellow italic]%s[/yellow italic]: [red]%s[/red]}", role, utility)

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
                percentile = utility_index / (len(self.utilities) - 1)  # TODO: division by zero
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


@dataclass
class ClingoStringVisualizer(SimpleVisualizer):
    ctl: clingo.Control = field(default_factory=clingo.Control)
    state_to_literal: MutableMapping[gdl.Subrelation, int] = field(default_factory=dict)
    last_drawn_ply: int = field(default=-1)
    viz_signature: ClassVar[gdl.Relation.Signature] = gdl.Relation.Signature("__viz", 3)

    @classmethod
    def from_cli(cls, path: str, *args: str, ruleset: gdl.Ruleset, **kwargs: str):
        ctl = _get_ctl(
            sentences=ruleset.rules,
            rules=(*clingo_helper.EXTERNALS,),
            logger=functools.partial(ControlContainer.log, context="visualizer"),
        )
        ctl.load(path)
        ctl.ground()
        return cls(ctl=ctl)

    def _draw_ply(self, ply: int) -> None:
        if ply >= len(self.states) or self.states[ply] is None:
            return
        state = self.states[ply]
        assert state is not None
        with _set_state(self.ctl, state_to_literal=self.state_to_literal, current=state):
            model = _get_model(self.ctl)
            subrelations = _transform_model(model, ClingoStringVisualizer.viz_signature)
            coordinates_to_subrelation = {
                subrelation.symbol.arguments[0].number: {
                    subrelation.symbol.arguments[1].number: subrelation.symbol.arguments[2],
                }
                for subrelation in subrelations
            }
        coordinates_to_str = {
            row: {
                column: subrelation.string if subrelation.is_string else str(subrelation)
                for column, subrelation in column_to_subrelation.items()
            }
            for row, column_to_subrelation in coordinates_to_subrelation.items()
        }
        for row in sorted(coordinates_to_str):
            for column in sorted(coordinates_to_str[row]):
                print(coordinates_to_str[row][column], end="")
            print()
