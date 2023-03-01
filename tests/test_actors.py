# pylint: disable=missing-docstring,invalid-name,unused-argument

import pytest

from common import SLEEP_TIME, MockCalledAgent, MockTimeoutAgent
from pyggp.actors import LocalActor
from pyggp.exceptions import ActorNotStartedError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Relation, Ruleset


def test_as_expected_local_actor() -> None:
    agent = MockCalledAgent()
    actor = LocalActor(agent)
    assert not agent.called_prepare_match
    actor.send_start("role", Ruleset([]), GameClockConfiguration(), GameClockConfiguration())
    assert agent.called_prepare_match

    assert not agent.called_calc_move
    move = actor.send_play(0, frozenset())
    assert agent.called_calc_move
    assert move == Relation("called")

    assert not agent.called_conclude_match
    actor.send_stop(frozenset())
    assert agent.called_conclude_match

    assert not agent.called_abort_match
    actor.send_abort()
    assert agent.called_abort_match


def test_throws_exception_if_not_started() -> None:
    agent = MockCalledAgent()
    actor = LocalActor(agent)
    with pytest.raises(ActorNotStartedError):
        actor.send_play(0, frozenset())


def test_throws_exception_if_timeout_during_start() -> None:
    agent = MockTimeoutAgent()
    actor = LocalActor(agent)
    with pytest.raises(TimeoutError):
        actor.send_start(
            "role",
            Ruleset([]),
            GameClockConfiguration(total_time=SLEEP_TIME - 0.05, increment=0.0, delay=0.0),
            GameClockConfiguration(),
        )


def test_throws_exception_if_timeout_during_play() -> None:
    agent = MockTimeoutAgent()
    actor = LocalActor(agent)
    actor.send_start(
        "role",
        Ruleset([]),
        GameClockConfiguration(),
        GameClockConfiguration(total_time=SLEEP_TIME - 0.05, increment=0.0, delay=0.0),
    )
    with pytest.raises(TimeoutError):
        actor.send_play(
            0,
            frozenset(),
        )
