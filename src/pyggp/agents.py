import abc
import contextlib
import random
from abc import ABC
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Type

import rich.console
import rich.prompt
from rich import print

from pyggp._logging import log
from pyggp.exceptions.agent_exceptions import InterpreterAgentWithoutInterpreterError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Move, Relation, Role, Ruleset, State
from pyggp.interpreters import ClingoInterpreter, Interpreter


class Agent(AbstractContextManager[None], abc.ABC):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={hex(id(self))})"

    def __enter__(self) -> None:
        self.set_up()

    def __exit__(
        self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        self.tear_down()

    def set_up(self) -> None:
        pass

    def tear_down(self) -> None:
        pass

    def prepare_match(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        pass  # pragma: no cover

    def abort_match(self) -> None:
        pass  # pragma: no cover

    def conclude_match(self, view: State) -> None:
        pass  # pragma: no cover

    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        raise NotImplementedError


class InterpreterAgent(Agent, ABC):
    def __init__(self) -> None:
        self._interpreter: Interpreter | None = None
        self._role: Role | None = None
        self._ruleset: Ruleset | None = None
        self._startclock_config: GameClockConfiguration | None = None
        self._playclock_config: GameClockConfiguration | None = None

    def prepare_match(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        self._role = role
        self._ruleset = ruleset
        self._startclock_config = startclock_config
        self._playclock_config = playclock_config
        self._interpreter = ClingoInterpreter(ruleset)

    def conclude_match(self, view: State) -> None:
        self._interpreter = None
        self._role = None
        self._ruleset = None
        self._startclock_config = None
        self._playclock_config = None


class ArbitraryAgent(InterpreterAgent):
    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        if self._interpreter is None:
            raise InterpreterAgentWithoutInterpreterError
        moves = self._interpreter.get_legal_moves_by_role(view, self._role)
        return random.choice(tuple(moves))


class RandomAgent(InterpreterAgent):
    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        if self._interpreter is None:
            raise InterpreterAgentWithoutInterpreterError
        moves = self._interpreter.get_legal_moves_by_role(view, self._role)
        return random.choice(tuple(moves))
