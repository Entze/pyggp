"""Valuations for MCTS agents."""

import contextlib
from dataclasses import dataclass
from typing import Any, Optional, Protocol, TypeVar

from typing_extensions import Self

from pyggp._logging import format_amount
from pyggp.agents.tree_agents.valuations import Valuation

_U = TypeVar("_U")


class PlayoutValuation(Valuation[_U], Protocol[_U]):
    total_playouts: int


@dataclass(frozen=True)
class NormalizedUtilityValuation(PlayoutValuation[float]):
    """Valuation that sums the achieved rank normalized as a value between 0 and 1.

    1 is the best rank, 0 is the worst rank. If a tie occurs, the ranks utility value is split between all roles who
    received the same rank. If more than two ranks, they are evenly spaced out between 0 and 1.

    """

    utility: float = 0.0
    total_playouts: int = 0

    @property
    def average_utility(self) -> float:
        """Average utility."""
        return self.utility / self.total_playouts

    @classmethod
    def from_utility(cls, utility: float) -> Self:
        """Constructs a valuation from a utility.

        Args:
            utility: Utility

        Returns:
            Valuation

        """
        assert 0 <= utility <= 1, "Requirement: 0 <= utility <= 1"
        return cls(utility=utility, total_playouts=1)

    def __lt__(self, other: Any) -> bool:
        other_key = NormalizedUtilityValuation._key(other)
        if other_key is None:
            return False
        return self.average_utility < other_key

    def __le__(self, other: Any) -> bool:
        if self == other:
            return True
        other_key = NormalizedUtilityValuation._key(other)
        if other_key is None:
            return False
        return self.average_utility <= other_key

    def __gt__(self, other: Any) -> bool:
        other_key = NormalizedUtilityValuation._key(other)
        if other_key is None:
            return True
        return self.average_utility > other_key

    def __ge__(self, other: Any) -> bool:
        other_key = NormalizedUtilityValuation._key(other)
        if other_key is None or self == other:
            return True
        return self.average_utility >= other_key

    def __str__(self) -> str:
        return f"{self.average_utility:.2f} @ {format_amount(self.total_playouts)}"

    def propagate(self, utility: float) -> Self:
        """Combines the information from this valuation with a utility.

        Args:
            utility: Immediate utility of a node or state

        Returns:
            Updated valuation

        """
        assert 0 <= utility <= 1, "Requirement: 0 <= utility <= 1"
        # Disables mypy. Because: mypy cannot infer that class is self.
        return NormalizedUtilityValuation(  # type: ignore[return-value]
            utility=self.utility + utility,
            total_playouts=self.total_playouts + 1,
        )

    @staticmethod
    def _key(other: Any) -> Optional[float]:
        if hasattr(other, "utility") and hasattr(other, "total_playouts"):
            return float(other.utility / other.total_playouts)
        if isinstance(other, float):
            return other
        if hasattr(other, "__getitem__"):
            with contextlib.suppress(ZeroDivisionError, KeyError, TypeError):
                return float(other[0] / other[1])
        return None
