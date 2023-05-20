"""Selectors for MCTS.

Selectors are used to select a key from a mapping of children nodes. Can be used in the Selection phase or when choosing
a move.

"""
import abc
import math
import random
from dataclasses import dataclass
from typing import Any, Callable, Final, Generic, Mapping, Optional, Protocol, Tuple, TypeVar

from pyggp.agents.tree_agents.mcts.nodes import MonteCarloTreeSearchNode
from pyggp.agents.tree_agents.nodes import Node
from pyggp.agents.tree_agents.valuations import Valuation

_K = TypeVar("_K")
_U = TypeVar("_U")


class MonteCarloTreeSearchSelector(Protocol[_U, _K]):
    def __call__(self, node: MonteCarloTreeSearchNode[_U, _K]) -> _K:
        """Selects a key from the children of the given Monte Carlo Tree Search node.

        Args:
            node: Node

        Returns:
            Selected key

        """


class Selector(MonteCarloTreeSearchSelector[_U, _K], Protocol[_U, _K]):
    """Protocol for selectors."""

    def __call__(self, node: Node[_U, _K]) -> _K:
        """Selects a key from the children of the given node.

        Args:
            node: Node

        Returns:
            Selected key

        """


_A = TypeVar("_A")


class _FunctionMonteCarloTreeSearchSelectorProtocol(MonteCarloTreeSearchSelector[_U, _K], Protocol[_U, _K, _A]):
    select_func: Callable[[_A], _K]
    """Function to select a key from the given keys."""
    get_keys_func: Optional[Callable[[MonteCarloTreeSearchNode[_U, _K]], _A]]
    """Function to get the keys from the given node."""


class _FunctionSelectorProtocol(Selector[_U, _K], Protocol[_U, _K, _A]):
    select_func: Callable[[_A], _K]
    """Function to select a key from the given keys."""
    get_keys_func: Optional[Callable[[Node[_U, _K]], _A]]
    """Function to get the keys from the given node."""


class _AbstractFunctionMonteCarloTreeSearchSelectorProtocol(
    _FunctionMonteCarloTreeSearchSelectorProtocol[_U, _K, _A],
    Generic[_U, _K, _A],
    abc.ABC,
):
    def __call__(self, node: MonteCarloTreeSearchNode[_U, _K]) -> _K:
        if self.get_keys_func is not None:
            keys = self.get_keys_func(node)
        elif node.children is not None:
            keys = tuple(node.children.keys())
        else:
            keys = ()
        return self.select_func(keys)


@dataclass(frozen=True)
class FunctionMonteCarloTreeSearchSelector(
    _AbstractFunctionMonteCarloTreeSearchSelectorProtocol[_U, _K, _A],
    Generic[_U, _K, _A],
):
    select_func: Callable[[_A], _K]
    """Function to select a key from the given keys."""
    get_keys_func: Optional[Callable[[MonteCarloTreeSearchNode[_U, _K]], _A]] = None
    """Function to get the keys from the given node."""


@dataclass(frozen=True)
class FunctionSelector(
    _AbstractFunctionMonteCarloTreeSearchSelectorProtocol[_U, _K, _A],
    Generic[_U, _K, _A],
):
    select_func: Callable[[_A], _K]
    """Function to select a key from the given keys."""
    get_keys_func: Optional[Callable[[Node[_U, _K]], _A]] = None
    """Function to get the keys from the given node."""


def _map_keys_to_valuation(node: Node[_U, _K]) -> Mapping[_K, Tuple[Valuation[_U], ...]]:
    if node.children is None:
        return {}
    return {key: (child.valuation,) if child.valuation is not None else () for key, child in node.children.items()}


_V = TypeVar("_V")


def _select_maximum(key_to_comparable: Mapping[_K, _V]) -> _K:
    return max(key_to_comparable, key=key_to_comparable.get)


def _map_keys_to_total_playouts(node: MonteCarloTreeSearchNode[_U, _K]) -> Mapping[_K, int]:
    return {
        key: child.valuation.total_playouts if child.valuation is not None else 0
        for key, child in node.children.items()
    }


SQRT_2: Final[float] = math.sqrt(2)


def _map_keys_to_uct(node: MonteCarloTreeSearchNode[_U, _K], exploitation: float = SQRT_2) -> Mapping[_K, float]:
    return {
        key: child.valuation.utility / child.valuation.total_playouts
        + exploitation * math.sqrt(math.log(node.valuation.total_playouts) / child.valuation.total_playouts)
        if child.valuation is not None
        and child.valuation.total_playouts > 0
        and node.valuation is not None
        and node.valuation.total_playouts > 0
        else float("inf")
        for key, child in node.children.items()
    }


random_selector: FunctionSelector[Any, Any, Any] = FunctionSelector(select_func=random.choice)
best_selector: FunctionSelector[Any, Any, Any] = FunctionSelector(
    select_func=_select_maximum,
    get_keys_func=_map_keys_to_valuation,
)
most_selector: FunctionMonteCarloTreeSearchSelector[Any, Any, Any] = FunctionMonteCarloTreeSearchSelector(
    select_func=_select_maximum,
    get_keys_func=_map_keys_to_total_playouts,
)
uct_selector: FunctionMonteCarloTreeSearchSelector[Any, Any, Any] = FunctionMonteCarloTreeSearchSelector(
    select_func=_select_maximum,
    get_keys_func=_map_keys_to_uct,
)
