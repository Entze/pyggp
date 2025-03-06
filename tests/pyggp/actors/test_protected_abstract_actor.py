from unittest import mock

import pytest

import pyggp.game_description_language as gdl
from pyggp.actors import _AbstractActor
from pyggp.engine_primitives import Role, State, View
from pyggp.exceptions.actor_exceptions import TimeoutActorError
from pyggp.gameclocks import DEFAULT_PLAY_CLOCK_CONFIGURATION, DEFAULT_START_CLOCK_CONFIGURATION, GameClock


@mock.patch.object(_AbstractActor, "__abstractmethods__", frozenset())
def test_send_start_raises_on_expired_startclock() -> None:
    actor = _AbstractActor()
    actor._send_start = mock.MagicMock()  # type: ignore[assignment]
    role: Role = Role(gdl.Subrelation(gdl.Number(0)))
    ruleset: gdl.Ruleset = gdl.Ruleset()
    startclock_config: GameClock.Configuration = DEFAULT_START_CLOCK_CONFIGURATION
    playclock_config: GameClock.Configuration = DEFAULT_PLAY_CLOCK_CONFIGURATION
    with mock.patch.object(GameClock, "is_expired", new_callable=mock.PropertyMock) as mock_is_expired:
        mock_is_expired.return_value = True
        with pytest.raises(TimeoutActorError):
            actor.send_start(
                role=role,
                ruleset=ruleset,
                startclock_configuration=startclock_config,
                playclock_configuration=playclock_config,
            )


@mock.patch.object(_AbstractActor, "__abstractmethods__", frozenset())
def test_send_play_raises_on_expired_playclock() -> None:
    actor = _AbstractActor()
    actor.playclock = GameClock.from_configuration(DEFAULT_PLAY_CLOCK_CONFIGURATION)
    # pylint: disable=protected-access
    actor._send_play = mock.MagicMock(return_value=0)  # type: ignore[assignment]
    with mock.patch("pyggp.gameclocks.GameClock.is_expired", new_callable=mock.PropertyMock) as mock_is_expired:
        mock_is_expired.return_value = True
        with pytest.raises(TimeoutActorError):
            actor.send_play(0, View(State(frozenset())))
