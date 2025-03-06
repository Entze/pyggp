"""Game clocks for GGP."""

import contextlib
import re
import time
from dataclasses import dataclass, field
from types import TracebackType
from typing import Final, Optional, Tuple, Type

from typing_extensions import Self

from pyggp._logging import format_ns, format_timedelta
from pyggp.exceptions.gameclock_exceptions import (
    DelayInvalidFloatGameClockConfigurationError,
    IncrementInvalidFloatGameClockConfigurationError,
    MalformedStringGameClockConfigurationError,
    TotalTimeInvalidFloatGameClockConfigurationError,
)

ONE_HOUR_IN_NS: Final[int] = 3600 * 1_000_000_000


@dataclass
class GameClock:
    """A game clock that can be used to track the time remaining for a player.

    The game clock is a context manager that can be used to track the time remaining for a player. Use the with
    statement to start the game clock. The game clock will automatically stop when the with statement exits.

    Example:
        >>> game_clock_config = GameClock.Configuration(total_time=0.1, increment=0.0, delay=0.0)
        >>> game_clock = GameClock.from_configuration(game_clock_config)
        >>> with game_clock as total_time_left_ns:
        ...     time.sleep(0.2)
        >>> game_clock.is_expired
        True

    """

    # region Inner Classes

    @dataclass(frozen=True)
    class Configuration:
        """Configuration for a game clock.

        All units are in seconds.

        """

        # region Attributes and Properties

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

        @property
        def total_time_ns(self) -> int:
            """Total time in nanoseconds."""
            if self.total_time == float("inf"):
                return ONE_HOUR_IN_NS * 24
            return int(self.total_time * 1e9)

        @property
        def increment_ns(self) -> int:
            """Increment in nanoseconds."""
            if self.increment == float("inf"):
                return ONE_HOUR_IN_NS * 24
            return int(self.increment * 1e9)

        @property
        def delay_ns(self) -> int:
            """Delay in nanoseconds."""
            if self.delay == float("inf"):
                return ONE_HOUR_IN_NS * 24
            return int(self.delay * 1e9)

        # endregion

        # region Magic Methods

        def __str__(self) -> str:
            """String of the game clock configuration.

            Returns:
                String of the game clock configuration.

            """
            return (
                f"{self.total_time if self.total_time != float('inf') else '∞'} "
                f"| {self.increment if self.increment != float('inf') else '∞'} "
                f"d{self.delay if self.delay != float('inf') else '∞'}"
            )

        def __rich__(self) -> str:
            if self.total_time == 0.0 and self.increment == 0.0 and self.delay == 0.0:
                return "0"
            total_time_str = f"{self.total_time}" if self.total_time != float("inf") else "∞"
            increment_str = f"{self.increment}" if self.increment != float("inf") else "∞"
            delay_str = f"{self.delay}" if self.delay != float("inf") else "∞"
            if self.total_time == 0.0 and self.increment == 0.0:
                return f"d{delay_str}"
            if self.increment == 0.0 and self.delay == 0.0:
                return total_time_str
            if self.increment == 0.0:
                return f"{total_time_str} d{delay_str}"
            if self.delay == 0.0:
                return f"{total_time_str} | {increment_str}"
            return f"{total_time_str} | {increment_str} d{delay_str}"

        # endregion

        # region Constructors

        @classmethod
        def from_str(cls, string: str) -> Self:
            """Create a game clock configuration from a string."""
            sanity_check_re = re.compile(r"^(\S+)?(\s*\|\s*\S+)?(\s*d\s*\S+)?$")
            if not sanity_check_re.match(string):
                raise MalformedStringGameClockConfigurationError(string=string)

            # Disables SLF001 (Private member accessed). Because the private methods are helpers for this method.
            _full_strs = GameClock.Configuration._full_spec_from_str(string)  # noqa: SLF001
            _increment_strs = GameClock.Configuration._increment_only_spec_from_str(string)  # noqa: SLF001
            _delay_strs = GameClock.Configuration._delay_only_spec_from_str(string)  # noqa: SLF001
            _bare_strs = GameClock.Configuration._bare_spec_from_str(string)  # noqa: SLF001
            _bare_delay_strs = GameClock.Configuration._bare_delay_spec_from_str(string)  # noqa: SLF001
            total_time_str = (
                _full_strs[0] or _increment_strs[0] or _delay_strs[0] or _bare_strs[0] or _bare_delay_strs[0]
            )
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

        # endregion

        # region Static Methods

        @staticmethod
        def _full_spec_from_str(string: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
            full_spec_re = re.compile(r"^(?P<total_time>\S+)\s*\|\s*(?P<increment>\S+)\s*d\s*(?P<delay>\S+)$")
            full_spec_match = full_spec_re.match(string)
            if not full_spec_match:
                return None, None, None
            return (
                full_spec_match.group("total_time"),
                full_spec_match.group("increment"),
                full_spec_match.group("delay"),
            )

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

        # endregion

    # endregion

    # region Attributes and Properties

    total_time_ns: int
    "Total time in nanoseconds."
    increment_ns: int
    "Increment in nanoseconds."
    delay_ns: int
    "Delay in nanoseconds."
    last_delta_ns: Optional[int] = field(default=None)
    "Last delta (gap between start and stop) in nanoseconds."
    total_time_is_inf: bool = field(default=False)
    "Whether the total time can decrease."
    increment_is_inf: bool = field(default=False)
    "Whether the increment can decrease."
    delay_is_inf: bool = field(default=False)
    "Whether the delay can decrease."
    __start: Optional[int] = field(default=None, init=False, repr=False)

    @property
    def can_timeout(self) -> bool:
        """Check if the game clock can time out."""
        return not self.total_time_is_inf and not self.delay_is_inf

    @property
    def is_expired(self) -> bool:
        """Check if the game clock is expired."""
        return self.can_timeout and self.total_time_ns < 0

    @property
    def total_time(self) -> float:
        """Total time in seconds."""
        if self.total_time_is_inf:
            return float("inf")
        return self.total_time_ns / 1e9

    @property
    def increment(self) -> float:
        """Increment in seconds."""
        if self.increment_is_inf:
            return float("inf")
        return self.increment_ns / 1e9

    @property
    def delay(self) -> float:
        """Delay in seconds."""
        if self.delay_is_inf:
            return float("inf")
        return self.delay_ns / 1e9

    @property
    def last_delta(self) -> Optional[float]:
        """Last delta (gap between start and stop) in seconds."""
        if self.last_delta_ns is None:
            return None
        return self.last_delta_ns / 1e9

    # endregion

    # region Constructors

    @classmethod
    def from_configuration(cls, configuration: Configuration) -> Self:
        """Create a game clock from a configuration.

        Args:
            configuration: Configuration

        Returns:
            Game clock

        """
        total_time_ns: int = 0
        with contextlib.suppress(OverflowError):
            total_time_ns = int(configuration.total_time * 1e9)
        increment_ns: int = 0
        with contextlib.suppress(OverflowError):
            increment_ns = int(configuration.increment * 1e9)
        delay_ns: int = 0
        with contextlib.suppress(OverflowError):
            delay_ns = int(configuration.delay * 1e9)
        return cls(
            total_time_ns=total_time_ns,
            increment_ns=increment_ns,
            delay_ns=delay_ns,
            total_time_is_inf=configuration.total_time == float("inf"),
            increment_is_inf=configuration.increment == float("inf"),
            delay_is_inf=configuration.delay == float("inf"),
        )

    # endregion

    # region Magic Methods

    def __enter__(self) -> int:
        """Start the game clock.

        See Also:
            :meth:`start`

        Returns:
            The current total time left in nanoseconds.

        """
        self.start()
        return self.total_time_ns

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Stop the game clock."""
        self.stop()

    def __rich__(self) -> str:
        if not self.can_timeout:
            return format_timedelta(float("inf"))
        return f"{format_ns(self.total_time_ns)}"

    # endregion

    # region Methods

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
        if self.__start is not None and self.can_timeout:
            time_delta = stop - self.__start
            clock_delta = max(0, time_delta - self.delay_ns)
            self.total_time_ns -= clock_delta
            if not self.is_expired:
                self.total_time_ns += self.increment_ns
            self.last_delta_ns = stop - self.__start
            self.__start = None

        if self.increment_is_inf:
            self.total_time_is_inf = True

    def get_timeout(self, slack: float = 0.0) -> float:
        """Get the timeout for the current move.

        This method gives an estimate when the current move can be stopped, as the game clock will be expired. This
        method never returns a negative value.

        Args:
            slack: The slack in seconds to add to the timeout

        Returns:
            The timeout in seconds

        """
        if not self.can_timeout:
            return float("inf")
        return max(0.0, self.total_time + self.delay + slack)

    # endregion


DEFAULT_START_CLOCK_CONFIGURATION: Final[GameClock.Configuration] = GameClock.Configuration(
    total_time=60.0,
    increment=0.0,
    delay=0.0,
)
DEFAULT_PLAY_CLOCK_CONFIGURATION: Final[GameClock.Configuration] = GameClock.Configuration(
    total_time=0.0,
    increment=0.0,
    delay=60.0,
)
DEFAULT_NO_TIMEOUT_CONFIGURATION: Final[GameClock.Configuration] = GameClock.Configuration(
    total_time=0.0,
    increment=0.0,
    delay=float("inf"),
)
