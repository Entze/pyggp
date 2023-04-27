"""Provides the most common basic agents."""
import abc
import contextlib
import logging
import random
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Any, Optional, Type

import rich.console
import rich.prompt
from rich import print

import pyggp.game_description_language as gdl
from pyggp.exceptions.agent_exceptions import InterpreterIsNoneInterpreterAgentError, RoleIsNoneAgentError
from pyggp.gameclocks import GameClock
from pyggp.interpreters import ClingoInterpreter, Interpreter, Move, Role, View

if TYPE_CHECKING:
    # TODO: Remove this once Python 3.8 is no longer supported.
    NoneContextManager = contextlib.AbstractContextManager[None]
    AnyContextManager = contextlib.AbstractContextManager[Any]
else:
    NoneContextManager = contextlib.AbstractContextManager
    AnyContextManager = contextlib.AbstractContextManager

log: logging.Logger = logging.getLogger("pyggp")


@dataclass
class Agent(NoneContextManager, abc.ABC):
    """Base class for all agents."""

    # region Magic Methods

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

    # endregion

    # region Methods

    def set_up(self) -> None:
        """Sets up the agent and all its required resources."""
        # Disables coverage. Because this not really testable.
        log.debug("Setting up %s", self)  # pragma: no cover

    def tear_down(self) -> None:
        """Destroys all resources of the agent."""
        # Disables coverage. Because this not really testable.
        log.debug("Tearing down %s", self)  # pragma: no cover

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
            "Preparing %s for match, role=%s, "
            "ruleset=Ruleset(nr_of_rules=%s)), "
            "startclock_config=%s, "
            "playclock_config=%s",
            self,
            role,
            len(ruleset.rules),
            startclock_config,
            playclock_config,
        )

    def abort_match(self) -> None:
        """Aborts the current match."""
        # Disables coverage. Because this not really testable.
        log.debug("Aborting match for %s", self)  # pragma: no cover

    def conclude_match(self, view: View) -> None:
        """Concludes the current match.

        Args:
            view: Final view of the match

        """
        # Disables coverage. Because this not really testable.
        log.debug("Concluding match for %s, view=%s", self, view)  # pragma: no cover

    @abc.abstractmethod
    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        """Calculates the next move.

        Args:
            ply: Current ply
            total_time_ns: Total time on the playclock in nanoseconds (without delay)
            view: Current view

        Returns:
            Move

        """
        raise NotImplementedError

    # endregion


@dataclass
class InterpreterAgent(Agent, abc.ABC):
    """Base class for all agents that use an interpreter."""

    # region Attributes and Properties

    role: Optional[Role] = None
    ruleset: Optional[gdl.Ruleset] = None
    startclock_config: Optional[GameClock.Configuration] = None
    playclock_config: Optional[GameClock.Configuration] = None
    interpreter: Optional[Interpreter] = None

    # endregion

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
        self.role = role
        self.ruleset = ruleset
        self.startclock_config = startclock_config
        self.playclock_config = playclock_config
        if self.interpreter is None:
            self.interpreter = ClingoInterpreter.from_ruleset(ruleset)

    def conclude_match(self, view: View) -> None:
        """Concludes the current match.

        Args:
            view: Final view of the match

        """
        super().conclude_match(view)
        self.role = None
        self.ruleset = None
        self.startclock_config = None
        self.playclock_config = None
        self.interpreter = None


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
        if self.interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError
        if self.role is None:
            raise RoleIsNoneAgentError
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
        if self.interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError
        if self.role is None:
            raise RoleIsNoneAgentError
        moves = self.interpreter.get_legal_moves_by_role(view, self.role)
        return random.choice(tuple(moves))


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
        if self.interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError
        if self.role is None:
            raise RoleIsNoneAgentError
        moves = sorted(self.interpreter.get_legal_moves_by_role(view, self.role))

        move_idx: Optional[int] = None
        while move_idx is None or not (1 <= move_idx <= len(moves)):
            console = rich.console.Console()
            ctx: AnyContextManager = (
                # Disables mypy. Because console.pager() returns only `object` and does not seem to be typed correctly.
                console.pager()  # type: ignore[assignment]
                # Disables PLR2004 (Magic value used in comparison). Because: 10 is an arbitrary value.
                if len(moves) > 10  # noqa: PLR2004
                else contextlib.nullcontext()
            )
            with ctx:
                console.print("Legal moves:")
                console.print("\n".join(f"\t[{n + 1}] {move}" for n, move in enumerate(moves)))
            move_prompt: str = rich.prompt.Prompt.ask(f"> (1-{len(moves)})", default="1", show_default=False)
            if move_idx is None:
                with contextlib.suppress(ValueError):
                    move_idx = int(move_prompt)
            if move_idx is None:
                with contextlib.suppress(ValueError):
                    tree = gdl.subrelation_parser.parse(move_prompt)
                    transformation = gdl.transformer.transform(tree)
                    assert isinstance(transformation, gdl.Subrelation)
                    search = Move(transformation)
                    move_idx = moves.index(search) + 1
            if move_idx is None or not (1 <= move_idx <= len(moves)):
                print(f"[red]Invalid move [italic purple]{move_prompt}.")

        return moves[move_idx - 1]
