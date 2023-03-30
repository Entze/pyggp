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
from pyggp._logging import log
from pyggp.exceptions.agent_exceptions import InterpreterIsNoneInterpreterAgentError, RoleIsNoneInterpreterAgentError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.interpreters import ClingoInterpreter, Interpreter, Move, Role, View


class Agent(AbstractContextManager[None], abc.ABC):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={hex(id(self))})"

    def __enter__(self) -> None:
        self.set_up()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.tear_down()

    def set_up(self) -> None:
        log.debug("Setting up %s", self)

    def tear_down(self) -> None:
        log.debug("Tearing down %s", self)

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        log.debug(
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
        log.debug("Aborting match for %s", self)

    def conclude_match(self, view: View) -> None:
        log.debug("Concluding match for %s, view=%s", self, view)

    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        raise NotImplementedError


class InterpreterAgent(Agent, abc.ABC):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._interpreter: Optional[Interpreter] = None
        self._role: Optional[Role] = None
        self._ruleset: Optional[gdl.Ruleset] = None
        self._startclock_config: Optional[GameClockConfiguration] = None
        self._playclock_config: Optional[GameClockConfiguration] = None

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        super().prepare_match(role, ruleset, startclock_config, playclock_config)
        self._role = role
        self._ruleset = ruleset
        self._startclock_config = startclock_config
        self._playclock_config = playclock_config
        self._interpreter = ClingoInterpreter(ruleset)

    def conclude_match(self, view: View) -> None:
        super().conclude_match(view)
        self._interpreter = None
        self._role = None
        self._ruleset = None
        self._startclock_config = None
        self._playclock_config = None


class ArbitraryAgent(InterpreterAgent):
    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        if self._interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError
        if self._role is None:
            raise RoleIsNoneInterpreterAgentError
        moves = self._interpreter.get_legal_moves_by_role(view, self._role)
        return random.choice(tuple(moves))


class RandomAgent(InterpreterAgent):
    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        if self._interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError
        if self._role is None:
            raise RoleIsNoneInterpreterAgentError
        moves = self._interpreter.get_legal_moves_by_role(view, self._role)
        return random.choice(tuple(moves))


class HumanAgent(InterpreterAgent):
    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        log.info("Calculating move %d for %s, view=%s", ply, self, view)
        if self._interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError
        if self._role is None:
            raise RoleIsNoneInterpreterAgentError
        moves = sorted(self._interpreter.get_legal_moves_by_role(view, self._role))

        move_idx: Optional[int] = None
        while move_idx is None or not (1 <= move_idx <= len(moves)):
            console = rich.console.Console()
            # Disables mypy. Because console.pager() returns only `object` and does not seem to be typed correctly.
            ctx: AbstractContextManager[Any] = (
                console.pager() if len(moves) > 10 else contextlib.nullcontext()  # type: ignore[assignment]
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
