# pylint: disable=missing-docstring,invalid-name,unused-argument

import pytest
from common import SLEEP_TIME, MockAgent, MockTimeoutAgent

from pyggp.actors import LocalActor
from pyggp.exceptions.actor_exceptions import ActorNotStartedError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Relation, Ruleset


def test_as_expected_local_actor() -> None:
    agent = MockAgent()
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


def test_raises_if_not_started() -> None:
    agent = MockAgent()
    actor = LocalActor(agent)
    with pytest.raises(ActorNotStartedError):
        actor.send_play(0, frozenset())


def test_raises_if_timeout_during_start() -> None:
    agent = MockTimeoutAgent()
    actor = LocalActor(agent)
    with pytest.raises(TimeoutError):
        actor.send_start(
            "role",
            Ruleset([]),
            GameClockConfiguration(total_time=SLEEP_TIME - 0.05, increment=0.0, delay=0.0),
            GameClockConfiguration(),
        )


def test_raises_if_timeout_during_play() -> None:
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
