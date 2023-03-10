import abc
import contextlib
import random
from abc import ABC
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Optional, Type

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
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        self.tear_down()

    def set_up(self) -> None:
        log.debug("Setting up %s", self)

    def tear_down(self) -> None:
        log.debug("Tearing down %s", self)

    def prepare_match(
        self,
        role: Role,
        ruleset: Ruleset,
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

    def conclude_match(self, view: State) -> None:
        log.debug("Concluding match for %s, view=%s", self, view)

    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        raise NotImplementedError


class InterpreterAgent(Agent, ABC):
    def __init__(self) -> None:
        self._interpreter: Optional[Interpreter] = None
        self._role: Optional[Role] = None
        self._ruleset: Optional[Ruleset] = None
        self._startclock_config: Optional[GameClockConfiguration] = None
        self._playclock_config: Optional[GameClockConfiguration] = None

    def prepare_match(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        super().prepare_match(role, ruleset, startclock_config, playclock_config)
        self._role = role
        self._ruleset = ruleset
        self._startclock_config = startclock_config
        self._playclock_config = playclock_config
        self._interpreter = ClingoInterpreter(ruleset)

    def conclude_match(self, view: State) -> None:
        super().conclude_match(view)
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


class HumanAgent(InterpreterAgent):
    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        log.info("Calculating move %d for %s, view=%s", move_nr, self, view)
        if self._interpreter is None:
            raise InterpreterAgentWithoutInterpreterError
        moves = sorted(self._interpreter.get_legal_moves_by_role(view, self._role))

        move_idx: Optional[int] = None
        while move_idx is None or not (1 <= move_idx <= len(moves)):
            console = rich.console.Console()
            ctx = contextlib.nullcontext() if len(moves) <= 10 else console.pager()
            with ctx:
                console.print("Legal moves:")
                console.print(f"\n".join(f"\t[{n + 1}] {move}" for n, move in enumerate(moves)))
            move_prompt: str = rich.prompt.Prompt.ask("> ", default="1")
            try:
                move_idx = int(move_prompt)
            except ValueError:
                pass
            try:
                if (move_prompt.startswith("'") and move_prompt.endswith("'")) or (
                    move_prompt.startswith('"') and move_prompt.endswith('"')
                ):
                    search = move_prompt[1:-1]
                else:
                    search = Relation(move_prompt)
                move_idx = moves.index(search) + 1
            except ValueError:
                pass
            if move_idx is None or not (1 <= move_idx <= len(moves)):
                print(f"[red]Invalid move [italic purple]{move_prompt}.")

        return moves[move_idx - 1]
