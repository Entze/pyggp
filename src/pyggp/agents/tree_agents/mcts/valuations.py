"""Valuations for MCTS agents."""
from dataclasses import dataclass
from typing import Literal, Mapping

from typing_extensions import Self

from pyggp._logging import format_amount, inflect_without_count
from pyggp.agents.tree_agents.valuations import Valuation


@dataclass(frozen=True)
class PlayoutValuation(Valuation):
    """Valuation that stores number of times a rank was achieved by a role."""

    ranks: Mapping[int, int]
    "Mapping of rank to amount of times it was achieved."

    @property
    def total_playouts(self) -> int:
        """Total number of playouts."""
        return sum(self.ranks.values())

    @property
    def relative_ranks(self) -> Mapping[int, float]:
        """Relative count (not necessarily the probability) of the ranks."""
        return {rank: count / self.total_playouts for rank, count in self.ranks.items()}

    @property
    def expected_rank(self) -> float:
        """Weighted average of ranks and their counts."""
        return sum(rank * count / self.total_playouts for rank, count in self.ranks.items())

    def __rich__(self) -> str:
        """Rich representation of the valuation.

        Returns:
            Rich representation of the valuation

        """
        fmt = ["{"]
        rank_dict_str_list = []
        for rank, probability in sorted(self.relative_ranks.items()):
            probability_str = f"{probability * 100:.2f}" if self.ranks[rank] != self.total_playouts else "100.0"
            rank_dict_str_list.append(f"[blue]{rank}[/blue]: [green]{probability_str:>5}%[/green]")
        fmt.append(", ".join(rank_dict_str_list))
        fmt.append("}")
        fmt.append(
            f" (expected rank: [yellow]{self.expected_rank:.2f}[/yellow] @ "
            f"[orange1]{format_amount(self.total_playouts):>7}[/orange1] "
            f"{inflect_without_count('playout', self.total_playouts)})",
        )
        return "".join(fmt)

    def compare(self, other: Self) -> Literal["<", "==", ">"]:
        """Compares this valuation to another.

        Uses the expected rank for comparison. The lower the rank the greater the valuation.

        Args:
            other: Other valuation to compare to

        Returns:
            "<", "==", or ">" if this valuation is less than, equal to, or greater than the other

        """
        if self == other:
            return "=="
        if self.expected_rank > other.expected_rank:
            return "<"
        return ">"

    def propagate(self, other: Self) -> Self:
        """Combines the information from this valuation with another.

        Sums up the counts of the ranks.

        Args:
            other: Other valuation to combine with

        Returns:
            New valuation that combines the information from this valuation with the other

        """
        all_ranks = set(self.ranks.keys()).union(set(other.ranks.keys()))
        ranks = {rank: self.ranks.get(rank, 0) + other.ranks.get(rank, 0) for rank in all_ranks}
        # Disables mypy. Mypy does not seem to respect the typing_extension.Self implementation.
        return PlayoutValuation(ranks=ranks)  # type: ignore[return-value]
