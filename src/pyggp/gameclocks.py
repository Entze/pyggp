"""Game clocks for GGP."""
import contextlib
import re
import time
from dataclasses import dataclass
from types import TracebackType
from typing import Optional, Tuple, Type

from typing_extensions import Self

from pyggp._logging import format_timedelta
from pyggp.exceptions.gameclock_exceptions import (
    DelayInvalidFloatGameClockConfigurationError,
    IncrementInvalidFloatGameClockConfigurationError,
    MalformedStringGameClockConfigurationError,
    TotalTimeInvalidFloatGameClockConfigurationError,
)


@dataclass(frozen=True)
class GameClockConfiguration:
    """Configuration for a game clock.

    All units are in seconds.

    """

    total_time: float = 0.0
    """Total time in seconds.

    This is the time that will be decremented.

    """
    increment: float = 0.0
    """Increment in seconds.

    This is the time that will be added to the total time after each move.

    """
    delay: float = 60.0
    """Delay in seconds.

    This is the time that will be removed from the delta before the total time is decremented.

    """

    def __repr__(self) -> str:
        """Represents the game clock configuration.

        Returns:
            Representation of the game clock configuration.

        """
        return f"{self.__class__.__name__}({self})"

    def __str__(self) -> str:
        """String of the game clock configuration.

        Returns:
            String of the game clock configuration.

        """
        return f"{self.total_time} | {self.increment} d{self.delay if self.delay != float('inf') else '∞'}"

    @classmethod
    def from_str(cls, string: str) -> Self:
        """Create a game clock configuration from a string."""
        sanity_check_re = re.compile(r"^(\S+)?(\s*\|\s*\S+)?(\s*d\s*\S+)?$")
        if not sanity_check_re.match(string):
            raise MalformedStringGameClockConfigurationError(string=string)

        # Disables SLF001 (Private member accessed). Because the private methods are helpers for this method.
        _full_strs = GameClockConfiguration._full_spec_from_str(string)  # noqa: SLF001
        _increment_strs = GameClockConfiguration._increment_only_spec_from_str(string)  # noqa: SLF001
        _delay_strs = GameClockConfiguration._delay_only_spec_from_str(string)  # noqa: SLF001
        _bare_strs = GameClockConfiguration._bare_spec_from_str(string)  # noqa: SLF001
        _bare_delay_strs = GameClockConfiguration._bare_delay_spec_from_str(string)  # noqa: SLF001
        total_time_str = _full_strs[0] or _increment_strs[0] or _delay_strs[0] or _bare_strs[0] or _bare_delay_strs[0]
        increment_str = _full_strs[1] or _increment_strs[1] or _bare_strs[1] or _bare_delay_strs[1]
        delay_str = _full_strs[2] or _delay_strs[2] or _bare_strs[2] or _bare_delay_strs[2]

        if total_time_str is None and delay_str is None:
            raise MalformedStringGameClockConfigurationError(string=string)

        total_time = 0.0
        increment = 0.0
        delay = 0.0

        if total_time_str is not None:
            total_time_str = total_time_str.replace("∞", "inf")
            try:
                total_time = float(total_time_str)
            except ValueError:
                raise TotalTimeInvalidFloatGameClockConfigurationError(string=string) from None

        if increment_str is not None:
            increment_str = increment_str.replace("∞", "inf")
            try:
                increment = float(increment_str)
            except ValueError:
                raise IncrementInvalidFloatGameClockConfigurationError(string=string) from None

        if delay_str is not None:
            delay_str = delay_str.replace("∞", "inf")
            try:
                delay = float(delay_str)
            except ValueError:
                raise DelayInvalidFloatGameClockConfigurationError(string=string) from None

        return cls(total_time=total_time, increment=increment, delay=delay)

    @classmethod
    def default_startclock_config(cls) -> Self:
        """Create a game clock configuration with a total time of 60 seconds.

        Returns:
            A game clock configuration with a total time of 60 seconds.

        """
        return cls(total_time=60.0, increment=0.0, delay=0.0)

    @classmethod
    def default_playclock_config(cls) -> Self:
        """Create a game clock configuration with a delay of 60 seconds.

        Returns:
            A game clock configuration with a delay of 60 seconds.

        """
        return cls(total_time=0.0, increment=0.0, delay=60.0)

    @classmethod
    def default_no_timeout_config(cls) -> Self:
        """Create a game clock configuration that cannot time out.

        Returns:
            A game clock configuration that cannot time out.

        """
        return cls(total_time=0.0, increment=0.0, delay=float("inf"))

    @staticmethod
    def _full_spec_from_str(string: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        full_spec_re = re.compile(r"^(?P<total_time>\S+)\s*\|\s*(?P<increment>\S+)\s*d\s*(?P<delay>\S+)$")
        full_spec_match = full_spec_re.match(string)
        if not full_spec_match:
            return None, None, None
        return full_spec_match.group("total_time"), full_spec_match.group("increment"), full_spec_match.group("delay")

    @staticmethod
    def _increment_only_spec_from_str(string: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        increment_only_spec_re = re.compile(r"^(?P<total_time>\S+)\s*\|\s*(?P<increment>\S+)$")
        increment_only_spec_match = increment_only_spec_re.match(string)

        if not increment_only_spec_match:
            return None, None, None
        return increment_only_spec_match.group("total_time"), increment_only_spec_match.group("increment"), None

    @staticmethod
    def _delay_only_spec_from_str(string: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        delay_only_spec_re = re.compile(r"^(?P<total_time>\S+)\s*d\s*(?P<delay>\S+)$")
        delay_only_spec_match = delay_only_spec_re.match(string)

        if not delay_only_spec_match:
            return None, None, None
        return delay_only_spec_match.group("total_time"), None, delay_only_spec_match.group("delay")

    @staticmethod
    def _bare_spec_from_str(string: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        bare_spec_re = re.compile(r"^(?P<total_time>[^d]\S*)$")
        bare_spec_match = bare_spec_re.match(string)

        if not bare_spec_match:
            return None, None, None
        return bare_spec_match.group("total_time"), None, None

    @staticmethod
    def _bare_delay_spec_from_str(string: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        bare_spec_re = re.compile(r"^d\s*(?P<delay>\S+)$")
        bare_spec_match = bare_spec_re.match(string)

        if not bare_spec_match:
            return None, None, None
        return None, None, bare_spec_match.group("delay")


class GameClock(contextlib.AbstractContextManager[int]):
    """A game clock that can be used to track the time remaining for a player.

    The game clock is a context manager that can be used to track the time remaining for a player. Use the with
    statement to start the game clock. The game clock will automatically stop when the with statement exits.

    Example:
        >>> game_clock_config = GameClockConfiguration(total_time=0.1, increment=0.0, delay=0.0)
        >>> game_clock = GameClock(game_clock_config)
        >>> with game_clock as total_time_left_ns:
        ...     time.sleep(0.2)
        >>> game_clock.is_expired
        True

    """

    def __init__(self, game_clock_config: GameClockConfiguration) -> None:
        """Create a new game clock.

        Args:
            game_clock_config: The configuration for the game clock.

        See Also:
            :class:`GameClockConfig`

        """
        self._total_time_is_inf = game_clock_config.total_time == float("inf")
        self._increment_is_inf = game_clock_config.increment == float("inf")
        self._delay_is_inf = game_clock_config.delay == float("inf")
        try:
            self._total_time_ns = int(game_clock_config.total_time * 1e9)
        except OverflowError:
            self._total_time_ns = int(2**63 - 1)
        self._increment = game_clock_config.increment
        try:
            self._increment_ns = int(game_clock_config.increment * 1e9)
        except OverflowError:
            self._increment_ns = int(2**63 - 1)
        self._delay = game_clock_config.delay
        try:
            self._delay_ns = int(game_clock_config.delay * 1e9)
        except OverflowError:
            self._delay_ns = int(2**63 - 1)
        self.__start: Optional[int] = None
        self._last_delta_ns: Optional[int] = None

    def __enter__(self) -> int:
        """Start the game clock.

        See Also:
            :meth:`start`

        Returns:
            The current total time left in nanoseconds.

        """
        self.start()
        return self._total_time_ns

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Stop the game clock."""
        self.stop()

    def __repr__(self) -> str:
        """Get a string representation of the game clock.

        Returns:
            A string representation of the game clock.

        """
        if self.is_expired:
            return f"0 | {self.__increment_repr} d{self.__delay_repr}"
        return f"{self.__total_time_repr} | {self.__increment_repr} d{self.__delay_repr}"

    @property
    def _can_timeout(self) -> bool:
        return not self._total_time_is_inf and not self._delay_is_inf

    @property
    def __total_time_repr(self) -> str:
        if self._total_time_is_inf:
            return "∞"
        return format_timedelta(self.total_time)

    @property
    def __increment_repr(self) -> str:
        if self._increment_is_inf:
            return "∞"
        if self._increment.is_integer():
            return f"{int(self._increment)}"
        return f"{self._increment}"

    @property
    def __delay_repr(self) -> str:
        if self._delay_is_inf:
            return "∞"
        if self._delay.is_integer():
            return f"{int(self._delay)}"
        return f"{self._delay}"

    @property
    def is_expired(self) -> bool:
        """Check if the game clock is expired."""
        return self._can_timeout and self._total_time_ns < 0

    @property
    def total_time(self) -> float:
        """Get the total time left in seconds."""
        if self._total_time_is_inf:
            return float("inf")
        return self._total_time_ns / 1e9

    @property
    def total_time_ns(self) -> int:
        """Get the total time left in nanoseconds."""
        return self._total_time_ns

    @property
    def last_delta_ns(self) -> Optional[int]:
        """Last time delta (time elapsed between calling start and stop) in nanoseconds."""
        return self._last_delta_ns

    @property
    def last_delta(self) -> Optional[float]:
        """Last time delta (time elapsed between calling start and stop) in seconds."""
        if self._last_delta_ns is None:
            return None
        return self._last_delta_ns / 1e9

    def start(self) -> None:
        """Start the game clock.

        See Also:
            :meth:`stop`
            :meth:`__enter__`

        """
        self.__start = time.monotonic_ns()

    def stop(self) -> None:
        """Stop the game clock.

        See Also:
            :meth:`start`
            :meth:`__exit__`

        """
        stop = time.monotonic_ns()
        if self.__start is not None and self._can_timeout:
            time_delta = stop - self.__start
            clock_delta = max(0, time_delta - self._delay_ns)
            self._total_time_ns -= clock_delta
            if not self.is_expired:
                self._total_time_ns += self._increment_ns
            self._last_delta_ns = stop - self.__start
            self.__start = None

        if self._increment_is_inf:
            self._total_time_is_inf = True

    def get_timeout(self, slack: float = 0.0) -> float:
        """Get the timeout for the current move.

        This method gives an estimate when the current move can be stopped, as the game clock will be expired.

        Args:
            slack: The slack in seconds to add to the timeout.

        Returns:
            The timeout in seconds.

        """
        return max(0.0, self.total_time + self._delay + slack)
