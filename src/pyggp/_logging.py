import contextlib
import datetime
import logging
import math
import time
from dataclasses import dataclass, field
from types import TracebackType
from typing import TYPE_CHECKING, Any, Final, Iterable, Mapping, Optional, Type, Union

import inflection

# Disables SIM108 (Use ternary operator instead of if-else block). Because: TYPE_CHECKING is an exception.
if TYPE_CHECKING:  # noqa: SIM108
    # TODO: Remove this when python 3.8 is no longer supported.
    NoneContextManager = contextlib.AbstractContextManager[None]
else:
    NoneContextManager = contextlib.AbstractContextManager


def inflect(noun: str, count: int = 0) -> str:
    """Inflect a noun based on a count.

    Args:
        noun: Noun to inflect.
        count: Count to use for inflection.

    Keyword Args:
        with_count: Whether to include the count in the output.

    Examples:
        >>> inflect("cat", 0)
        '0 cats'
        >>> inflect("cat", 1)
        '1 cat'
        >>> inflect("cat", 2)
        '2 cats'

    """
    return f"{count} {inflect_without_count(noun, count)}"


def compact_inflect(noun: str, count: int = 0) -> str:
    return f"{format_amount(count)} {inflect_without_count(noun, count)}"


def inflect_without_count(noun: str, count: int = 0) -> str:
    return inflection.pluralize(noun) if count != 1 else inflection.singularize(noun)


_ONE_MINUTE_IN_S: Final[float] = 60.0
_ONE_HOUR_IN_S: Final[float] = _ONE_MINUTE_IN_S * 60.0
_ONE_HUNDRED_MILLISECONDS_IN_S: Final[float] = 0.1
_ONE_MILLISECOND_IN_S: Final[float] = 0.001


# Disables PLR0911 (too many return statements). Because: This is a function with many exceptional cases.
def format_timedelta(delta: Union[float, int, datetime.timedelta]) -> str:  # noqa: PLR0911
    """Format a timedelta as a human-readable string.

    Args:
        delta: Delta to format. Float and int are interpreted as seconds.

    Returns:
        Human-readable string representation of the timedelta.

    Examples:
        >>> format_timedelta(datetime.timedelta(seconds=0))
        '0s'
        >>> format_timedelta(0.1)
        '0.10s'
        >>> format_timedelta(0.0001)
        '0.1000ms'
        >>> format_timedelta(20)
        '20.00s'
        >>> format_timedelta(60)
        '60.00s'
        >>> format_timedelta(61)
        '01:01'
        >>> format_timedelta(datetime.timedelta(hours=2, minutes=31, seconds=13))
        '2:31:13'

    """
    if delta == float("inf"):
        return "∞s"
    if isinstance(delta, (float, int)):
        delta = datetime.timedelta(seconds=delta)
    assert isinstance(delta, datetime.timedelta)
    total_seconds: float = delta.total_seconds()
    if total_seconds == 0:
        return "0s"
    if total_seconds > _ONE_HOUR_IN_S:
        return str(delta)
    if _ONE_MINUTE_IN_S < total_seconds < _ONE_HOUR_IN_S:
        minutes, seconds = divmod(total_seconds, _ONE_MINUTE_IN_S)
        return f"{int(minutes):02d}:{int(seconds):02d}"
    if total_seconds >= _ONE_HUNDRED_MILLISECONDS_IN_S:
        return f"{total_seconds:.2f}s"
    if total_seconds >= _ONE_MILLISECOND_IN_S:
        return f"{total_seconds * 1000:.0f}ms"
    return f"{total_seconds * 1000:.4f}ms"


_LOGARITHM_SYMBOL_MAP: Final[Mapping[int, str]] = {
    0: "",
    3: "k",
    6: "M",
    9: "G",
    12: "T",
    15: "P",
    18: "E",
    21: "Z",
    24: "Y",
    27: "R",
}


def format_ns(ns: int) -> str:
    return format_timedelta(ns * 1e-9)


def remove_trailing(string: str, *trails: str) -> str:
    for trail in trails:
        while string.endswith(trail):
            string = string[: -len(trail)]
    return string


def format_amount(amount: Union[float, int]) -> str:
    if amount == 0:
        return "0"
    exponent: int = max(0, min(30, math.floor(math.log10(amount))))
    symbol: str = _LOGARITHM_SYMBOL_MAP.get(exponent - (exponent % 3), "Q")
    diminished_amount: float = round(amount / 10 ** (exponent - (exponent % 3)), 2)
    formatted = remove_trailing(f"{diminished_amount:.2f}", "0", ".")
    return f"{formatted}{symbol}"


def format_rate(amount: Union[float, int], delta: Union[float, int, datetime.timedelta]) -> str:
    if delta == 0:
        return "∞"
    if isinstance(delta, datetime.timedelta):
        delta = delta.total_seconds()
    return format_amount(amount / delta)


def format_rate_ns(amount: Union[float, int], delta: int) -> str:
    return format_rate(amount, delta * 1e-9)


def format_iterable(iterable: Iterable[Any], *, pre: str = "{", sep: str = ", ", post: str = "}") -> str:
    return f"{pre}{sep.join(str(item) for item in iterable)}{post}"


def format_sorted_iterable(iterable: Iterable[Any], *, pre: str = "{", sep: str = ", ", post: str = "}") -> str:
    return format_iterable(sorted(iterable), pre=pre, sep=sep, post=post)


def format_set(iterable: Iterable[Any]) -> str:
    return format_iterable(iterable, pre="{", sep=", ", post="}")


def format_sorted_set(iterable: Iterable[Any]) -> str:
    return format_sorted_iterable(iterable, pre="{", sep=", ", post="}")


def format_list(iterable: Iterable[Any]) -> str:
    return format_iterable(iterable, pre="[", sep=", ", post="]")


def format_sorted_list(iterable: Iterable[Any]) -> str:
    return format_sorted_iterable(iterable, pre="[", sep=", ", post="]")


@dataclass
class TimeLogger(NoneContextManager):
    log: logging.Logger
    level: int = field(default=logging.INFO)
    begin_msg: Optional[str] = field(default=None)
    end_msg: Optional[str] = field(default=None)
    abort_msg: Optional[str] = field(default=None)
    start_time: Optional[float] = field(default=None, repr=False)
    stop_time: Optional[float] = field(default=None, repr=False)
    delta: Optional[float] = field(default=None, repr=False)

    def __enter__(self) -> None:
        if self.begin_msg is not None:
            self.log.log(self.level, self.begin_msg)
        self.start_time = time.monotonic()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        assert self.start_time is not None, "Assumption: start_time is not None (__enter__ was called)"
        self.stop_time: float = time.monotonic()
        self.delta = self.stop_time - self.start_time
        if exc_val is not None:
            if self.abort_msg is not None:
                self.log.log(self.level, "%s (after %s)", self.abort_msg, format_timedelta(self.delta))
            else:
                self.log.log(self.level, "Aborted after %s", format_timedelta(self.delta))
        else:
            if self.end_msg is not None:
                self.log.log(self.level, "%s (in %s)", self.end_msg, format_timedelta(self.delta))
            else:
                self.log.log(self.level, "in %s", format_timedelta(self.delta))

        self.start_time = None
        self.stop_time = None


def log_time(
    log: logging.Logger,
    level: int = logging.INFO,
    begin_msg: Optional[str] = None,
    end_msg: Optional[str] = None,
    abort_msg: Optional[str] = None,
) -> TimeLogger:
    return TimeLogger(log=log, level=level, begin_msg=begin_msg, end_msg=end_msg, abort_msg=abort_msg)
