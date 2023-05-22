"""Selectors for MCTS.

Selectors are used to select a key from a mapping of children nodes. Can be used in the Selection phase or when choosing
a move.

"""
import abc
import math
import random
from dataclasses import dataclass
from typing import Any, Callable, Final, Generic, Mapping, Optional, Protocol, SupportsFloat, Tuple, TypeVar

from pyggp.agents.tree_agents.nodes import Node
from pyggp.agents.tree_agents.valuations import Valuation

_K = TypeVar("_K")
_U_co = TypeVar("_U_co", bound=SupportsFloat)


class Selector(Protocol[_U_co, _K]):
    """Protocol for selectors."""

    def __call__(self, node: Node[_U_co, _K]) -> _K:
        """Selects a key from the children of the given node.

        Args:
            node: Node

        Returns:
            Selected key

        """


_A = TypeVar("_A")


class _FunctionSelectorProtocol(Selector[_U_co, _K], Protocol[_U_co, _K, _A]):
    select_func: Callable[[_A], _K]
    """Function to select a key from the given keys."""
    get_keys_func: Optional[Callable[[Node[_U_co, _K]], _A]]
    """Function to get the keys from the given node."""


class _AbstractFunctionSelectorProtocol(
    _FunctionSelectorProtocol[_U_co, _K, _A],
    Generic[_U_co, _K, _A],
    abc.ABC,
):
    def __call__(self, node: Node[_U_co, _K]) -> _K:
        if self.get_keys_func is not None:
            keys = self.get_keys_func(node)
        elif node.children is not None:
            # Disables mypy. Because: tuple(node.children.keys()) is the default should get_keys_func be None.
            keys = tuple(node.children.keys())  # type: ignore[assignment]
        else:
            # Disables mypy. Because: tuple() is the default should get_keys_func be None and node.children be None.
            keys = ()  # type: ignore[assignment]
        return self.select_func(keys)


@dataclass(frozen=True)
class FunctionSelector(
    _AbstractFunctionSelectorProtocol[_U_co, _K, _A],
    Generic[_U_co, _K, _A],
):
    select_func: Callable[[_A], _K]
    """Function to select a key from the given keys."""
    get_keys_func: Optional[Callable[[Node[_U_co, _K]], _A]] = None
    """Function to get the keys from the given node."""


def _map_keys_to_valuation(node: Node[_U_co, _K]) -> Mapping[_K, Tuple[Valuation[_U_co], ...]]:
    if node.children is None:
        return {}
    return {key: (child.valuation,) if child.valuation is not None else () for key, child in node.children.items()}


_V = TypeVar("_V")


def _select_maximum(key_to_comparable: Mapping[_K, _V]) -> _K:
    def key(key: _K) -> Tuple[_V, ...]:
        val = key_to_comparable.get(key)
        if val is None:
            return ()
        return (val,)

    return max(key_to_comparable, key=key)


def _get_total_playouts(valuation: Valuation[_U_co], default: int = 0) -> int:
    return getattr(valuation, "total_playouts", default)


def _map_keys_to_total_playouts(node: Node[_U_co, _K]) -> Mapping[_K, int]:
    if node.children is None:
        return {}
    return {
        key: _get_total_playouts(child.valuation) if child.valuation is not None else 0
        for key, child in node.children.items()
    }


SQRT_2: Final[float] = math.sqrt(2)


def _map_keys_to_uct(node: Node[_U_co, _K], exploitation: float = SQRT_2) -> Mapping[_K, float]:
    if node.children is None:
        return {}
    return {
        # Disables mypy. Because: Utility supports float (don't fight the typechecker).
        key: child.valuation.utility / _get_total_playouts(child.valuation, default=1)  # type: ignore[operator]
        + exploitation
        * math.sqrt(
            math.log(_get_total_playouts(node.valuation, default=1)) / _get_total_playouts(child.valuation, default=1),
        )
        if child.valuation is not None
        and _get_total_playouts(child.valuation) > 0
        and node.valuation is not None
        and _get_total_playouts(node.valuation) > 0
        else float("inf")
        for key, child in node.children.items()
    }


random_selector: FunctionSelector[Any, Any, Any] = FunctionSelector(select_func=random.choice)
best_selector: FunctionSelector[Any, Any, Any] = FunctionSelector(
    select_func=_select_maximum,
    get_keys_func=_map_keys_to_valuation,
)
most_selector: FunctionSelector[Any, Any, Any] = FunctionSelector(
    select_func=_select_maximum,
    get_keys_func=_map_keys_to_total_playouts,
)
uct_selector: FunctionSelector[Any, Any, Any] = FunctionSelector(
    select_func=_select_maximum,
    get_keys_func=_map_keys_to_uct,
)
