import datetime
from typing import Union

import pytest
from pyggp._logging import format_timedelta, inflect


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
    assert format_timedelta(delta) == expected
