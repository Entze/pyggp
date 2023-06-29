"""Visualizers for consecutive states."""
import abc
import collections
import functools
import importlib
import re
from dataclasses import dataclass, field
from typing import (
    ClassVar,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

import clingo
from rich import print
from typing_extensions import ParamSpec, Self

import pyggp._clingo as clingo_helper
import pyggp.game_description_language as gdl
from pyggp._clingo_interpreter.base import _get_ctl, _get_model, _transform_model
from pyggp._clingo_interpreter.control_containers import ControlContainer, _set_state
from pyggp._logging import rich
from pyggp.cli.argument_specification import ArgumentSpecification
from pyggp.engine_primitives import Role, State
from pyggp.exceptions.cli_exceptions import VisualizerNotFoundCLIError
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

    def __rich__(self) -> str:
        return f"{self.__class__.__name__}()"

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
    def from_argument_specification_str(
        argument_specification_str: str,
        ruleset: gdl.Ruleset,
    ) -> "Visualizer":
        argument_specification = ArgumentSpecification.from_str(argument_specification_str)
        return Visualizer.from_argument_specification(argument_specification=argument_specification, ruleset=ruleset)

    @staticmethod
    def from_argument_specification(
        argument_specification: ArgumentSpecification,
        ruleset: gdl.Ruleset,
    ) -> "Visualizer":
        name = argument_specification.name
        args = argument_specification.args
        kwargs = argument_specification.kwargs

        try:
            module_name, class_name = name.rsplit(".", maxsplit=1)
            module = importlib.import_module(module_name)
            module_type = getattr(module, class_name)
        except (ValueError, ModuleNotFoundError, AttributeError):
            raise VisualizerNotFoundCLIError(name=name, args=args, kwargs=kwargs)
        module_factory = getattr(module_type, "from_cli", module_type)
        return module_factory(*args, ruleset=ruleset, **kwargs)


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
                print(
                    rich(
                        {
                            f"[yellow italic]{role}[/yellow italic]": f"[red]{utility}[/red]"
                            for role, utility in self.utilities.items()
                        },
                    ),
                )

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
    debug: bool = field(default=False)
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
        debug = bool(kwargs.pop("debug", False))
        return cls(ctl=ctl, debug=debug)

    def _draw_ply(self, ply: int) -> None:
        if ply >= len(self.states) or self.states[ply] is None:
            return
        state = self.states[ply]
        assert state is not None
        coordinates_to_str: MutableMapping[int, MutableMapping[int, str]] = collections.defaultdict(dict)
        sorted_subrelations = ()
        with _set_state(self.ctl, state_to_literal=self.state_to_literal, current=state):
            model = _get_model(self.ctl)
            if not self.debug:
                subrelations = _transform_model(model, ClingoStringVisualizer.viz_signature)
            else:
                sorted_subrelations = sorted(_transform_model(model))
                subrelations = (
                    subrelation
                    for subrelation in sorted_subrelations
                    if subrelation.matches_signature(*ClingoStringVisualizer.viz_signature)
                )
            for subrelation in subrelations:
                row: int = subrelation.symbol.arguments[0].symbol.number
                column: int = subrelation.symbol.arguments[1].symbol.number
                element = subrelation.symbol.arguments[2]
                string = element.symbol.string if element.is_string else str(element)
                coordinates_to_str[row][column] = string

        print(f"{ply}:")
        for row in sorted(coordinates_to_str):
            for column in sorted(coordinates_to_str[row]):
                print(coordinates_to_str[row][column], end="")
            print()
        if self.debug:
            print("Subrelations:")
            for subrelation in sorted_subrelations:
                print(subrelation)
