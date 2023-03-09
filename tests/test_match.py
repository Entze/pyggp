# pylint: disable=missing-docstring,invalid-name,unused-argument
from unittest import TestCase

from common import SLEEP_TIME, MockAgent, MockTimeoutAgent, mock_match

from pyggp.actors import LocalActor
from pyggp.exceptions.match_exceptions import MatchDNSError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.games import nim_ruleset
from pyggp.gdl import Relation
from pyggp.interpreters import ClingoInterpreter
from pyggp.match import Match, MatchConfiguration


def test_as_expected_is_finished_non_finished() -> None:
    match = mock_match()

    assert not match.is_finished


def test_as_expected_is_finished_finished() -> None:
    match = mock_match(finish_match=True)

    assert match.is_finished


def test_as_expected_get_result() -> None:
    agent_p1 = MockAgent()
    match = mock_match(agents=(agent_p1,))

    agent_p1.next_move = 1

    match.execute_ply()
    match.conclude_match()

    assert match.get_result().utilities == {Relation("p1"): 1}


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
                match._initialize_agents()
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
                    Relation("first"): GameClockConfiguration(total_time=SLEEP_TIME * 0.9, increment=0.0, delay=0.0),
                    Relation("second"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                },
                playclock_configs={
                    Relation("first"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                    Relation("second"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=60.0),
                },
            )
            match = Match(match_configuration)
            with self.assertRaises(MatchDNSError):
                match._initialize_agents()
