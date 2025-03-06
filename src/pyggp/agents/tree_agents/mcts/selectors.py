"""Selectors for MCTS.

Selectors are used to select a key from a mapping of children nodes. Can be used in the Selection phase or when choosing
a move.

"""

import abc
import math
import random
from dataclasses import dataclass
from typing import Any, Callable, Final, Generic, Mapping, Optional, Protocol, SupportsFloat, Tuple, TypeVar

from typing_extensions import ParamSpec

from pyggp.agents.tree_agents.nodes import Node
from pyggp.agents.tree_agents.valuations import Valuation
from pyggp.engine_primitives import Role, State

_K = TypeVar("_K")
_U_co = TypeVar("_U_co", bound=SupportsFloat)


class Selector(Protocol[_U_co, _K]):
    """Protocol for selectors."""

    def __call__(self, node: Node[_U_co, _K], *args: Any, **kwargs: Any) -> _K:
        """Selects a key from the children of the given node.

        Args:
            node: Node

        Returns:
            Selected key

        """


_A = TypeVar("_A")

_P = ParamSpec("_P")


class _FunctionSelectorProtocol(Selector[_U_co, _K], Protocol[_U_co, _K, _A]):
    select_func: Callable[[_A], _K]
    """Function to select a key from the given keys."""
    get_keys_func: Optional[Callable[_P, _A]]
    """Function to get the keys from the given node."""


class _AbstractFunctionSelectorProtocol(
    _FunctionSelectorProtocol[_U_co, _K, _A],
    Generic[_U_co, _K, _A],
    abc.ABC,
):
    def __call__(self, node: Node[_U_co, _K], *args: Any, **kwargs: Any) -> _K:
        if self.get_keys_func is not None:
            keys = self.get_keys_func(node, *args, **kwargs)
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
    get_keys_func: Optional[Callable[_P, _A]] = None
    """Function to get the keys from the given node."""


def _map_keys_to_valuation(
    node: Node[_U_co, _K],
    *args: Any,
    **kwargs: Any,
) -> Mapping[_K, Tuple[Valuation[_U_co], ...]]:
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


def _map_keys_to_total_playouts(node: Node[_U_co, _K], default: int = 0, *args: Any, **kwargs: Any) -> Mapping[_K, int]:
    if node.children is None:
        return {}
    return {
        key: _get_total_playouts(child.valuation, default=default) if child.valuation is not None else default
        for key, child in node.children.items()
    }


SQRT_2: Final[float] = math.sqrt(2)


@dataclass(frozen=True)
class UCTSelector(Selector[_U_co, _K]):
    role: Role
    exploration_constant: float = SQRT_2

    def __call__(self, node: Node[_U_co, _K], state: Optional[State] = None, *args: Any, **kwargs: Any) -> _K:
        assert node.children is not None, "Requirement: node.children is not None"
        parent_total_playouts: int = (
            node.valuation.total_playouts
            if node.valuation is not None and hasattr(node.valuation, "total_playouts")
            else 0
        )
        key_to_win_ratio: Mapping[_K, float] = {
            key: child.valuation.utility / child.valuation.total_playouts
            for key, child in node.children.items()
            if child.valuation is not None
            and hasattr(child.valuation, "total_playouts")
            and child.valuation.total_playouts > 0
        }
        key_to_exploration_factor: Mapping[_K, float] = {
            key: math.sqrt(math.log(parent_total_playouts) / child.valuation.total_playouts)
            for key, child in node.children.items()
            if parent_total_playouts > 0 and child.valuation is not None and hasattr(child.valuation, "total_playouts")
        }
        if not node.is_in_control(self.role):
            win_ratio_factor = -1.0
            win_ratio_offset = 1.0
        else:
            win_ratio_factor = 1.0
            win_ratio_offset = 0.0
        key_to_uct: Mapping[_K, float] = {
            key: (
                (win_ratio_factor * key_to_win_ratio.get(key, float("inf") * win_ratio_factor) + win_ratio_offset)
                + self.exploration_constant * key_to_exploration_factor.get(key, float("inf"))
                if state is None or state == key[0]
                else float("-inf")
            )
            for key in node.children
        }
        return max(key_to_uct, key=key_to_uct.get)


random_selector: FunctionSelector[Any, Any, Any] = FunctionSelector(select_func=random.choice)
best_selector: FunctionSelector[Any, Any, Any] = FunctionSelector(
    select_func=_select_maximum,
    get_keys_func=_map_keys_to_valuation,
)
most_selector: FunctionSelector[Any, Any, Any] = FunctionSelector(
    select_func=_select_maximum,
    get_keys_func=_map_keys_to_total_playouts,
)
