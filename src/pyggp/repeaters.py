import logging
import math
import time
from dataclasses import dataclass
from typing import Callable, Final, Optional, Tuple, TypeVar

from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")

ONE_S_IN_NS: Final[int] = 1_000_000_000
INV_GOLDEN_RATIO: Final[float] = 2.0 / (1.0 + math.sqrt(5.0))

log = logging.getLogger("pyggp")


@dataclass
class Repeater:
    func: Callable[[], None]
    timeout_ns: int
    shortcircuit: Optional[Callable[[], bool]] = None

    def __call__(self) -> Tuple[int, int]:
        if self.timeout_ns == 0:
            return 0, 0
        calls: int = 0
        start_ns: int = time.monotonic_ns()
        end_ns = time.monotonic_ns() + self.timeout_ns
        last_delta_ns = 0
        while time.monotonic_ns() + (3 * last_delta_ns) < end_ns and (
            self.shortcircuit is None or not self.shortcircuit()
        ):
            last_delta_ns = time.monotonic_ns()
            self.func()
            last_delta_ns = time.monotonic_ns() - last_delta_ns
            calls += 1

        return calls, (time.monotonic_ns() - start_ns)
