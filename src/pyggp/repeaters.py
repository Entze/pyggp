import itertools
import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
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
    timeout_ns: Optional[int]
    max_repeats: Optional[int] = None
    shortcircuit: Optional[Callable[P, bool]] = None
    tail: int = 100
    weights: Optional[Tuple[float, ...]] = None
    slack: float = 1.0
    _start_ns: int = field(init=False, repr=False, default=0)
    _calls: int = field(init=False, repr=False, default=0)
    _avg_delta_ns: float = field(init=False, repr=False, default=0.0)

    def __post_init__(self):
        if self.timeout_ns is None and self.max_repeats is None and self.shortcircuit is None:
            log.warning(
                "Repeater has no timeout, max_repeats or shortcircuit. No exit condition, likely to loop forever.",
            )

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Tuple[int, int]:
        if self.timeout_ns == 0:
            return 0, 0
        weights = self.weights
        if weights is None:
            weights = tuple(itertools.repeat(1, self.tail))
        weights = weights[: self.tail]
        deltas_ns: Deque[int] = deque(maxlen=self.tail)
        self._start_ns = time.monotonic_ns()
        while self.should_loop(*args, **kwargs):
            last_delta_ns = time.monotonic_ns()
            self.func(*args, **kwargs)
            last_delta_ns = time.monotonic_ns() - last_delta_ns
            deltas_ns.append(last_delta_ns)
            self._avg_delta_ns = more_itertools.dotproduct(weights, deltas_ns) / sum(weights[: len(deltas_ns)])
            self._calls += 1

        return self._calls, (time.monotonic_ns() - self._start_ns)

    def should_loop(self, *args: P.args, **kwargs: P.kwargs) -> bool:
        return (
            (
                self.timeout_ns is None
                or self.timeout_ns > ((time.monotonic_ns() - self._start_ns) + self._avg_delta_ns * self.slack)
            )
            and (self.max_repeats is None or self.max_repeats > self._calls)
            and (self.shortcircuit is None or not self._shortcircuit(*args, **kwargs))
        )

    def _shortcircuit(self, *args: P.args, **kwargs: P.kwargs) -> bool:
        return self.shortcircuit is not None and self.shortcircuit(*args, **kwargs)
