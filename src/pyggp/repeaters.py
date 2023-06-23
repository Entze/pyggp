import logging
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Final, Generic, Optional, Tuple, TypeVar

import more_itertools
from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")

ONE_S_IN_NS: Final[int] = 1_000_000_000
INV_GOLDEN_RATIO: Final[float] = 2.0 / (1.0 + math.sqrt(5.0))

log = logging.getLogger("pyggp")


@dataclass
class Repeater(Generic[T]):
    func: Callable[P, T]
    timeout_ns: int
    shortcircuit: Optional[Callable[P, bool]] = None
    average_tail: int = 5
    average_weights: Optional[Tuple[float, ...]] = None

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Tuple[int, int]:
        if self.timeout_ns == 0:
            return 0, 0
        average_weights = self.average_weights
        if average_weights is None:
            average_weights = (1, *(2**i for i in range(0, self.average_tail - 1)))
        average_weights = average_weights[: self.average_tail]
        calls: int = 0
        deltas_ns: Deque[int] = deque(maxlen=self.average_tail)
        start_ns: int = time.monotonic_ns()
        end_ns = time.monotonic_ns() + self.timeout_ns
        avg_delta_ns: float = more_itertools.dotproduct(average_weights, deltas_ns) / sum(
            average_weights[: len(deltas_ns)]
        )
        while time.monotonic_ns() + avg_delta_ns < end_ns and (
            self.shortcircuit is None or not self.shortcircuit(*args, **kwargs)
        ):
            last_delta_ns = time.monotonic_ns()
            self.func(*args, **kwargs)
            last_delta_ns = time.monotonic_ns() - last_delta_ns
            deltas_ns.appendleft(last_delta_ns)
            calls += 1

        return calls, (time.monotonic_ns() - start_ns)
