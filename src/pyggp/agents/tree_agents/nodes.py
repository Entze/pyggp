"""Nodes for tree agents.

Nodes can be used to represent the game tree.

"""
import abc
from dataclasses import dataclass, field
from typing import ClassVar, Generic, Iterator, Mapping, MutableMapping, Optional, Type, TypeVar, cast

from typing_extensions import Self

from pyggp.agents.tree_agents.evaluators import Evaluator
from pyggp.agents.tree_agents.perspectives import DeterministicPerspective, Perspective
from pyggp.agents.tree_agents.valuations import Valuation
from pyggp.interpreters import Development, Interpreter, Record, Role, State, Turn, View

_K = TypeVar("_K")
_P = TypeVar("_P", bound=Perspective)
_V = TypeVar("_V", bound=Valuation)


@dataclass
class Node(Generic[_P, _V, _K], abc.ABC):
    """Base class for all nodes."""

    perspective: _P
    "Perspective of the node."
    valuation: Optional[_V] = field(default=None)
    "Valuation of the node."
    turn: Optional[Turn] = field(default=None)
    "Turn done to reach the next node."
    parent: Optional[Self] = field(default=None, repr=False)
    "Parent node."
    children: Optional[Mapping[_K, Self]] = field(default=None, repr=False)
    "Children nodes."
    perspective_type: ClassVar[Type[Perspective]]
    "Type of perspective."
    valuation_type: ClassVar[Type[Valuation]]
    "Type of valuation."
    default_evaluator: ClassVar[Evaluator[Perspective, Valuation]]
    "Default evaluator to use when evaluating a node."

    @property
    def is_root(self) -> bool:
        """Whether the node is the root of the tree."""
        return self.parent is None

    @property
    def is_expanded(self) -> bool:
        """Whether the node has been expanded."""
        return self.children is not None

    @property
    def is_terminal(self) -> bool:
        """Whether the node is terminal."""
        return self.is_expanded and not self.children

    @property
    def count_expanded_children(self) -> int:
        """Number of expanded children."""
        if not self.is_expanded:
            return 0
        assert self.children is not None, "Assumption: self.is_expanded is True implies self.children is not None."
        return sum(1 for child in self.children.values() if child.is_expanded)

    @property
    def depth(self) -> int:
        """Depth of the node in the tree."""
        node = self
        depth = 0
        while not node.is_root:
            assert node.parent is not None, "Assumption: node.is_root is False implies node.parent is not None."
            node = node.parent
            depth += 1
        return depth

    @classmethod
    def from_state(cls, state: State, *, parent: Optional[Self] = None) -> Self:
        """Creates a node from a state.

        Args:
            state: State
            parent: Parent node

        Returns:
            Node

        """
        perspective = cls.perspective_type.from_state(state)
        # Disables mypy. Because cls.perspective_type is a ClassVar it cannot use TypeVars. Setting cls.perspective_type
        # needs to be done in the subclass.
        return cls.from_perspective(perspective, parent=parent)  # type: ignore[arg-type]

    @classmethod
    def from_perspective(cls, perspective: _P, *, parent: Optional[Self] = None) -> Self:
        """Creates a node from a perspective.

        Args:
            perspective: Perspective
            parent: Parent node

        Returns:
            Node

        """
        return cls(perspective=perspective, parent=parent)

    @abc.abstractmethod
    def search(
        self,
        interpreter: Interpreter,
        *,
        max_expand_depth: Optional[int] = None,
        max_expand_width: Optional[int] = None,
    ) -> None:
        """Searches the tree and updates the valuations.

        Args:
            interpreter: Interpreter
            max_expand_depth: Maximum depth to expand
            max_expand_width: Maximum width to expand

        """
        raise NotImplementedError

    @abc.abstractmethod
    def expand(self, interpreter: Interpreter) -> Mapping[_K, Self]:
        """Expands the node.

        For each possible next perspective a child is created and added to the node.

        Args:
            interpreter: Interpreter

        Returns:
            Mapping from key to child node

        """
        raise NotImplementedError

    def evaluate(self, interpreter: Interpreter, *, evaluator: Optional[Evaluator[_P, _V]] = None) -> _V:
        """Evaluates the node.

        Args:
            interpreter: Interpreter
            evaluator: Evaluator to use (defaults to self.default_evaluator)

        Returns:
            Valuation

        """
        if evaluator is not None:
            valuation = evaluator(interpreter, self.perspective)
        else:
            cls = type(self)
            # Disables mypy. Because cls.default_evaluator is a ClassVar it cannot use TypeVars. Setting
            # cls.default_evaluator needs to be done in the subclass.
            valuation = cls.default_evaluator(interpreter, self.perspective)  # type: ignore[assignment]
        if self.valuation is not None:
            self.valuation = self.valuation.propagate(valuation)
        else:
            self.valuation = valuation
        return valuation

    def propagate_back(self, valuation: _V) -> None:
        """Propagates the valuations back to the root."""
        node = self
        while not node.is_root:
            assert not node.is_root, "Assumption: node.is_root is False implies node.is_root is False."
            assert node.parent is not None, "Assumption: node.is_root is False implies node.parent is not None."
            child = node
            node = node.parent
            if node.valuation is not None:
                node.valuation = node.valuation.propagate(valuation)
            else:
                node.valuation = child.valuation
            assert node.valuation is not None, "Guarantee: node.valuation is not None."

    @abc.abstractmethod
    def develop(self, interpreter: Interpreter, ply: int, view: View) -> Self:
        """Develops the node to a given ply and view.

        Args:
            interpreter: Interpreter
            ply: Ply
            view: View

        Returns:
            New root node

        """
        raise NotImplementedError

    @abc.abstractmethod
    def trim(self) -> None:
        """Trims the node.

        Removes all children that are no longer possible to reach.

        """
        raise NotImplementedError


_DP = TypeVar("_DP", bound=DeterministicPerspective)


@dataclass
class DeterministicNode(Generic[_DP, _V], Node[_DP, _V, Turn], abc.ABC):
    """Node for deterministic games."""

    perspective_type = DeterministicPerspective

    def develop(self, interpreter: Interpreter, ply: int, view: View) -> Self:
        """Develops the node to a given ply and view.

        Args:
            interpreter: Interpreter
            ply: Ply
            view: View

        Returns:
            New root node

        """
        if self.depth == ply:
            return self
        current_state: State = cast(State, view)
        states: MutableMapping[int, State] = {ply: current_state}
        views: MutableMapping[int, Mapping[Role, View]] = {}
        turns: MutableMapping[int, Turn] = {}
        depth = self.depth
        node = self
        state = node.perspective.get_state_record()
        assert state is not None, "Assumption: DeterministicNode always has a state record."
        turn = node.turn
        states[depth] = state
        if turn is not None:
            turns[depth] = turn
        while not node.is_root:
            assert node.parent is not None, "Assumption: not node.is_root implies node.parent is not None."
            node = node.parent
            depth -= 1
            state = node.perspective.get_state_record()
            assert state is not None, "Assumption: DeterministicNode always has a state record."
            turn = node.turn
            states[depth] = state
            if turn is not None:
                turns[depth] = turn
        assert depth == 0, "Assumption: depth == 0 after traversing up to root."

        record = Record(states, views, turns)

        developments: Iterator[Development] = interpreter.get_developments(record)
        development, *_ = developments
        for development_step in development:
            node.trim()
            if node.turn is None:
                node.turn = development_step.turn
                node.trim()
            if development_step.turn is not None:
                node.expand(interpreter)
                assert node.is_expanded, "Assumption: Calling node.expand implies node.is_expanded."
                assert node.children is not None, "Assumption: node.is_expanded implies node.children is not None."
                node = node.children[development_step.turn]
                depth += 1
            assert depth == node.depth, f"Assumption: depth == node.depth. However, {depth} != {node.depth}."

        assert depth == ply, f"Assumption: depth == ply after development. However, {depth} != {ply}."

        return node

    def trim(self) -> None:
        """Trims the node.

        Removes all children that are no longer possible to reach.

        """
        if not self.children or self.turn is None or len(self.children) == 1:
            return
        self.children = {turn: child for turn, child in self.children.items() if turn == self.turn}
