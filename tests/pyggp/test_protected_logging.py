import datetime
from typing import Union

import pytest

from pyggp._logging import format_amount, format_timedelta, inflect


@pytest.mark.parametrize(
    ("noun", "count", "expected"),
    [
        ("cat", 0, "0 cats"),
        ("cat", 1, "1 cat"),
        ("cat", 2, "2 cats"),
    ],
)
def test_inflect(noun: str, count: int, expected: str) -> None:
    assert inflect(noun, count) == expected


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (datetime.timedelta(seconds=0), "0s"),
        (0, "0s"),
        (0.0, "0s"),
        (float("inf"), "∞s"),
        (datetime.timedelta(seconds=0.1), "0.10s"),
        (datetime.timedelta(seconds=20), "20.00s"),
        (datetime.timedelta(seconds=60), "60.00s"),
        (datetime.timedelta(seconds=61), "01:01"),
        (datetime.timedelta(seconds=61, hours=1), str(datetime.timedelta(seconds=61, hours=1))),
        (datetime.timedelta(seconds=0.99), "0.99s"),
        (datetime.timedelta(seconds=0.099), "99ms"),
        (datetime.timedelta(seconds=0.001), "1ms"),
        (datetime.timedelta(seconds=0.0005), "0.5000ms"),
        (datetime.timedelta(seconds=0.00001), "0.0100ms"),
        (datetime.timedelta(seconds=0.000001), "0.0010ms"),
    ],
)
def test_format_timedelta(delta: Union[float, int, datetime.timedelta], expected: str) -> None:
    actual = format_timedelta(delta)
    assert actual == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, "0"),
        (0.0, "0"),
        (0.001, "0"),
        (0.01, "0.01"),
        (1, "1"),
        (1.0, "1"),
        (1.1, "1.1"),
        (1.12, "1.12"),
        (1.123, "1.12"),
        (1.1234, "1.12"),
        (1.126, "1.13"),
        (1_000, "1k"),
        (1_000_000, "1M"),
        (999_990, "999.99k"),
        (1_500, "1.5k"),
        (1_500_000, "1.5M"),
        (1_000.123, "1k"),
        (1_000_000_000, "1G"),
        (1_050_000_000, "1.05G"),
        (1_000_000_000_000, "1T"),
        (1_000_000_000_000_000, "1P"),
        (1_000_000_000_000_000_000, "1E"),
        (1_000_000_000_000_000_000_000, "1Z"),
        (1_000_000_000_000_000_000_000_000, "1Y"),
        (1_000_000_000_000_000_000_000_000_000, "1R"),
        (1_000_000_000_000_000_000_000_000_000_000, "1Q"),
        (1_000_000_000_000_000_000_000_000_000_000_000, "1000Q"),
    ],
)
def test_format_amount(amount: Union[float, int], expected: str) -> None:
    actual = format_amount(amount)
    assert actual == expected
