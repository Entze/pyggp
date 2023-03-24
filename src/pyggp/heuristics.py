"""Heuristics for tree search.

Defines the heuristic types and default heuristics.

"""
import collections
from typing import Callable, Mapping, Optional, TypeAlias

from pyggp.gdl import ConcreteRole, State

Heuristic: TypeAlias = Callable[[State], Mapping[ConcreteRole, float]]
"""Heuristics map a state to a float for each role."""


def get_default_goal_heuristic(
    *roles: ConcreteRole,
    lowest_possible_goal: Optional[int] = None,
    highest_possible_goal: Optional[int] = None,
) -> Heuristic:
    """Gets a heuristic that maps to the lower bound for provided roles and the upper bound otherwise.

    Args:
        roles: Roles to return the lowest possible goal for.
        lowest_possible_goal: Lower bound. Defaults to -2**31.
        highest_possible_goal: Upper bound. Defaults to 2**31 - 1.

    Returns:
        Default goal heuristic.

    """
    lower_bound = float(lowest_possible_goal or "-inf")
    upper_bound = float(highest_possible_goal or "inf")

    # Disables ARG001 (Unused function argument). Because it has to match the Heuristic type.
    def default_goal_heuristic(state: State) -> Mapping[ConcreteRole, float]:  # noqa: ARG001
        return collections.defaultdict(
            lambda: upper_bound,
            {role: lower_bound for role in roles},
        )

    return default_goal_heuristic


def get_default_win_heuristic(*roles: ConcreteRole) -> Heuristic:
    """Gets a default heuristic that returns -inf for all provided roles and 0 per default.

    Args:
        roles: Roles to return -inf for.

    Returns:
        Default win heuristic.

    """

    # Disables ARG001 (Unused function argument). Because it has to match the Heuristic type.
    def default_win_heuristic(state: State) -> Mapping[ConcreteRole, float]:  # noqa: ARG001
        return collections.defaultdict(float, {role: float("-inf") for role in roles})

    return default_win_heuristic
