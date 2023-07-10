"""Visualizers for consecutive states."""
import abc
import collections
import functools
import importlib
import pathlib
import re
import sys
from dataclasses import dataclass, field
from types import TracebackType
from typing import (
    IO,
    ClassVar,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Type,
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
from pyggp.match import Disqualification, Match, log

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

    def __enter__(self) -> None:
        pass

    def __exit__(self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb: TracebackType) -> None:
        pass

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
            module_type = argument_specification.load()
        except (ValueError, ModuleNotFoundError, AttributeError):
            raise VisualizerNotFoundCLIError(name=name, args=args, kwargs=kwargs)
        module_factory = getattr(module_type, "from_cli", module_type)
        return module_factory(*args, ruleset=ruleset, **kwargs)

    @staticmethod
    def determine_filepath(
        path: Union[str, pathlib.Path],
    ) -> pathlib.Path:
        if isinstance(path, str):
            path = pathlib.Path(path)
        if (path.exists() and path.is_file()) or not hasattr(sys, "_MEIPASS"):
            return path
        # Disables SLF001 (Private member accessed). Because: pyinstaller sets this attribute.
        base_path = pathlib.Path(sys._MEIPASS).joinpath("visualizers")  # noqa: SLF001
        return base_path.joinpath(path)


@dataclass
class TextVisualizer(Visualizer, abc.ABC):
    path: Optional[pathlib.Path] = field(default=None)
    file: Optional[IO[str]] = field(default=None)

    def __enter__(self) -> None:
        super().__enter__()
        if self.path is not None:
            self.file = self.path.open("w")

    def __exit__(self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb: TracebackType) -> None:
        if self.file is not None:
            self.file.close()
        self.file = None
        super().__exit__(exc_type, exc_val, exc_tb)


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
class SimpleVisualizer(TextVisualizer):
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
    def from_cli(cls, file: Optional[str] = None, *args: str, **kwargs: str) -> Self:
        path = pathlib.Path(file) if file is not None else None
        return cls(path=path)

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
            print("Match aborted!", file=self.file)

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
                    file=self.file,
                )

    def _draw_ply(self, ply: int) -> None:
        if ply >= len(self.states) or self.states[ply] is None:
            return
        state = self.states[ply]
        assert state is not None
        print(f"{ply}: {'{'} ", end="", file=self.file)
        for n, symbol in enumerate(sorted(state)):
            print(symbol, end="", file=self.file)
            if n < len(state) - 1:
                print(", ", end="", file=self.file)
        print(" }", file=self.file)

    def _draw_utility(self) -> None:
        print("Utilities: { ", end="", file=self.file)
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
            print(f"[yellow italic]{role}[/yellow italic]: {pre}{utility}{post}", end="", file=self.file)
            if n < len(self.utilities) - 1:
                print(", ", end="", file=self.file)
        print(" }", file=self.file)


@dataclass
class ClingoStringVisualizer(SimpleVisualizer):
    ctl: clingo.Control = field(default_factory=clingo.Control)
    state_to_literal: MutableMapping[gdl.Subrelation, int] = field(default_factory=dict)
    debug_level: int = field(default=0)
    viz_signature: ClassVar[gdl.Relation.Signature] = gdl.Relation.Signature("__viz", 3)

    @classmethod
    def from_cli(cls, *paths: str, ruleset: Optional[gdl.Ruleset] = None, file: Optional[str] = None, **kwargs: str):
        if ruleset is None:
            ruleset = gdl.Ruleset()
        ctl = _get_ctl(
            sentences=ruleset.rules,
            rules=(*clingo_helper.EXTERNALS,),
            logger=functools.partial(ControlContainer.log, context="visualizer"),
        )
        for path in paths:
            p = Visualizer.determine_filepath(path)
            ctl.load(str(p))
            log.debug(f"Loaded %s", p)
        ctl.ground()
        debug = int(kwargs.pop("debug", 0))
        path = pathlib.Path(file) if file is not None else None
        return cls(ctl=ctl, path=path, debug_level=debug)

    def _draw_ply(self, ply: int) -> None:
        if ply >= len(self.states) or self.states[ply] is None:
            return
        state = self.states[ply]
        assert state is not None
        coordinates_to_str: MutableMapping[int, MutableMapping[int, str]] = collections.defaultdict(dict)
        sorted_subrelations = ()
        with _set_state(self.ctl, state_to_literal=self.state_to_literal, current=state):
            model = _get_model(self.ctl)
            if self.debug_level < 2:
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

        print(f"{ply}:", end="", file=self.file)
        if self.debug_level >= 1:
            print("", rich(state), end="", file=self.file)
        print(file=self.file)
        for row in sorted(coordinates_to_str):
            for column in sorted(coordinates_to_str[row]):
                print(coordinates_to_str[row][column], end="", file=self.file)
            print(file=self.file)
        if self.debug_level >= 2:
            print("Subrelations:", file=self.file)
            for subrelation in sorted_subrelations:
                print(subrelation, file=self.file)
