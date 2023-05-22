"""Provides Evaluators.

Evaluators are used to evaluate a node in the game tree based on the perspective of the agent.

"""
from typing import Any, Callable, Protocol, TypeVar

from pyggp.engine_primitives import Role, State
from pyggp.interpreters import Interpreter

_U_co = TypeVar("_U_co", covariant=True)


class Evaluator(Protocol[_U_co]):
    """Protocol for evaluators."""

    # Disables ARG002 (Unused method argument). Accepting any argument is fine, as this is the base class.
    def __call__(self, state: State, *args: Any, **kwargs: Any) -> _U_co:
        """Evaluates a given state.

        Args:
            state: Current state
            args: Additional arguments
            kwargs: Additional keyword arguments

        Returns:
            Utility of the state

        """


# Disables ARG001 (Unused function argument). Because: It should fit the Evaluator protocol.
def _evaluate_per_default(*args: Any, default: Any, **kwargs: Any) -> Any:  # noqa: ARG001
    """Default evaluator.

    Args:
        args: Additional arguments
        default: Default value
        kwargs: Additional keyword arguments

    Returns:
        Default value

    """
    return default


def _evaluate_per_default_factory(
    # Disables ARG001 (Unused function argument). Because: It should fit the Evaluator protocol.
    *args: Any,  # noqa: ARG001
    default_factory: Callable[[], _U_co],
    **kwargs: Any,  # noqa: ARG001
) -> _U_co:
    """Default evaluator.

    Args:
        args: Additional arguments
        default_factory: Default value factory
        kwargs: Additional keyword arguments

    Returns:
        Default value

    """
    return default_factory()


def _evaluate_by_goals_to_normalized_utility(
    state: State,
    role: Role,
    interpreter: Interpreter,
    # Disables ARG001 (Unused function argument). Because: It should fit the Evaluator protocol.
    *args: Any,  # noqa: ARG001
    **kwargs: Any,  # noqa: ARG001
) -> float:
    goals = interpreter.get_goals(state)
    ranks = Interpreter.get_ranks(goals)
    rank = ranks[role]
    rank_count = sum(1 for r in ranks.values() if r == rank)
    places = len(ranks)
    assert 0 < rank_count <= places, "Assumption: 0 < rank_count <= places"
    utility = (places - rank - 1) / (rank_count * (places - 1))
    assert 0 <= utility <= 1, "Guarantee: 0 <= utility <= 1"
    return utility


# Disables mypy. Because: mypy is not able to infer the correct type.
default_evaluator: Evaluator[Any] = _evaluate_per_default  # type: ignore[assignment]
# Disables mypy. Because: mypy is not able to infer the correct type.
default_factory_evaluator: Evaluator[Any] = _evaluate_per_default_factory  # type: ignore[assignment]
# Disables mypy. Because: mypy is not able to infer the correct type.
final_goal_normalized_utility_evaluator: Evaluator[
    float
] = _evaluate_by_goals_to_normalized_utility  # type: ignore[assignment]
