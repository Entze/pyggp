"""Selectors for MCTS.

Selectors are used to select a key from a mapping of children nodes. Can be used in the Selection phase or when choosing
a move.

"""
import abc
import random
from dataclasses import dataclass
from typing import Callable, Generic, Mapping, Tuple, TypeVar

from pyggp.agents.tree_agents.nodes import Node
from pyggp.agents.tree_agents.perspectives import Perspective
from pyggp.agents.tree_agents.valuations import Valuation

_K = TypeVar("_K")
_P = TypeVar("_P", bound=Perspective)
_V = TypeVar("_V", bound=Valuation)


@dataclass
class Selector(Generic[_P, _V, _K], abc.ABC):
    """Base class for all selectors."""

    def __call__(self, children: Mapping[_K, Node[_P, _V, _K]]) -> _K:
        """Selects a key from the given mapping of children nodes.

        Args:
            children: Mapping of children nodes

        Returns:
            Selected key

        """
        return self.select(children)

    def select(self, children: Mapping[_K, Node[_P, _V, _K]]) -> _K:
        """Selects a key from the given mapping of children nodes.

        Args:
            children: Mapping of children nodes

        Returns:
            Selected key

        """
        raise NotImplementedError


@dataclass
class RandomSelector(Selector[_P, _V, _K]):
    """Selector that selects a random key."""

    def select(self, children: Mapping[_K, Node[_P, _V, _K]]) -> _K:
        """Selects a key from the given mapping of children nodes.

        Any child's key may be selected uniformly at random.

        Args:
            children: Mapping of children nodes

        Returns:
            Selected key

        """
        return random.choice(list(children.keys()))


@dataclass
class BestSelector(Selector[_P, _V, _K]):
    """Selector that selects the key with the best valuation."""

    def select(self, children: Mapping[_K, Node[_P, _V, _K]]) -> _K:
        """Selects a key from the given mapping of children nodes.

        Selects the key where the node has the maximum valuation. If the valuation is None, the key is minimal.

        Args:
            children: Mapping of children nodes

        Returns:
            Selected key

        """
        return max(children.keys(), key=BestSelector.get_key(children))

    @staticmethod
    def get_key(children: Mapping[_K, Node[_P, _V, _K]]) -> Callable[[_K], Tuple[_V, ...]]:
        """Builds a function that provides wraps the valuation, if it exists, into a tuple.

        This ensures that all keys are comparable, even if some nodes have no valuation.

        Args:
            children: Mapping of children nodes

        Returns:
            Function that wraps the valuations into a tuple

        """

        def comparable(key: _K) -> Tuple[_V, ...]:
            """Returns the valuation associated with the given key into a tuple.

            If the valuation is None, returns an empty tuple.

            Args:
                key: Key to get the valuation for

            Returns:
                Tuple of the valuation, or empty tuple if the valuation is None

            """
            node = children[key]
            if node.valuation is None:
                return ()
            return (node.valuation,)

        return comparable
