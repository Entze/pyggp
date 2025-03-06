from typing import Type

import pytest

from pyggp.exceptions.gameclock_exceptions import (
    DelayInvalidFloatGameClockConfigurationError,
    GameClockConfigurationError,
    IncrementInvalidFloatGameClockConfigurationError,
    MalformedStringGameClockConfigurationError,
    TotalTimeInvalidFloatGameClockConfigurationError,
)
from pyggp.gameclocks import GameClock


@pytest.mark.parametrize(
    ("string", "expected_total_time", "expected_increment", "expected_delay"),
    [
        ("60 | 10 d5", 60.0, 10.0, 5.0),
        ("60 | 10", 60.0, 10.0, 0.0),
        ("60 d5", 60.0, 0.0, 5.0),
        ("60", 60.0, 0.0, 0.0),
        ("60.5", 60.5, 0.0, 0.0),
        ("60.5 | 10.5", 60.5, 10.5, 0.0),
        ("60.5 | 10.5 d5.5", 60.5, 10.5, 5.5),
        ("60.5 d5.5", 60.5, 0.0, 5.5),
        ("inf", float("inf"), 0.0, 0.0),
        ("0 dinf", 0.0, 0.0, float("inf")),
        ("∞", float("inf"), 0.0, 0.0),
        ("0 d∞", 0.0, 0.0, float("inf")),
        ("d20", 0.0, 0.0, 20.0),
        ("d     10", 0.0, 0.0, 10.0),
    ],
)
def test_from_str(string: str, expected_total_time: float, expected_increment: float, expected_delay: float) -> None:
    actual = GameClock.Configuration.from_str(string)
    expected = GameClock.Configuration(
        total_time=expected_total_time,
        increment=expected_increment,
        delay=expected_delay,
    )
    assert actual == expected


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        ("", MalformedStringGameClockConfigurationError),
        ("60 | 10 d", MalformedStringGameClockConfigurationError),
        ("60 | 10 d5.5.5", DelayInvalidFloatGameClockConfigurationError),
        ("| 10", MalformedStringGameClockConfigurationError),
        ("ab | c de", TotalTimeInvalidFloatGameClockConfigurationError),
        ("60 | c de", IncrementInvalidFloatGameClockConfigurationError),
        ("60 | 10 de", DelayInvalidFloatGameClockConfigurationError),
    ],
)
def test_from_str_raises(string: str, expected: Type[GameClockConfigurationError]) -> None:
    with pytest.raises(expected):
        GameClock.Configuration.from_str(string)


@pytest.mark.parametrize(
    ("total_time", "increment", "delay", "expected"),
    [
        (60.0, 10.0, 5.0, "60.0 | 10.0 d5.0"),
        (60.0, 10.0, 0.0, "60.0 | 10.0 d0.0"),
        (60.0, 0.0, 5.0, "60.0 | 0.0 d5.0"),
        (0.0, 10.0, 5.0, "0.0 | 10.0 d5.0"),
        (60.0, 10.0, float("inf"), "60.0 | 10.0 d∞"),
        (60.0, float("inf"), 5.0, "60.0 | ∞ d5.0"),
        (float("inf"), 10.0, 5.0, "∞ | 10.0 d5.0"),
    ],
)
def test_dunder_str(total_time: float, increment: float, delay: float, expected: str) -> None:
    configuration = GameClock.Configuration(total_time, increment, delay)
    actual = str(configuration)
    assert actual == expected
