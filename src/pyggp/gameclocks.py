"""Game clocks for GGP."""
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import Type


@dataclass(frozen=True)
class GameClockConfiguration:
    """Configuration for a game clock. All units are in seconds."""

    total_time: float = 0.0
    """Total time in seconds. This is the time that will be decremented."""
    increment: float = 0.0
    """Increment in seconds. This is the time that will be added to the total time after each move."""
    delay: float = 60.0
    """Delay in seconds. This is the time that will be removed from the delta of the move."""


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
        self._total_time_ns = int(game_clock_config.total_time * 1e9)
        self._increment = game_clock_config.increment
        self._increment_ns = int(game_clock_config.increment * 1e9)
        self._delay = game_clock_config.delay
        self._delay_ns = int(game_clock_config.delay * 1e9)
        self.__start: int | None = None

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
    def __total_time_repr(self) -> str:
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
        if self._increment.is_integer():
            return f"{int(self._increment)}"
        return f"{self._increment}"

    @property
    def __delay_repr(self) -> str:
        if self._delay.is_integer():
            return f"{int(self._delay)}"
        return f"{self._delay}"

    @property
    def is_expired(self) -> bool:
        """Check if the game clock is expired."""
        return self._total_time_ns < 0

    @property
    def total_time(self) -> float:
        """Get the total time left in seconds."""
        return self._total_time_ns / 1e9

    @property
    def total_time_ns(self) -> int:
        """Get the total time left in nanoseconds."""
        return self._total_time_ns

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
        if self.__start is not None:
            time_delta = stop - self.__start
            clock_delta = max(0, time_delta - self._delay_ns)
            self._total_time_ns -= clock_delta
            if not self.is_expired:
                self._total_time_ns += self._increment_ns
            self.__start = None

    def get_timeout(self, slack: float = 0.0) -> float:
        """Get the timeout for the current move.

        This method gives an estimate when the current move can be stopped, as the game clock will be expired.

        Args:
            slack: The slack in seconds to add to the timeout.

        Returns:
            The timeout in seconds.
        """
        return max(0.0, self.total_time + self._delay + slack)
