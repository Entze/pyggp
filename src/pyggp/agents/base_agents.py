"""Provides the most common basic agents."""
import abc
import contextlib
import random
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, Optional, Type

import rich.console
import rich.prompt
from rich import print

import pyggp.game_description_language as gdl
from pyggp._logging import format_timedelta, log
from pyggp.exceptions.agent_exceptions import InterpreterIsNoneInterpreterAgentError, RoleIsNoneInterpreterAgentError
from pyggp.gameclocks import GameClock
from pyggp.interpreters import ClingoInterpreter, Interpreter, Move, Role, View


class Agent(AbstractContextManager[None], abc.ABC):
    """Base class for all agents."""

    # region Magic Methods

    def __repr__(self) -> str:
        """Representation of the agent.

        Returns:
            Representation of the agent

        """
        return f"{self.__class__.__name__}(id={hex(id(self))})"

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


class InterpreterAgent(Agent, abc.ABC):
    """Base class for all agents that use an interpreter."""

    # region Magic Methods

    # Disables ARG002 (Unused method argument). Because: Defer arguments to other classes in MRO.
    def __init__(self, interpreter: Optional[Interpreter] = None, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        """Initializes the agent.

        Args:
            interpreter: Interpreter to use
            *args: Leftover arguments
            **kwargs: Leftover keyword arguments

        """
        self._interpreter: Optional[Interpreter] = interpreter
        self._role: Optional[Role] = None
        self._ruleset: Optional[gdl.Ruleset] = None
        self._startclock_config: Optional[GameClock.Configuration] = None
        self._playclock_config: Optional[GameClock.Configuration] = None

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
        self._role = role
        self._ruleset = ruleset
        self._startclock_config = startclock_config
        self._playclock_config = playclock_config
        self._interpreter = ClingoInterpreter(ruleset)

    def conclude_match(self, view: View) -> None:
        """Concludes the current match.

        Args:
            view: Final view of the match

        """
        super().conclude_match(view)
        self._interpreter = None
        self._role = None
        self._ruleset = None
        self._startclock_config = None
        self._playclock_config = None


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
        if self._interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError
        if self._role is None:
            raise RoleIsNoneInterpreterAgentError
        moves = self._interpreter.get_legal_moves_by_role(view, self._role)
        # Disables S311 (Standard pseudo-random generators are not suitable for security/cryptographic purposes).
        # Because: This is not a security/cryptographic purpose.
        return random.choice(tuple(moves))  # noqa: S311


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
        if self._interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError
        if self._role is None:
            raise RoleIsNoneInterpreterAgentError
        moves = self._interpreter.get_legal_moves_by_role(view, self._role)
        # Disables S311 (Standard pseudo-random generators are not suitable for security/cryptographic purposes).
        # Because: This is not a security/cryptographic purpose.
        return random.choice(tuple(moves))  # noqa: S311


class HumanAgent(InterpreterAgent):
    """Agent that asks the user for a move."""

    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        """Calculates the next move.

        Args:
            ply: Current ply
            total_time_ns: Total time on the playclock in nanoseconds (without delay)
            view: Current view

        Returns:
            Move

        """
        log.info(
            "Calculating move %d for %s, view=%s, total_time=%s",
            ply,
            self,
            view,
            format_timedelta(total_time_ns / 1e9),
        )
        if self._interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError
        if self._role is None:
            raise RoleIsNoneInterpreterAgentError
        moves = sorted(self._interpreter.get_legal_moves_by_role(view, self._role))

        move_idx: Optional[int] = None
        while move_idx is None or not (1 <= move_idx <= len(moves)):
            console = rich.console.Console()
            ctx: AbstractContextManager[Any] = (
                # Disables mypy. Because console.pager() returns only `object` and does not seem to be typed correctly.
                console.pager()  # type: ignore[assignment]
                # Disables PLR2004 (Magic value used in comparison). Because: 10 is an arbitrary value.
                if len(moves) > 10  # noqa: PLR2004
                else contextlib.nullcontext()
            )
            with ctx:
                console.print("Legal moves:")
                console.print("\n".join(f"\t[{n + 1}] {move}" for n, move in enumerate(moves)))
            move_prompt: str = rich.prompt.Prompt.ask("> ", default="1")
            if move_idx is None:
                with contextlib.suppress(ValueError):
                    move_idx = int(move_prompt)
            if move_idx is None:
                with contextlib.suppress(ValueError):
                    search = Move(gdl.Subrelation(gdl.Relation.from_str(move_prompt)))
                    move_idx = moves.index(search) + 1
            if move_idx is None or not (1 <= move_idx <= len(moves)):
                print(f"[red]Invalid move [italic purple]{move_prompt}.")

        return moves[move_idx - 1]
