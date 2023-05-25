"""Nodes for tree agents.

Nodes can be used to represent the game tree.

"""
import abc
import logging
import random
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Final,
    Generic,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from typing_extensions import Self

from pyggp._logging import format_sorted_set, log_time
from pyggp.agents.tree_agents.evaluators import Evaluator
from pyggp.agents.tree_agents.valuations import Valuation
from pyggp.engine_primitives import Development, Move, Role, State, Turn, View
from pyggp.interpreters import Interpreter
from pyggp.records import PerfectInformationRecord

log = logging.getLogger("pyggp")

_U = TypeVar("_U")
_K = TypeVar("_K")  # , Turn, FrozenDict[State, FrozenSet[Turn]], None, FrozenDict[State, FrozenSet[Move]])


# noinspection PyPropertyDefinition
class Node(Protocol[_U, _K]):
    valuation: Optional[Valuation[_U]]
    parent: Optional["Node[_U, Any]"]
    children: Optional[MutableMapping[_K, "Node[_U, Any]"]]

    @property
    def depth(self) -> int:
        """Depth of the node in the tree defined by the distance from root.

        Root has depth 0.

        Returns:
            distance from root

        """

    @property
    def arity(self) -> int:
        """Number of unique children."""

    @property
    def avg_height(self) -> float:
        """Average height of the node in the tree defined by the distance to the leaves.

        Leaves have height 0.

        Returns:
            average height of the node

        """

    def expand(self, interpreter: Interpreter) -> Mapping[_K, "Node[_U, Any]"]:
        ...

    def trim(self) -> None:
        ...

    def evaluate(
        self,
        interpreter: Interpreter,
        evaluator: Evaluator[_U],
        valuation_factory: Callable[[_U], Valuation[_U]],
    ) -> _U:
        ...

    def develop(self, interpreter: Interpreter, ply: int, view: View) -> "Node[_U, Any]":
        ...

    def is_in_control(self, role: Role) -> bool:
        ...


class _AbstractNode(Node[_U, _K], Generic[_U, _K], abc.ABC):
    @property
    def arity(self) -> int:
        if self.children is None:
            return 0
        unique_children = []
        for child in self.children.values():
            if child not in unique_children:
                unique_children.append(child)
        return len(unique_children)

    @property
    def avg_height(self) -> float:
        if self.children is None or not self.children:
            return 0.0
        unique_children = []
        for child in self.children.values():
            if child not in unique_children:
                unique_children.append(child)
        return 1.0 + sum(child.avg_height for child in unique_children) / len(unique_children)


@dataclass(unsafe_hash=True)
class PerfectInformationNode(_AbstractNode[_U, Turn], Generic[_U]):
    state: State
    turn: Optional[Turn] = field(default=None)
    valuation: Optional[Valuation[_U]] = field(default=None)
    depth: Final[int] = field(default=0)
    parent: Optional[Self] = field(default=None, repr=False, hash=False)
    # Disables mypy. Because: Self is a Node.
    children: Optional[MutableMapping[Turn, Self]] = field(  # type: ignore[assignment]
        default=None,
        repr=False,
        hash=False,
    )

    def expand(self, interpreter: Interpreter) -> Mapping[Turn, Self]:
        if self.children is None:
            self.children = {
                # Disables mypy. Because: mypy cannot infer that class is Self.
                turn: PerfectInformationNode(  # type: ignore[misc]
                    state=next_state,
                    parent=self,
                    depth=self.depth + 1,
                )
                for turn, next_state in interpreter.get_all_next_states(self.state)
            }

        assert self.children is not None, "Guarantee: self.children is not None"
        return self.children

    def trim(self) -> None:
        """Removes all impossible to reach children."""
        if not self.children or self.turn is None:
            return

        to_delete: MutableSequence[Turn] = []
        for turn in self.children:
            if self.turn != turn:
                to_delete.append(turn)

        for turn in to_delete:
            del self.children[turn]

    def evaluate(
        self,
        interpreter: Interpreter,
        evaluator: Evaluator[_U],
        valuation_factory: Callable[[_U], Valuation[_U]],
    ) -> _U:
        utility = evaluator(self.state, interpreter)
        if self.valuation is not None:
            self.valuation = self.valuation.propagate(utility)
        else:
            self.valuation = valuation_factory(utility)
        assert self.valuation is not None, "Guarantee: self.valuation is not None"
        return utility

    def develop(self, interpreter: Interpreter, ply: int, view: View) -> Self:
        state: State = cast(State, view)
        depth = self.depth
        if depth == ply:
            assert self.state == state, "Assumption: self.state == state (consistency)"
            return self

        state_record: MutableMapping[int, State] = {ply: state}
        turn_record: MutableMapping[int, Turn] = {}

        node = self

        state_record[depth] = node.state
        if node.turn is not None:
            turn_record[depth] = node.turn

        record = PerfectInformationRecord(state_record, {}, turn_record)

        developments: Iterable[Development] = interpreter.get_developments(record)
        development, *_ = developments

        for step, development_step in enumerate(development):
            assert development_step.state == node.state, (
                "Assumption: development_step.state == node.state (consistency, "
                f"development_step.state={format_sorted_set(development_step.state)}, "
                f"node.state={format_sorted_set(node.state)})"
            )

            assert (
                node.turn is None or development_step.turn == node.turn
            ), "Assumption: development_step.turn == node.turn (consistency)"

            node.turn = development_step.turn
            node.expand(interpreter)
            assert node.children is not None, "Assumption: node.children is not None"
            node.trim()

            if development_step.turn is not None:
                node = node.children[development_step.turn]

        assert ply == node.depth, "Guarantee: ply == node.depth (developed the tree to current depth)"
        return node

    def is_in_control(self, role: Role) -> bool:
        return role in Interpreter.get_roles_in_control(self.state)


_A = TypeVar("_A", Turn, Move)


class InformationSetNode(Node[_U, Tuple[State, _A]], Protocol[_U, _A]):
    role: Role
    possible_states: Set[State]
    parent: Optional["InformationSetNode[_U, Any]"]
    # Disables mypy. Because: InformationSetNode is a Node
    children: Optional[MutableMapping[Tuple[State, _A], "InformationSetNode[_U, Any]"]]  # type: ignore[assignment]

    def cut(self, interpreter: Interpreter) -> None:
        """Remove impossible states from possible_states."""


class _AbstractInformationSetNode(InformationSetNode[_U, _A], _AbstractNode[_U, _A], Generic[_U, _A], abc.ABC):
    def evaluate(
        self,
        interpreter: Interpreter,
        evaluator: Evaluator[_U],
        valuation_factory: Callable[[_U], Valuation[_U]],
        state: Optional[State] = None,
    ) -> _U:
        self.valuation: Optional[Valuation[_U]]  # needed for mypy
        if state is None:
            state = random.choice(tuple(self.possible_states))
        assert state in self.possible_states, (
            f"Assumption: state in self.possible_states (consistency, state={format_sorted_set(state)}, "
            "possible_states="
            f"{format_sorted_set(format_sorted_set(possible_state) for possible_state in self.possible_states)})"
        )
        utility = evaluator(state=state, interpreter=interpreter)
        if self.valuation is not None:
            self.valuation = self.valuation.propagate(utility)
        else:
            self.valuation = valuation_factory(utility)
        assert self.valuation is not None, "Guarantee: self.valuation is not None"
        return utility

    def develop(
        self,
        interpreter: Interpreter,
        ply: int,
        view: View,
    ) -> "ImperfectInformationNode[_U]":
        if ply == self.depth:
            assert isinstance(
                self,
                (HiddenInformationSetNode, VisibleInformationSetNode),
            ), "Requirement: self is ImperfectInformationNode"
            return self

        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg="Rerooting tree",
            end_msg="Rerooted tree",
            abort_msg="Aborted rerooting tree",
        ):
            node = self._reroot(interpreter, ply, view)
        assert ply == node.depth, "Guarantee: ply == node.depth == depth (developed the tree to current depth)"
        assert isinstance(node, VisibleInformationSetNode), "Guarantee: node is VisibleInformationSetNode"
        assert node.view is None or node.view == view, "Assumption: node.view == view (consistency)"
        node.view = view

        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg="Cutting node",
            end_msg="Cut node",
            abort_msg="Aborted cutting node",
        ):
            node.cut(interpreter=interpreter)
        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg="Trimming node",
            end_msg="Trimmed node",
            abort_msg="Aborted trimming node",
        ):
            node.trim()
        node.parent = None

        return node

    def _reroot(self, interpreter: Interpreter, ply: int, view: View) -> "VisibleInformationSetNode[_U]":
        node = self

        while node.depth != ply:
            node.expand(interpreter=interpreter)
            node = node._walk(ply, view)

        assert isinstance(node, VisibleInformationSetNode), "Guarantee: node is VisibleInformationSetNode"

        return node

    @abc.abstractmethod
    def _walk(self, ply: int, view: View) -> "ImperfectInformationNode[_U]":
        raise NotImplementedError

    def is_in_control(self, role: Role) -> bool:
        assert any(role in Interpreter.get_roles_in_control(state) for state in self.possible_states) == all(
            role in Interpreter.get_roles_in_control(state) for state in self.possible_states
        ), "Assumption: If in any state role is in control, then in all states role is in control"
        return self.possible_states and role in Interpreter.get_roles_in_control(next(iter(self.possible_states)))


@dataclass(unsafe_hash=True)
class HiddenInformationSetNode(_AbstractInformationSetNode[_U, Turn], Generic[_U]):
    role: Role = field(hash=True)
    possible_states: Set[State] = field(default_factory=set, hash=False)
    valuation: Optional[Valuation[_U]] = field(default=None, hash=True)
    depth: Final[int] = field(default=0)
    parent: Optional["ImperfectInformationNode[_U]"] = field(default=None, repr=False, hash=False)
    # Disables mypy. Because: ImperfectInformationNode is an InformationSetNode
    children: Optional[
        MutableMapping[Tuple[State, Turn], "ImperfectInformationNode[_U]"]
    ] = field(  # type: ignore[assignment]
        default=None,
        repr=False,
        hash=False,
    )
    visible_child: Optional["VisibleInformationSetNode[_U]"] = field(default=None, repr=False, hash=False)
    hidden_child: Optional["HiddenInformationSetNode[_U]"] = field(default=None, repr=False, hash=False)

    @property
    def arity(self) -> int:
        return int(self.visible_child is not None) + int(self.hidden_child is not None)

    @property
    def avg_height(self) -> float:
        if self.visible_child is None and self.hidden_child is None:
            return 0.0
        if self.visible_child is None:
            return 1.0 + self.hidden_child.avg_height
        if self.hidden_child is None:
            return 1.0 + self.visible_child.avg_height
        return 1.0 + (self.visible_child.avg_height + self.hidden_child.avg_height) / 2.0

    def _walk(self, ply: int, view: View) -> "ImperfectInformationNode[_U]":
        if ply == self.depth:
            return self
        if ply < self.depth:
            return self.parent
        if ply == self.depth + 1:
            return self.visible_child
        return self.hidden_child

    def expand(self, interpreter: Interpreter) -> Mapping[Tuple[State, Turn], "ImperfectInformationNode[_U]"]:
        if self.children is None:
            self.children = {}
            for possible_state in self.possible_states:
                for turn, next_state in interpreter.get_all_next_states(possible_state):
                    roles_in_control = Interpreter.get_roles_in_control(next_state)
                    key = (possible_state, turn)
                    if self.role not in roles_in_control:
                        if self.hidden_child is None:
                            self.hidden_child = HiddenInformationSetNode(
                                role=self.role,
                                parent=self,
                                depth=self.depth + 1,
                            )
                        child = self.hidden_child
                    else:
                        if self.visible_child is None:
                            self.visible_child = VisibleInformationSetNode(
                                role=self.role,
                                parent=self,
                                depth=self.depth + 1,
                            )
                        child = self.visible_child
                    child.possible_states.add(next_state)
                    self.children[key] = child

        assert self.children is not None, "Guarantee: self.children is not None (expanded)"
        return self.children

    def trim(self) -> None:
        if self.children is None or not self.children:
            return

        to_delete: Set[Tuple[State, Turn]] = set()

        for state, turn in self.children:
            if state not in self.possible_states:
                to_delete.add((state, turn))

        if self.visible_child is not None and self.visible_child.view is not None:
            for key, child in self.children.items():
                if child == self.hidden_child:
                    to_delete.add(key)
            self.hidden_child = None

        for key in to_delete:
            del self.children[key]

    def cut(self, interpreter: Interpreter) -> None:
        if self.children is None or not self.children or self.visible_child is None or self.visible_child.view is None:
            return

        next_view = self.visible_child.view
        self.possible_states = {
            state
            for state in self.possible_states
            if any(
                next_view <= next_state and interpreter.get_sees_by_role(next_state, self.role) == next_view
                for _, next_state in interpreter.get_all_next_states(state)
            )
        }


@dataclass(unsafe_hash=True)
class VisibleInformationSetNode(_AbstractInformationSetNode[_U, Move], Generic[_U]):
    role: Role = field(hash=True)
    possible_states: Set[State] = field(default_factory=set, hash=False)
    view: Optional[View] = field(default=None, hash=True)
    move: Optional[Move] = field(default=None, hash=True)
    valuation: Optional[Valuation[_U]] = field(default=None, hash=True)
    depth: Final[int] = field(default=0)
    parent: Optional["ImperfectInformationNode[_U]"] = field(default=None, repr=False, hash=False)
    # Disables mypy. Because: ImperfectInformationNode is an InformationSetNode.
    children: Optional[
        MutableMapping[Tuple[State, Move], "ImperfectInformationNode[_U]"]
    ] = field(  # type: ignore[assignment]
        default=None,
        repr=False,
        hash=False,
    )

    def _walk(self, ply: int, view: View) -> "ImperfectInformationNode[_U]":
        if ply == self.depth:
            return self
        if ply < self.depth:
            return self.parent
        for state in self.possible_states:
            if (state, self.move) not in self.children:
                continue
            child = self.children[(state, self.move)]
            if ply == self.depth + 1 and isinstance(child, VisibleInformationSetNode) and child.view == view:
                return child
            elif ply > self.depth + 1 and isinstance(child, HiddenInformationSetNode):
                return child

    def expand(self, interpreter: Interpreter) -> Mapping[Tuple[State, Move], "ImperfectInformationNode[_U]"]:
        if self.children is None:
            self.children = {}
            view_node_map: MutableMapping[View, VisibleInformationSetNode[_U]] = {}
            hidden_children: MutableMapping[Move, HiddenInformationSetNode[_U]] = {}
            for possible_state in self.possible_states:
                for turn, next_state in interpreter.get_all_next_states(possible_state):
                    roles_in_control = Interpreter.get_roles_in_control(next_state)
                    assert self.role in turn, f"Assumption: self.role in turn (role={self.role}, turn={turn})"
                    move = turn[self.role]
                    key = (possible_state, move)
                    if self.role not in roles_in_control:
                        if move not in hidden_children:
                            child = HiddenInformationSetNode(role=self.role, parent=self, depth=self.depth + 1)
                            hidden_children[move] = child
                        child = hidden_children[move]
                    else:
                        view = interpreter.get_sees_by_role(next_state, self.role)
                        if view not in view_node_map:
                            child = VisibleInformationSetNode(
                                role=self.role,
                                parent=self,
                                view=view,
                                depth=self.depth + 1,
                            )
                            view_node_map[view] = child
                        child = view_node_map[view]
                    child.possible_states.add(next_state)
                    self.children[key] = child

        assert self.children is not None, "Guarantee: self.children is not None (expanded)"
        return self.children

    def trim(self) -> None:
        if self.children is None or not self.children:
            return

        to_delete: MutableSequence[Tuple[State, Move]] = []

        for state, move in self.children:
            if (self.move is not None and move != self.move) or state not in self.possible_states:
                to_delete.append((state, move))

        for key in to_delete:
            del self.children[key]

    def cut(self, interpreter: Interpreter) -> None:
        if self.view is None:
            return

        self.possible_states = {
            state
            for state in self.possible_states
            if self.view <= state and interpreter.get_sees_by_role(state, self.role) == self.view
        }


ImperfectInformationNode = Union[HiddenInformationSetNode[_U], VisibleInformationSetNode[_U]]
