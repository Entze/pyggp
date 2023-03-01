from contextlib import AbstractContextManager
from types import TracebackType
from typing import Type

from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Ruleset, Move, Role, State


class Agent(AbstractContextManager[None]):
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
        pass

    def abort_match(self) -> None:
        pass  # pragma: no cover

    def conclude_match(self, view: State) -> None:
        pass  # pragma: no cover

    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        raise NotImplementedError
