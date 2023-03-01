# pylint: disable=missing-docstring,invalid-name,unused-argument
from unittest import TestCase

from pyggp.actors import LocalActor
from pyggp.agents import Agent
from pyggp.exceptions import MatchDNSError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.games import nim_ruleset
from pyggp.gdl import Move, Role, Ruleset, Relation, State
from pyggp.interpreters import ClingoInterpreter
from pyggp.match import MatchConfiguration, Match


class MockTimeoutAgent(Agent):
    def prepare_match(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        raise TimeoutError

    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        raise TimeoutError


class MockAgent(Agent):
    # pylint: disable=unused-argument
    def calculate_move(self, move_nr: int, total_time_ns: int, view: State) -> Move:
        return Relation("take", (1,))


class TestMatchInitializeAgents(TestCase):
    def test_success(self) -> None:
        ruleset = nim_ruleset
        first_agent = MockAgent()
        second_agent = MockAgent()
        with first_agent, second_agent:
            first_actor = LocalActor(first_agent)
            second_actor = LocalActor(second_agent)
            match_configuration = MatchConfiguration(
                ruleset=ruleset,
                interpreter=ClingoInterpreter(ruleset),
                role_actor_map={
                    Relation("first"): first_actor,
                    Relation("second"): second_actor,
                },
                startclock_configs={
                    Relation("first"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                    Relation("second"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                },
                playclock_configs={
                    Relation("first"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                    Relation("second"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                },
            )
            match = Match(match_configuration)
            try:
                match.initialize_agents()
            except TimeoutError:
                self.fail("Should not timeout")

    def test_timeout(self) -> None:
        ruleset = nim_ruleset
        first_agent = MockTimeoutAgent()
        second_agent = MockAgent()
        with first_agent, second_agent:
            first_actor = LocalActor(first_agent)
            second_actor = LocalActor(second_agent)
            match_configuration = MatchConfiguration(
                ruleset=ruleset,
                interpreter=ClingoInterpreter(ruleset),
                role_actor_map={
                    Relation("first"): first_actor,
                    Relation("second"): second_actor,
                },
                startclock_configs={
                    Relation("first"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                    Relation("second"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                },
                playclock_configs={
                    Relation("first"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                    Relation("second"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                },
            )
            match = Match(match_configuration)
            with self.assertRaises(MatchDNSError):
                match.initialize_agents()
