"""Game clocks for GGP."""
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import Self, Type


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

    This is the time that will be removed from the delta of the move.

    """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.total_time} | {self.increment} d{self.delay})"

    @classmethod
    def from_str(cls, string: str) -> Self:
        # TODO: Swap for a proper parser. Very manual parsing
        split = string.split(" ", 3)
        total_time_str: str | None = None
        increment_str: str | None = None
        delay_str: str | None = None
        divider_str: str | None = None
        if len(split) == 1:
            if not split[0].startswith("d"):
                total_time_str = split[0]
            else:
                delay_str = split[0]
        elif len(split) == 2:
            if split[0] != "|":
                total_time_str, delay_str = split
            else:
                divider_str, increment_str = split
        elif len(split) == 3:
            total_time_str, divider_str, increment_str = split
        elif len(split) == 4:
            total_time_str, divider_str, increment_str, delay_str = split
        else:
            raise ValueError(f"Invalid game clock configuration: '{string}'")

        if divider_str is not None and divider_str != "|":
            raise ValueError(
                f"Invalid game clock configuration: '{string}', divider between total time and increment must be '|'."
            )
        if delay_str is not None and not delay_str.startswith("d"):
            raise ValueError(f"Invalid game clock configuration: '{string}', delay '{delay_str}' must start with 'd'.")

        if total_time_str is not None:
            try:
                total_time = float(total_time_str)
            except ValueError as exception:
                raise ValueError(
                    f"Invalid game clock configuration: '{string}', could not parse '{total_time_str}' as float."
                ) from exception
        else:
            total_time = 0.0
        if increment_str is not None:
            try:
                increment = float(increment_str)
            except ValueError as exception:
                raise ValueError(
                    f"Invalid game clock configuration: '{string}', could not parse '{increment_str}' as float"
                ) from exception
        else:
            increment = 0.0
        if delay_str is not None:
            try:
                delay = float(delay_str[1:])
            except ValueError as exception:
                raise ValueError(
                    f"Invalid game clock configuration: '{string}', could not parse '{delay_str}' as float"
                ) from exception
        else:
            delay = 0.0
        return cls(total_time=total_time, increment=increment, delay=delay)

    @classmethod
    def default_startclock_config(cls) -> Self:
        return cls(60.0, 0.0, 0.0)

    @classmethod
    def default_playclock_config(cls) -> Self:
        return cls(0.0, 0.0, 60.0)

    @classmethod
    def default_no_timeout_config(cls) -> Self:
        return cls(0.0, 0.0, float("inf"))


class GameClock(AbstractContextManager[int]):
    """A game clock that can be used to track the time remaining for a player.

    The game clock is a context manager that can be used to track the time remaining for a player. Use the with
    statement to start the game clock. The game clock will automatically stop when the with statement exits.

    Example:
        >>> game_clock_config = GameClockConfiguration(total_time=0.1, increment=0.0, delay=0.0)
        >>> game_clock = GameClock(game_clock_config)
        >>> with game_clock as total_time_left_ns:
        ...     time.sleep(0.2)
        ...     total_time_left_ns
        100000000
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
            self._total_time_ns = int(365 * 24 * 60 * 60 * 1e9)
        self._increment = game_clock_config.increment
        try:
            self._increment_ns = int(game_clock_config.increment * 1e9)
        except OverflowError:
            self._increment_ns = int(365 * 24 * 60 * 60 * 1e9)
        self._delay = game_clock_config.delay
        try:
            self._delay_ns = int(game_clock_config.delay * 1e9)
        except OverflowError:
            self._delay_ns = int(365 * 24 * 60 * 60 * 1e9)
        self.__start: int | None = None
        self._last_delta_ns: int | None = None

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
        self, exc_type: Type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
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
        if self._total_time_ns > 60_000_000_000:
            minutes = self._total_time_ns // 60_000_000_000
            seconds = (self._total_time_ns % 60_000_000_000) // 1_000_000_000
            return f"{minutes}:{seconds:02}"
        if self._total_time_ns > 30_000_000_000:
            return f"{self.total_time:.1f}"
        if self._total_time_ns > 1_000_000_000:
            return f"{self.total_time:.2f}"
        if self._total_time_ns > 100_000_000:
            return f"{self.total_time:.3f}"
        if self._total_time_ns == 0:
            return "0."
        return f"{self.total_time:.4f}"

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
    def last_delta_ns(self) -> int | None:
        return self._last_delta_ns

    @property
    def last_delta(self) -> float | None:
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
