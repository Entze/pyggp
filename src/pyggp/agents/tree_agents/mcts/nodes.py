"""Nodes for MCTS agents."""
import abc
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, Mapping, Optional, TypeVar, Union

from typing_extensions import Self, override

from pyggp.agents.tree_agents.evaluators import Evaluator, NullEvaluator
from pyggp.agents.tree_agents.mcts.selectors import BestSelector, RandomSelector, Selector
from pyggp.agents.tree_agents.mcts.valuations import PlayoutValuation
from pyggp.agents.tree_agents.nodes import DeterministicNode, Node
from pyggp.agents.tree_agents.perspectives import DeterministicPerspective, Perspective
from pyggp.interpreters import Interpreter, Turn

_K = TypeVar("_K")
_P = TypeVar("_P", bound=Perspective)
_PV = TypeVar("_PV", bound=PlayoutValuation)


@dataclass
class MCTSNode(Generic[_P, _PV, _K], Node[_P, _PV, _K], abc.ABC):
    """Base class for all MCTS nodes.

    Requires the valuation to be an instance of PlayoutValuation.

    """

    default_selector: ClassVar[Selector[Perspective, PlayoutValuation, Any]] = RandomSelector()
    "Default selector to use during Selection phase."
    default_chooser: ClassVar[Selector[Perspective, PlayoutValuation, Any]] = BestSelector()
    "Default selector to use when choosing a move."
    valuation_type = PlayoutValuation
    default_evaluator = NullEvaluator(valuation_type)

    def select(
        self,
        *,
        selector: Optional[Selector[_P, _PV, _K]] = None,
        max_expand_width: Optional[int] = None,
    ) -> Self:
        """Selects a child node to expand.

        Args:
            selector: Selector to use (defaults to the default selector)
            max_expand_width: Maximum number of expanded children (defaults to no limit)

        Returns:
            Selected child node

        """
        if not self.children:
            message = "Cannot select from node with no children."
            raise ValueError(message)
        max_expand_width_: Union[int, float] = max_expand_width or float("inf")
        expand_width = self.count_expanded_children if max_expand_width is not None else -1
        # Disables mypy. Because: Selector has to be set as class variable. Safe typing is tricky.
        selector_: Selector[_P, _PV, _K] = selector or type(self).default_selector  # type: ignore[assignment]
        selected_key = selector_(
            {key: node for key, node in self.children.items() if node.is_expanded or expand_width < max_expand_width_},
        )
        return self.children[selected_key]

    def search(
        self,
        interpreter: Interpreter,
        *,
        selector: Optional[Selector[_P, _PV, _K]] = None,
        evaluator: Optional[Evaluator[_P, _PV]] = None,
        max_expand_depth: Optional[int] = None,
        max_expand_width: Optional[int] = None,
    ) -> None:
        """Searches the tree and updates the valuations.

        Args:
            interpreter: Interpreter
            selector: Selector to use (defaults to the default selector)
            evaluator: Evaluator to use (defaults to the default evaluator)
            max_expand_depth: Maximum depth to expand
            max_expand_width: Maximum width to expand

        """
        node = self
        expand_depth = 0
        max_expand_depth_: Union[int, float] = max_expand_depth or float("inf")
        while node.children and expand_depth < max_expand_depth_:
            node = node.select(selector=selector, max_expand_width=max_expand_width)
            expand_depth += 1
        node.expand(interpreter)
        node.evaluate(interpreter, evaluator=evaluator)
        node.propagate_back()

    def choose(self, *, chooser: Optional[Selector[_P, _PV, _K]] = None) -> _K:
        """Chooses a move.

        Similar to select, however, this method does not expand the node. Additionally, another criteria for selection
        may be defined.

        Args:
            chooser: Chooser to use (defaults to the default chooser)

        Returns:
            Key of the chosen child

        """
        if not self.children:
            message = "Cannot choose from node with no children."
            raise ValueError(message)
        # Disables mypy. Because: Chooser has to be set as class variable. Safe typing is tricky.
        chooser_: Selector[_P, _PV, _K] = chooser or type(self).default_chooser  # type: ignore[assignment]
        return chooser_(self.children)


_DP = TypeVar("_DP", bound=DeterministicPerspective)


@dataclass
class DeterministicMCTSNode(Generic[_DP, _PV], MCTSNode[_DP, _PV, Turn], DeterministicNode[_DP, _PV]):
    """MCTS node for deterministic games.

    Constraints the perspective to be an instance of DeterministicPerspective.

    """

    perspective_type = DeterministicPerspective
    valuation_type = PlayoutValuation
    default_evaluator = NullEvaluator(valuation_type)

    @override
    def expand(self, interpreter: Interpreter) -> Mapping[Turn, Self]:
        if not self.is_expanded:
            children: Mapping[Turn, DeterministicMCTSNode[_DP, _PV]] = {
                turn: DeterministicMCTSNode.from_perspective(perspective=perspective, parent=self)
                for turn, perspective in self.perspective.get_next_perspectives(interpreter)
            }
            # Disables mypy. Mypy does not seem to respect the typing_extension.Self implementation.
            self.children = children  # type: ignore[assignment]
        assert self.is_expanded, "Assumption: self.is_expanded was true before or it now became now"
        assert self.children is not None, "Assumption: self.is_expanded implies self.children is not None"
        return self.children
