from unittest import mock

import pytest
from pyggp.gameclocks import GameClock


def test_in_with_stmt() -> None:
    game_clock = GameClock(total_time_ns=100, increment_ns=0, delay_ns=0)
    assert game_clock.total_time_ns == 100
    assert game_clock.last_delta_ns is None
    assert game_clock.last_delta is None
    assert game_clock.is_expired is False
    with mock.patch("time.monotonic_ns", side_effect=(0, 50)), game_clock as total_time_ns:
        assert total_time_ns == 100
    assert game_clock.total_time_ns == 50
    assert game_clock.last_delta_ns == 50
    assert game_clock.last_delta == 50 / 1e9
    assert game_clock.is_expired is False


def test_in_with_stmt_with_inf_increment() -> None:
    game_clock = GameClock(total_time_ns=100, increment_ns=0, delay_ns=0, increment_is_inf=True)
    assert game_clock.total_time_ns == 100
    assert game_clock.can_timeout is True
    assert game_clock.last_delta_ns is None
    assert game_clock.last_delta is None
    assert game_clock.is_expired is False
    with mock.patch("time.monotonic_ns", side_effect=(0, 50)), game_clock as total_time_ns:
        assert total_time_ns == 100
    assert game_clock.total_time_ns == 50
    assert game_clock.can_timeout is False
    assert game_clock.last_delta_ns == 50
    assert game_clock.last_delta == 50 / 1e9
    assert game_clock.is_expired is False


def test_in_with_stmt_timeout() -> None:
    game_clock = GameClock(total_time_ns=100, increment_ns=100, delay_ns=0)
    assert game_clock.total_time_ns == 100
    assert game_clock.last_delta_ns is None
    assert game_clock.last_delta is None
    assert game_clock.is_expired is False
    with mock.patch("time.monotonic_ns", side_effect=(0, 150)), game_clock as total_time_ns:
        assert total_time_ns == 100
    assert game_clock.total_time_ns == -50
    assert game_clock.last_delta_ns == 150
    assert game_clock.last_delta == 150 / 1e9
    assert game_clock.is_expired is True


@pytest.mark.parametrize(
    ("total_time", "increment", "delay", "expected"),
    [
        (60.0, 10.0, 5.0, GameClock(total_time_ns=60_000_000_000, increment_ns=10_000_000_000, delay_ns=5_000_000_000)),
        (60.0, 10.0, 0.0, GameClock(total_time_ns=60_000_000_000, increment_ns=10_000_000_000, delay_ns=0)),
        (60.0, 0.0, 5.0, GameClock(total_time_ns=60_000_000_000, increment_ns=0, delay_ns=5_000_000_000)),
        (0.0, 10.0, 5.0, GameClock(total_time_ns=0, increment_ns=10_000_000_000, delay_ns=5_000_000_000)),
        (
            60.0,
            10.0,
            float("inf"),
            GameClock(total_time_ns=60_000_000_000, increment_ns=10_000_000_000, delay_ns=0, delay_is_inf=True),
        ),
        (
            60.0,
            float("inf"),
            5.0,
            GameClock(total_time_ns=60_000_000_000, increment_ns=0, delay_ns=5_000_000_000, increment_is_inf=True),
        ),
        (
            float("inf"),
            10.0,
            5.0,
            GameClock(total_time_ns=0, increment_ns=10_000_000_000, delay_ns=5_000_000_000, total_time_is_inf=True),
        ),
    ],
)
def test_from_configuration(total_time: float, increment: float, delay: float, expected: GameClock) -> None:
    configuration = GameClock.Configuration(total_time=total_time, increment=increment, delay=delay)
    actual = GameClock.from_configuration(configuration)
    assert actual == expected
    assert actual.total_time == total_time
    assert actual.increment == increment
    assert actual.delay == delay


@pytest.mark.parametrize(
    ("gameclock", "slack", "expected"),
    [
        (GameClock(total_time_ns=60_000_000_000, increment_ns=10_000_000_000, delay_ns=5_000_000_000), 0.0, 65.0),
        (GameClock(total_time_ns=60_000_000_000, increment_ns=10_000_000_000, delay_ns=5_000_000_000), 0.5, 65.5),
    ],
)
def test_get_timeout(gameclock: GameClock, slack: float, expected: float) -> None:
    actual = gameclock.get_timeout(slack=slack)
    assert actual == expected
