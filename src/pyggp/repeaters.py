import logging
import math
import time
from dataclasses import dataclass
from typing import Callable, Final, Generic, Tuple, TypeVar

from typing_extensions import ParamSpec

from pyggp._logging import format_amount, format_timedelta

P = ParamSpec("P")
T = TypeVar("T")

INV_GOLDEN_RATIO: Final[float] = 2.0 / (1.0 + math.sqrt(5.0))

log = logging.getLogger("pyggp")


@dataclass
class Repeater(Generic[P]):
    func: Callable[P, None]
    timeout_ns: int
    max_repeats: int = 1_000_000
    repeat_ratio: float = INV_GOLDEN_RATIO

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Tuple[int, int]:
        total_elapsed_ns: int = 0
        elapsed_ns: int = 0
        repeats: int = 1
        calls: int = 0
        start_ns: int = 0
        avg_it_per_ns: float = 0.0
        while total_elapsed_ns <= self.timeout_ns:
            start_ns = time.monotonic_ns()
            for _ in range(repeats):
                self.func(*args, **kwargs)
            elapsed_ns = time.monotonic_ns() - start_ns
            total_elapsed_ns += elapsed_ns
            avg_it_per_ns = repeats / elapsed_ns
            log.debug(
                "%s it in %s (%s it/s)",
                format_amount(repeats),
                format_timedelta(elapsed_ns / 1e9),
                format_amount(avg_it_per_ns * 1e9),
            )
            calls += repeats
            repeats = min(
                self.max_repeats,
                repeats * 2,
                max(1, repeats // 10, int(avg_it_per_ns * (self.repeat_ratio * (self.timeout_ns - total_elapsed_ns)))),
            )

        return calls, total_elapsed_ns
