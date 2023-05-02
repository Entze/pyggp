"""Provides Evaluators.

Evaluators are used to evaluate a node in the game tree based on the perspective of the agent.

"""
from dataclasses import dataclass
from typing import Any, Generic, Type, TypeVar

from typing_extensions import override

from pyggp.agents.tree_agents.perspectives import Perspective
from pyggp.agents.tree_agents.valuations import Valuation
from pyggp.interpreters import Interpreter

_P = TypeVar("_P", bound=Perspective)
_V = TypeVar("_V", bound=Valuation)


@dataclass
class Evaluator(Generic[_P, _V]):
    """Base class for all evaluators."""

    # Disables ARG002 (Unused method argument). Accepting any argument is fine, as this is the base class.
    def __call__(self, interpreter: Interpreter, perspective: _P, *args: Any, **kwargs: Any) -> _V:  # noqa: ARG002
        """Evaluates the node.

        Args:
            interpreter: Interpreter
            perspective: Current perspective
            args: Additional arguments
            kwargs: Additional keyword arguments

        Returns:
            Valuation of the node

        """
        return self.evaluate(interpreter, perspective)

    def evaluate(self, interpreter: Interpreter, perspective: _P) -> _V:
        """Evaluates the node.

        Args:
            interpreter: Interpreter
            perspective: Current perspective

        Returns:
            Valuation of the node

        """
        raise NotImplementedError


@dataclass
class NullEvaluator(Evaluator[_P, _V]):
    """An evaluator that always returns the default valuation."""

    valuation_type: Type[_V]

    @override
    def evaluate(self, interpreter: Interpreter, perspective: _P) -> _V:
        """Evaluates the node.

        Returns the default valuation of the valuation's type. Ignores the interpreter and perspective.

        Args:
        interpreter: Interpreter (ignored)
        perspective: Current perspective (ignored)

        Returns:
            Valuation of the node

        """
        return self.valuation_type()
