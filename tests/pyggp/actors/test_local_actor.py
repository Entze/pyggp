from unittest import mock

import pyggp.game_description_language as gdl
from pyggp.actors import LocalActor
from pyggp.agents import Agent
from pyggp.engine_primitives import Move, Role, State, View
from pyggp.gameclocks import (
    DEFAULT_NO_TIMEOUT_CONFIGURATION,
    DEFAULT_PLAY_CLOCK_CONFIGURATION,
    DEFAULT_START_CLOCK_CONFIGURATION,
    GameClock,
)


@mock.patch.object(Agent, "__abstractmethods__", set())
def test_send_start() -> None:
    agent: Agent = mock.MagicMock()
    agent.prepare_match = mock.MagicMock()
    role: Role = Role(gdl.Subrelation(gdl.Number(0)))
    ruleset: gdl.Ruleset = gdl.Ruleset()
    startclock_config: GameClock.Configuration = DEFAULT_START_CLOCK_CONFIGURATION
    playclock_config: GameClock.Configuration = DEFAULT_PLAY_CLOCK_CONFIGURATION
    actor = LocalActor(agent=agent)
    actor.send_start(
        role=role,
        ruleset=ruleset,
        startclock_configuration=startclock_config,
        playclock_configuration=playclock_config,
    )
    agent.prepare_match.assert_called_once_with(
        role,
        ruleset,
        startclock_config,
        playclock_config,
    )


def test_send_play() -> None:
    agent: Agent = mock.MagicMock()
    agent.calculate_move = mock.MagicMock(return_value=Move(gdl.Subrelation(gdl.Number(0))))
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


def test_send_abort() -> None:
    agent: Agent = mock.MagicMock()
    agent.abort_match = mock.MagicMock()
    actor = LocalActor(agent=agent)
    actor.send_abort()
    agent.abort_match.assert_called_once_with()


def test_send_stop() -> None:
    agent: Agent = mock.MagicMock()
    agent.conclude_match = mock.MagicMock()
    actor = LocalActor(agent=agent)
    view: View = View(State(frozenset()))
    actor.send_stop(view)
    agent.conclude_match.assert_called_once_with(view)
