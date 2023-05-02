import datetime
import math
from typing import Final, Mapping, Union

import inflection


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
