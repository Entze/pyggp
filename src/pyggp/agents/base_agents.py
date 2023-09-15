"""Provides the most common basic agents."""
import abc
import contextlib
import difflib
import functools
import logging
import random
from dataclasses import dataclass, field
from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, Final, MutableSequence, Optional, Protocol, Sequence, Type

import rich.console as rich_console
import rich.prompt as rich_prompt
from rich import print
from typing_extensions import ParamSpec, Self

import pyggp.game_description_language as gdl
from pyggp._logging import format_id, rich
from pyggp.cli.argument_specification import ArgumentSpecification
from pyggp.engine_primitives import Move, Role, View
from pyggp.gameclocks import GameClock
from pyggp.interpreters import ClingoInterpreter, Interpreter

# Disables SIM108 (Use ternary operator instead of if-else block). Because: TYPE_CHECKING is an exception.
if TYPE_CHECKING:  # noqa: SIM108
    # TODO: Remove after python 3.8 is no longer supported
    AnyContextManager = contextlib.AbstractContextManager[Any]
else:
    AnyContextManager = contextlib.AbstractContextManager

log: logging.Logger = logging.getLogger("pyggp")


class Agent(Protocol):
    def __enter__(self) -> None:
        """Calls set_up."""
        self.set_up()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Calls tear_down."""
        self.tear_down()

    @classmethod
    def from_cli(cls, *args: str, **kwargs: str) -> Self:
        """Creates an agent from command line arguments."""

    def set_up(self) -> None:
        """Sets up the agent and all its required resources."""

    def tear_down(self) -> None:
        """Destroys all resources of the agent."""

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        """Prepares the agent for a match.

        Args:
            role: Role of the agent
            ruleset: Ruleset of the match
            startclock_config: Configuration of startclock
            playclock_config: Configuration of playclock

        """

    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        """Calculates the next move.

        Args:
            ply: Current ply
            total_time_ns: Total time on the playclock in nanoseconds (without delay)
            view: Current view

        Returns:
            Move

        """

    def conclude_match(self, view: View) -> None:
        """Concludes the current match.

        Args:
            view: Final view of the match

        """

    def abort_match(self) -> None:
        """Aborts the current match."""


class _AbstractAgent(Agent, abc.ABC):
    """Base class for all agents."""

    def __rich__(self) -> str:
        id_str = f"id={format_id(self)}"
        attributes_str = id_str
        return f"{self.__class__.__name__}({attributes_str})"

    @classmethod
    def from_cli(cls, *args: str, **kwargs: str) -> Self:
        return cls()

    def set_up(self) -> None:
        """Sets up the agent and all its required resources."""
        # Disables coverage. Because this not really testable.
        log.debug("Setting up %s", rich(self))  # pragma: no cover

    def tear_down(self) -> None:
        """Destroys all resources of the agent."""
        # Disables coverage. Because this not really testable.
        log.debug("Tearing down %s", rich(self))  # pragma: no cover

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        """Prepares the agent for a match.

        Args:
            role: Role of the agent
            ruleset: Ruleset of the match
            startclock_config: Configuration of startclock
            playclock_config: Configuration of playclock

        """
        # Disables coverage. Because this not really testable.
        log.debug(  # pragma: no cover
            "Preparing %s for match, role=%s, ruleset=%s, startclock_config=%s, playclock_config=%s",
            rich(self),
            rich(role),
            rich(ruleset),
            rich(startclock_config),
            rich(playclock_config),
        )

    def abort_match(self) -> None:
        """Aborts the current match."""
        # Disables coverage. Because this not really testable.
        log.debug("Aborting match for %s", rich(self))  # pragma: no cover

    def conclude_match(self, view: View) -> None:
        """Concludes the current match.

        Args:
            view: Final view of the match

        """
        # Disables coverage. Because this not really testable.
        log.debug("Concluding match for %s, view=%s", rich(self), rich(view))  # pragma: no cover

    # endregion


_P = ParamSpec("_P")


@dataclass
class InterpreterAgent(_AbstractAgent, abc.ABC):
    """Base class for all agents that use an interpreter."""

    # region Attributes and Properties

    role: Optional[Role] = None
    ruleset: Optional[gdl.Ruleset] = field(default=None, repr=False)
    startclock_config: Optional[GameClock.Configuration] = None
    playclock_config: Optional[GameClock.Configuration] = None
    interpreter: Optional[Interpreter] = field(default=None, repr=False)
    interpreter_factory: Callable[_P, Interpreter] = field(default=ClingoInterpreter.from_ruleset, repr=False)

    # endregion

    def __rich__(self) -> str:
        id_str = f"id={format_id(self)}"
        interpreter_str = f"interpreter={rich(self.interpreter)}"
        interpreter_factory_str = f"interpreter_factory={rich(self.interpreter_factory)}"
        attributes_str = f"{id_str}, {interpreter_str}, {interpreter_factory_str}"
        return f"{self.__class__.__name__}({attributes_str})"

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        """Prepares the agent for a match.

        Args:
            role: Role of the agent
            ruleset: Ruleset of the match
            startclock_config: Configuration of startclock
            playclock_config: Configuration of playclock

        """
        super().prepare_match(role, ruleset, startclock_config, playclock_config)
        log.debug("Setting role, ruleset, startclock_config, playclock_config, and interpreter for %s", rich(self))
        self.role = role
        self.ruleset = ruleset
        self.startclock_config = startclock_config
        self.playclock_config = playclock_config
        if self.interpreter is None:
            self.interpreter = self.interpreter_factory(ruleset=ruleset)

    def conclude_match(self, view: View) -> None:
        """Concludes the current match.

        Args:
            view: Final view of the match

        """
        super().conclude_match(view)
        log.debug("Deleting role, ruleset, startclock_config, playclock_config, and interpreter for %s", rich(self))
        self.role = None
        self.ruleset = None
        self.startclock_config = None
        self.playclock_config = None
        self.interpreter = None

    @staticmethod
    def interpreter_factory_from_spec_str(spec_str: str) -> Callable[[gdl.Ruleset], Interpreter]:
        spec = ArgumentSpecification.from_str(spec_str)
        interpreter_type = spec.load()
        factory = getattr(interpreter_type, "from_cli", getattr(interpreter_type, "from_ruleset", interpreter_type))
        return functools.partial(factory, *spec.args, **spec.kwargs)


@dataclass
class ArbitraryAgent(InterpreterAgent):
    """Agent that returns an arbitrary legal move."""

    # Disables ARG002 (Unused method argument). Because: Implements abstract method.
    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:  # noqa: ARG002
        """Calculates the next move.

        Args:
            ply: Current ply
            total_time_ns: Total time on the playclock in nanoseconds (without delay)
            view: Current view

        Returns:
            Move

        """
        assert (
            self.interpreter is not None
        ), "Assumption: interpreter is not None (should have been set in prepare_match)"
        assert self.role is not None, "Assumption: role is not None (should have been set in prepare_match)"
        moves = self.interpreter.get_legal_moves_by_role(view, self.role)
        return random.choice(tuple(moves))


@dataclass
class RandomAgent(InterpreterAgent):
    """Agent that handles the random role.

    Attention, this agent is not to be confused with ArbitraryAgent. ArbitraryAgent returns an arbitrary legal move.

    """

    # Disables ARG002 (Unused method argument). Because: Implements abstract method.
    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:  # noqa: ARG002
        """Calculates the next move.

        Args:
            ply: Current ply
            total_time_ns: Total time on the playclock in nanoseconds (without delay)
            view: Current view

        Returns:
            Move

        """
        assert (
            self.interpreter is not None
        ), "Assumption: interpreter is not None (should have been set in prepare_match)"
        assert self.role is not None, "Assumption: role is not None (should have been set in prepare_match)"
        moves = self.interpreter.get_legal_moves_by_role(view, self.role)
        return random.choice(tuple(moves))


MAX_DISPLAYED_OPTIONS: Final[int] = 10


@dataclass
class HumanAgent(InterpreterAgent):
    """Agent that asks the user for a move."""

    # Disables ARG002 (Unused method argument). Because: Implements abstract method.
    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:  # noqa: ARG002
        """Calculates the next move.

        Args:
            ply: Current ply
            total_time_ns: Total time on the playclock in nanoseconds (without delay)
            view: Current view

        Returns:
            Move

        """
        assert (
            self.interpreter is not None
        ), "Assumption: interpreter is not None (should have been set in prepare_match)"
        assert self.role is not None, "Assumption: role is not None (should have been set in prepare_match)"
        print("ply:", ply)
        print(rich(view))
        moves = sorted(self.interpreter.get_legal_moves_by_role(view, self.role))

        move: Optional[Move] = None
        while move is None:
            console = rich_console.Console()
            ctx: AnyContextManager = (
                # Disables mypy. Because console.pager() returns only `object` and does not seem to be typed correctly.
                console.pager()  # type: ignore[assignment]
                if len(moves) > MAX_DISPLAYED_OPTIONS
                else contextlib.nullcontext()
            )
            only_numbers = all(move.is_number for move in moves)
            console.print("Legal moves:")
            if not only_numbers:
                self._display_moves(ctx, console, moves)
            else:
                self._display_moves_only_numbers(ctx, console, moves)
            move_prompt: str = self._prompt(moves) if not only_numbers else self._prompt_only_numbers()
            move = (
                self._parse_move_prompt(move_prompt, moves)
                if not only_numbers
                else self._parse_move_str(move_prompt, moves)
            )
            if move is None:
                self._help(move_prompt, moves)

        assert move is not None, "Guarantee: move is not None (loop condition)"
        return move

    def _help(self, move_prompt: str, moves: Sequence[Move]) -> None:
        print(f"[red]Invalid move [italic purple]{move_prompt}.")
        only_numbers = all(move.is_number for move in moves)
        moves_strs = (*(str(move) for move in moves), *(str(n) for n in range(1, len(moves) + 1) if not only_numbers))
        similar_moves = difflib.get_close_matches(move_prompt, moves_strs, n=MAX_DISPLAYED_OPTIONS)
        if similar_moves:
            print("Did you mean?")
            for similar_move in similar_moves:
                print(f"\t{similar_move}")

    def _display_moves_only_numbers(
        self,
        ctx: AnyContextManager,
        console: rich_console.Console,
        moves: Sequence[Move],
    ) -> None:
        ranges = []
        range_start = None
        last_move = None
        for move in moves:
            if range_start is None:
                range_start = move
            elif last_move is not None and last_move.symbol.number + 1 != move.symbol.number:
                ranges.append((range_start, last_move))
                range_start = move
            last_move = move
        ranges.append((range_start, last_move))
        ranges_strs = []
        for lower, upper in ranges:
            if lower == upper:
                ranges_strs.append(f"{lower}")
            else:
                ranges_strs.append(f"{lower}-{upper}")

        with ctx:
            console.print(", ".join(ranges_strs))

    def _display_moves(self, ctx: AnyContextManager, console: rich_console.Console, moves: Sequence[Move]) -> None:
        with ctx:
            console.print("\n".join(f"\t[{n + 1}] {move}" for n, move in enumerate(moves)))

    def _prompt_only_numbers(self) -> str:
        return rich_prompt.Prompt.ask("> ", show_default=False)

    def _prompt(self, moves: Sequence[Move]) -> str:
        return rich_prompt.Prompt.ask(f"> (1-{len(moves)})", default="1", show_default=False)

    def _parse_move_prompt(self, move_prompt: str, moves: Sequence[Move]) -> Optional[Move]:
        move = self._parse_move_idx(move_prompt, moves)
        if move is None:
            move = self._parse_move_str(move_prompt, moves)
        return move

    def _parse_move_idx(self, move_prompt_idx: str, moves: Sequence[Move]) -> Optional[Move]:
        move_idx: Optional[int] = None
        with contextlib.suppress(ValueError):
            move_idx = int(move_prompt_idx)
        if move_idx is None or not 1 <= move_idx <= len(moves):
            return None
        return moves[move_idx - 1]

    def _parse_move_str(self, move_prompt_str: str, moves: Sequence[Move]) -> Optional[Move]:
        moves_strs: Sequence[str] = tuple(str(move) for move in moves)
        assert len(moves_strs) == len(
            set(moves_strs),
        ), "Assumption: len(moves_strs) == len(set(moves_strs)) (no duplicate strings)"
        exact_match_idx: Optional[int] = None
        fuzzy_matches: MutableSequence[int] = []
        for idx, move_str in enumerate(moves_strs):
            if move_str == move_prompt_str:
                exact_match_idx = idx
                break
            m = move_str.rfind(move_prompt_str)
            if m != -1:
                fuzzy_matches.append(idx)
        if exact_match_idx is not None:
            return moves[exact_match_idx]
        if len(fuzzy_matches) == 1:
            return moves[fuzzy_matches[0]]
        return None
