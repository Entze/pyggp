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
    tail: int = 5
    weights: Optional[Tuple[float, ...]] = None
    slack: float = 1.0

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Tuple[int, int]:
        if self.timeout_ns == 0:
            return 0, 0
        weights = self.weights
        if weights is None:
            weights = (1, *(2**i for i in range(0, self.tail - 1)))
        weights = weights[: self.tail]
        deltas_ns: Deque[int] = deque(maxlen=self.tail)
        calls: int = 0
        start_ns: int = time.monotonic_ns()
        end_ns: int = time.monotonic_ns() + self.timeout_ns
        avg_delta_ns: float = 0.0
        while time.monotonic_ns() + avg_delta_ns * self.slack < end_ns and not self._shortcircuit(*args, **kwargs):
            last_delta_ns = time.monotonic_ns()
            self.func(*args, **kwargs)
            last_delta_ns = time.monotonic_ns() - last_delta_ns
            deltas_ns.append(last_delta_ns)
            avg_delta_ns = more_itertools.dotproduct(weights, deltas_ns) / sum(weights[: len(deltas_ns)])
            calls += 1

        return calls, (time.monotonic_ns() - start_ns)

    def _shortcircuit(self, *args: P.args, **kwargs: P.kwargs) -> bool:
        if self.shortcircuit is None:
            return False
        return self.shortcircuit(*args, **kwargs)
