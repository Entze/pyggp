from unittest import mock

import pytest
from pyggp.actors import Actor
from pyggp.exceptions.actor_exceptions import ActorPlayclockIsNoneError, ActorTimeoutError
from pyggp.gameclocks import GameClock, GameClockConfiguration
from pyggp.gdl import ConcreteRole, Ruleset


def test_send_start_raises_if_the_startclock_expires() -> None:
    actor: Actor = Actor()
    # pylint: disable=protected-access
    actor._send_start = mock.MagicMock()  # type: ignore[assignment]
    role: ConcreteRole = 0
    ruleset: Ruleset = Ruleset()
    startclock_config: GameClockConfiguration = GameClockConfiguration.default_startclock_config()
    playclock_config: GameClockConfiguration = GameClockConfiguration.default_playclock_config()
    with mock.patch("pyggp.gameclocks.GameClock.is_expired", new_callable=mock.PropertyMock) as mock_is_expired:
        mock_is_expired.return_value = True
        with pytest.raises(ActorTimeoutError):
            actor.send_start(
                role=role,
                ruleset=ruleset,
                startclock_config=startclock_config,
                playclock_config=playclock_config,
            )


def test_send_play_raises_if_the_playclock_is_none() -> None:
    actor: Actor = Actor()
    actor.playclock = None
    with pytest.raises(ActorPlayclockIsNoneError):
        actor.send_play(0, frozenset())


def test_send_play_raises_if_the_playclock_expired() -> None:
    actor: Actor = Actor()
    actor.playclock = GameClock(GameClockConfiguration.default_playclock_config())
    # pylint: disable=protected-access
    actor._send_play = mock.MagicMock(return_value=0)  # type: ignore[assignment]
    with mock.patch("pyggp.gameclocks.GameClock.is_expired", new_callable=mock.PropertyMock) as mock_is_expired:
        mock_is_expired.return_value = True
        with pytest.raises(ActorTimeoutError):
            actor.send_play(0, frozenset())
