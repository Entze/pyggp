from unittest import mock

from pyggp.actors import LocalActor
from pyggp.agents import Agent
from pyggp.gameclocks import GameClock, GameClockConfiguration
from pyggp.gdl import ConcreteRole, Ruleset, State


def test_send_start_as_expected() -> None:
    agent: Agent = Agent()
    agent.prepare_match = mock.MagicMock()  # type: ignore[assignment]
    role: ConcreteRole = 0
    ruleset: Ruleset = Ruleset()
    startclock_config: GameClockConfiguration = GameClockConfiguration.default_startclock_config()
    playclock_config: GameClockConfiguration = GameClockConfiguration.default_playclock_config()
    actor = LocalActor(agent)
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


def test_send_play_as_expected() -> None:
    agent: Agent = Agent()
    agent.calculate_move = mock.MagicMock(return_value=0)  # type: ignore[assignment]
    move_nr: int = 0
    view: State = frozenset()
    actor = LocalActor(agent)
    playclock: GameClock = GameClock(GameClockConfiguration.default_playclock_config())
    actor.playclock = playclock
    with mock.patch("pyggp.actors.GameClock.total_time_ns", new_callable=mock.PropertyMock) as mock_total_time_ns:
        mock_total_time_ns.return_value = 1000
        actual = actor.send_play(move_nr, view)
    expected = 0
    agent.calculate_move.assert_called_once_with(move_nr, 1000, view)
    assert actual == expected


def test_send_abort_as_expected() -> None:
    agent: Agent = Agent()
    agent.abort_match = mock.MagicMock()  # type: ignore[assignment]
    actor = LocalActor(agent)
    actor.send_abort()
    agent.abort_match.assert_called_once_with()


def test_send_stop_as_expected() -> None:
    agent: Agent = Agent()
    agent.conclude_match = mock.MagicMock()  # type: ignore[assignment]
    actor = LocalActor(agent)
    view: State = frozenset()
    actor.send_stop(view)
    agent.conclude_match.assert_called_once_with(view)
