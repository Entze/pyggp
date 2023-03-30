import collections
from dataclasses import dataclass
from typing import Mapping, Self, Type

from pyggp.gdl import ConcreteRole


@dataclass(frozen=True)
class Valuation:
    def __matmul__(self, other: Self) -> Self:
        return self.backpropagate(other)

    def backpropagate(self, other: Self) -> Self:
        raise NotImplementedError


@dataclass(frozen=True)
class PlayoutValuation(Valuation):
    wins: Mapping[ConcreteRole, int]
    ties: Mapping[ConcreteRole, int]
    losses: Mapping[ConcreteRole, int]

    @property
    def playouts(self) -> int:
        total_wins = sum(self.wins.values()) // len(self.wins)
        total_ties = sum(self.ties.values()) // len(self.ties)
        total_losses = sum(self.losses.values()) // len(self.losses)
        return total_wins + total_ties + total_losses

    def backpropagate(self, other: Self) -> Self:
        cls: Type[Self] = type(self)
        # Disables PyCharm inspection. This seems to be a false positive
        # noinspection PyArgumentList
        return cls(
            wins=collections.defaultdict(
                int,
                {role: self.wins[role] + other.wins[role] for role in (*self.wins.keys(), *other.wins.keys())},
            ),
            ties=collections.defaultdict(
                int,
                {role: self.ties[role] + other.ties[role] for role in (*self.ties.keys(), *other.ties.keys())},
            ),
            losses=collections.defaultdict(
                int,
                {role: self.losses[role] + other.losses[role] for role in (*self.losses.keys(), *other.losses.keys())},
            ),
        )
