# pylint: disable=missing-docstring,invalid-name,unused-argument
import time

from pyggp.agents import Agent
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Role, Ruleset, State, Move, Relation

SLEEP_TIME: float = 0.25


class MockCalledAgent(Agent):
    def __init__(self) -> None:
        super().__init__()
        self.called_calc_move = False
        self.called_prepare_match = False
        self.called_abort_match = False
        self.called_conclude_match = False

    def prepare_match(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        self.called_prepare_match = True

    def abort_match(self) -> None:
        self.called_abort_match = True

    def conclude_match(self, view: State) -> None:
        self.called_conclude_match = True

    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        self.called_calc_move = True
        return Relation("called")


class MockTimeoutAgent(Agent):
    def prepare_match(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        time.sleep(SLEEP_TIME)

    def abort_match(self) -> None:
        time.sleep(SLEEP_TIME)

    def conclude_match(self, view: State) -> None:
        time.sleep(SLEEP_TIME)

    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        time.sleep(SLEEP_TIME)
        return Relation("called")
