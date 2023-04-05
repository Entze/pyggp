from unittest import mock

import pyggp.game_description_language as gdl
import pytest
from pyggp.actors import LocalActor
from pyggp.agents import Agent
from pyggp.exceptions.actor_exceptions import AgentIsNoneLocalActorError
from pyggp.gameclocks import (
    DEFAULT_NO_TIMEOUT_CONFIGURATION,
    DEFAULT_PLAY_CLOCK_CONFIGURATION,
    DEFAULT_START_CLOCK_CONFIGURATION,
    GameClock,
)
from pyggp.interpreters import Move, Role, State, View


def test_send_start() -> None:
    agent: Agent = Agent()
    agent.prepare_match = mock.MagicMock()  # type: ignore[assignment]
    role: Role = Role(gdl.Subrelation(gdl.Number(0)))
    ruleset: gdl.Ruleset = gdl.Ruleset()
    startclock_config: GameClock.Configuration = DEFAULT_START_CLOCK_CONFIGURATION
    playclock_config: GameClock.Configuration = DEFAULT_PLAY_CLOCK_CONFIGURATION
    actor = LocalActor(agent=agent)
    actor.send_start(
        role=role,
        ruleset=ruleset,
        startclock_config=startclock_config,
        playclock_config=playclock_config,
    )
    agent.prepare_match.assert_called_once_with(
        role,
        ruleset,
        startclock_config,
        playclock_config,
    )


def test_send_start_raises_on_no_agent() -> None:
    actor = LocalActor(agent=mock.MagicMock())
    actor.agent = None
    with pytest.raises(AgentIsNoneLocalActorError):
        actor.send_start(
            role=mock.MagicMock(),
            ruleset=mock.MagicMock(),
            startclock_config=mock.MagicMock(),
            playclock_config=mock.MagicMock(),
        )


def test_send_play() -> None:
    agent: Agent = Agent()
    agent.calculate_move = mock.MagicMock(return_value=Move(gdl.Subrelation(gdl.Number(0))))  # type: ignore[assignment]
    ply: int = 0
    view: View = View(State(frozenset()))
    actor = LocalActor(agent=agent)
    playclock: GameClock = GameClock.from_configuration(DEFAULT_NO_TIMEOUT_CONFIGURATION)
    playclock.total_time_ns = 1000
    actor.playclock = playclock
    actual = actor.send_play(ply, view)
    expected = Move(gdl.Subrelation(gdl.Number(0)))
    agent.calculate_move.assert_called_once_with(ply, 1000, view)
    assert actual == expected


def test_send_play_raises_on_no_agent() -> None:
    actor = LocalActor(playclock=mock.MagicMock(), agent=mock.MagicMock())
    actor.agent = None
    with pytest.raises(AgentIsNoneLocalActorError):
        actor.send_play(
            ply=mock.MagicMock(),
            view=mock.MagicMock(),
        )


def test_send_abort() -> None:
    agent: Agent = Agent()
    agent.abort_match = mock.MagicMock()  # type: ignore[assignment]
    actor = LocalActor(agent=agent)
    actor.send_abort()
    agent.abort_match.assert_called_once_with()


def test_send_abort_raises_on_no_agent() -> None:
    actor = LocalActor(agent=mock.MagicMock())
    actor.agent = None
    with pytest.raises(AgentIsNoneLocalActorError):
        actor.send_abort()


def test_send_stop() -> None:
    agent: Agent = Agent()
    agent.conclude_match = mock.MagicMock()  # type: ignore[assignment]
    actor = LocalActor(agent=agent)
    view: View = View(State(frozenset()))
    actor.send_stop(view)
    agent.conclude_match.assert_called_once_with(view)


def test_send_stop_raises_on_no_agent() -> None:
    actor = LocalActor(agent=mock.MagicMock())
    actor.agent = None
    with pytest.raises(AgentIsNoneLocalActorError):
        actor.send_stop(
            view=mock.MagicMock(),
        )


def test_dunder_post_init() -> None:
    agent: Agent = Agent()
    actor = LocalActor(agent=agent)
    assert actor.agent == agent


def test_dunder_post_init_raises_on_no_agent() -> None:
    with pytest.raises(AgentIsNoneLocalActorError):
        LocalActor()
