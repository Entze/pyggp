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
    FrozenSet,
    Generic,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Protocol,
    Sequence,
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
from pyggp.engine_primitives import Development, DevelopmentStep, Move, Role, State, Turn, View
from pyggp.interpreters import Interpreter
from pyggp.records import ImperfectInformationRecord, PerfectInformationRecord

log = logging.getLogger("pyggp")

_U = TypeVar("_U")
_K = TypeVar("_K")  # , Turn, FrozenDict[State, FrozenSet[Turn]], None, FrozenDict[State, FrozenSet[Move]])


class Node(Protocol[_U, _K]):
    valuation: Optional[Valuation[_U]]
    parent: Optional["Node[_U, Any]"]
    children: Optional[MutableMapping[_K, "Node[_U, Any]"]]

    @property
    def depth(self) -> int:
        ...

    @property
    def unique_children(self) -> FrozenSet["Node[_U, Any]"]:
        ...

    @property
    def arity(self) -> int:
        ...

    @property
    def descendant_count(self) -> int:
        ...

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


class _AbstractNode(Node[_U, _K], Generic[_U, _K], abc.ABC):
    @property
    def depth(self) -> int:
        node: Node[_U, Any] = self
        depth = 0
        while node.parent is not None:
            node = node.parent
            depth += 1
        return depth

    @property
    def unique_children(self) -> FrozenSet["Node[_U, Any]"]:
        if self.children is None:
            return frozenset()
        return frozenset(self.children.values())

    @property
    def arity(self) -> int:
        if self.children is None:
            return 0
        return len(self.unique_children)

    @property
    def descendant_count(self) -> int:
        if self.children is None:
            return 0
        return sum(1 + child.descendant_count for child in self.unique_children)


@dataclass(unsafe_hash=True)
class PerfectInformationNode(_AbstractNode[_U, Turn], Generic[_U]):
    state: State
    turn: Optional[Turn] = field(default=None)
    valuation: Optional[Valuation[_U]] = field(default=None)
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
        if self.depth == ply:
            assert self.state == state, "Assumption: self.state == state (consistency)"
            return self

        state_record: MutableMapping[int, State] = {ply: state}
        turn_record: MutableMapping[int, Turn] = {}

        node = self
        depth = self.depth

        state_record[depth] = node.state
        if node.turn is not None:
            turn_record[depth] = node.turn

        while node.parent is not None:
            node = node.parent
            depth -= 1
            state_record[depth] = node.state
            if node.turn is not None:
                turn_record[depth] = node.turn

        record = PerfectInformationRecord(state_record, {}, turn_record)

        assert node.parent is None, "Assumption: node.parent is None (traversed up to root node)"
        assert depth == 0, "Assumption: node.parent is None implies depth == 0"

        developments: Iterable[Development] = interpreter.get_developments(record)
        development, *_ = developments

        for step, development_step in enumerate(development):
            assert depth == step, "Assumption: depth == step (consistency)"
            assert (
                development_step.state == node.state
            ), "Assumption: development_step.state == node.state (consistency)"

            assert (
                node.turn is None or development_step.turn == node.turn
            ), "Assumption: development_step.turn == node.turn (consistency)"

            node.turn = development_step.turn
            node.expand(interpreter)
            assert node.children is not None, "Assumption: node.children is not None"
            node.trim()

            if development_step.turn is not None:
                node = node.children[development_step.turn]
                depth += 1

        assert depth == ply == node.depth, "Guarantee: depth == ply == node.depth (developed the tree to current depth)"
        return node


_A = TypeVar("_A", Turn, Move)


class InformationSetNode(Node[_U, Tuple[State, _A]], Protocol[_U, _A]):
    role: Role
    possible_states: Set[State]
    parent: Optional["InformationSetNode[_U, Any]"]
    # Disables mypy. Because: InformationSetNode is a Node
    children: Optional[MutableMapping[Tuple[State, _A], "InformationSetNode[_U, Any]"]]  # type: ignore[assignment]


class _AbstractInformationSetNode(InformationSetNode[_U, _A], _AbstractNode[_U, _A], Generic[_U, _A], abc.ABC):
    def evaluate(
        self,
        interpreter: Interpreter,
        evaluator: Evaluator[_U],
        valuation_factory: Callable[[_U], Valuation[_U]],
    ) -> _U:
        self.valuation: Optional[Valuation[_U]]  # needed for mypy
        state = random.choice(tuple(self.possible_states))
        utility = evaluator(state=state, interpreter=interpreter)
        if self.valuation is not None:
            self.valuation = self.valuation.propagate(utility)
        else:
            self.valuation = valuation_factory(utility)
        assert self.valuation is not None, "Guarantee: self.valuation is not None"
        return utility

    def develop(self, interpreter: Interpreter, ply: int, view: View) -> "ImperfectInformationNode[_U]":
        if ply == self.depth:
            assert isinstance(
                self,
                (HiddenInformationSetNode, VisibleInformationSetNode),
            ), "Requirement: self is ImperfectInformationNode"
            return self

        with log_time(log, logging.DEBUG, "Gathering all records", "Gathered all records"):
            record, root = self.gather_all_records(
                ply,
                view,
                has_incomplete_information=interpreter.has_incomplete_information,
            )

        developments: Iterable[Development] = interpreter.get_developments(record)

        with log_time(log, logging.DEBUG, "Reset all records", "Reset all records"):
            self.reset_all_records_below(max_depth=ply)

        with log_time(log, logging.DEBUG, "Updating tree", "Updated tree"):
            node, visited_nodes = root.update_all_from_developments(interpreter, developments)

        assert node in visited_nodes, "Guarantee: node in visited_nodes (node was visited)"

        assert isinstance(node, VisibleInformationSetNode), "Assumption: providing a view implies visible information"
        assert node.view is None or node.view == view, "Assumption: current.view == view (consistency)"
        node.view = view

        with log_time(log, logging.DEBUG, "Trimming tree", "Trimmed tree"):
            root.trim()
            for visited in visited_nodes:
                visited.trim()

        assert node.depth == ply, "Guarantee: current.depth == ply (developed the tree to current depth)"

        return node

    def reset_all_records_below(self, max_depth: Optional[int] = None) -> None:
        assert isinstance(
            self,
            (HiddenInformationSetNode, VisibleInformationSetNode),
        ), "Assumption (ImperfectInformationNode)"
        stack: MutableSequence[ImperfectInformationNode[_U]] = [self]
        while stack:
            node = stack.pop()
            node.reset_records()
            if node.children is not None and (max_depth is None or node.depth < max_depth):
                stack.extend(node.children.values())

    def gather_all_records(
        self,
        ply: int,
        view: View,
        *,
        has_incomplete_information: bool = False,
    ) -> Tuple[ImperfectInformationRecord, "ImperfectInformationNode[_U]"]:
        possible_states_record: MutableMapping[int, FrozenSet[State]] = {}
        view_record: MutableMapping[int, Mapping[Role, View]] = {ply: {self.role: view}}
        possible_turns_record: MutableMapping[int, FrozenSet[Turn]] = {}
        rmm_record: MutableMapping[int, Mapping[Role, Move]] = {}
        assert isinstance(
            self,
            (HiddenInformationSetNode, VisibleInformationSetNode),
        ), "Assumption (ImperfectInformationNode)"
        node: ImperfectInformationNode[_U] = self

        stop = False

        while not stop:
            node.gather_records(
                possible_states_record=possible_states_record,
                view_record=view_record,
                possible_turns_record=possible_turns_record,
                rmm_record=rmm_record,
                has_incomplete_information=has_incomplete_information,
            )
            node.reset_records()

            if node.parent is not None:
                node = node.parent
            else:
                stop = True

        if not has_incomplete_information:
            state = cast(State, view)
            possible_states_record[ply] = frozenset((state,))

        return (
            ImperfectInformationRecord(
                possible_states=possible_states_record,
                views=view_record,
                possible_turns=possible_turns_record,
                role_move_map=rmm_record,
            ),
            node,
        )

    def update_all_from_developments(
        self,
        interpreter: Interpreter,
        developments: Iterable[Development],
    ) -> Tuple["ImperfectInformationNode[_U]", Sequence["ImperfectInformationNode[_U]"]]:
        assert isinstance(
            self,
            (HiddenInformationSetNode, VisibleInformationSetNode),
        ), "Assumption (ImperfectInformationNode)"
        node: ImperfectInformationNode[_U] = self
        visited: MutableSequence[ImperfectInformationNode[_U]] = []
        for development in developments:
            node = self
            for step, development_step in enumerate(development):
                assert step == node.depth, "Assumption: step == node.depth (tree consistency)"
                node.update_from_development_step(development_step)
                state, turn = development_step
                if turn is not None:
                    if not node.can_descend(state, turn):
                        fresh_children, _ = node.expand_by(interpreter, state)
                        for child in fresh_children:
                            child.reset_records()
                    assert node.can_descend(state, turn), "Assumption: node.can_descend(state, turn) (tree is expanded)"
                    node = node.descend(state, turn)
                    visited.append(node)

        return node, visited

    @abc.abstractmethod
    def gather_records(
        self,
        possible_states_record: MutableMapping[int, FrozenSet[State]],
        view_record: MutableMapping[int, Mapping[Role, View]],
        possible_turns_record: MutableMapping[int, FrozenSet[Turn]],
        rmm_record: MutableMapping[int, Mapping[Role, Move]],
        *,
        has_incomplete_information: bool = True,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def reset_records(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def can_descend(self, state: State, turn: Turn) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def descend(self, state: State, turn: Turn) -> "ImperfectInformationNode[_U]":
        raise NotImplementedError

    @abc.abstractmethod
    def update_from_development_step(self, development_step: DevelopmentStep) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def expand_by(
        self,
        interpreter: Interpreter,
        possible_state: State,
    ) -> Tuple[Iterable["ImperfectInformationNode[_U]"], Tuple[Any, ...]]:
        raise NotImplementedError


@dataclass(unsafe_hash=True)
class HiddenInformationSetNode(_AbstractInformationSetNode[_U, Turn], Generic[_U]):
    role: Role = field(hash=True)
    possible_states: Set[State] = field(default_factory=set, hash=False)
    possible_turns: Optional[Set[Turn]] = field(default=None, hash=False)
    valuation: Optional[Valuation[_U]] = field(default=None, hash=True)
    parent: Optional["ImperfectInformationNode[_U]"] = field(default=None, repr=False, hash=False)
    # Disables mypy. Because: ImperfectInformationNode is an InformationSetNode
    children: Optional[
        MutableMapping[Tuple[State, Turn], "ImperfectInformationNode[_U]"]
    ] = field(  # type: ignore[assignment]
        default=None,
        repr=False,
        hash=False,
    )

    def expand(self, interpreter: Interpreter) -> Mapping[Tuple[State, Turn], "ImperfectInformationNode[_U]"]:
        if self.children is None:
            self.children = {}
            visible_child: Optional[VisibleInformationSetNode[_U]] = None
            hidden_child: Optional[HiddenInformationSetNode[_U]] = None
            for possible_state in self.possible_states:
                _, (visible_child, hidden_child) = self.expand_by(
                    interpreter,
                    possible_state,
                    visible_child=visible_child,
                    hidden_child=hidden_child,
                )

        assert self.children is not None, "Guarantee: self.children is not None (expanded)"
        return self.children

    def expand_by(
        self,
        interpreter: Interpreter,
        possible_state: State,
        *,
        visible_child: Optional["VisibleInformationSetNode[_U]"] = None,
        hidden_child: Optional["HiddenInformationSetNode[_U]"] = None,
    ) -> Tuple[
        Iterable["ImperfectInformationNode[_U]"],
        Tuple[
            Optional["VisibleInformationSetNode[_U]"],
            Optional["HiddenInformationSetNode[_U]"],
        ],
    ]:
        if self.children is None:
            self.children = {}
        child: ImperfectInformationNode[_U]

        for child in self.children.values():
            if hidden_child is not None and visible_child is not None:
                break
            if visible_child is None and isinstance(child, VisibleInformationSetNode):
                visible_child = child
            elif hidden_child is None and isinstance(child, HiddenInformationSetNode):
                hidden_child = child
        fresh_nodes: MutableSequence[ImperfectInformationNode[_U]] = []
        for turn, next_state in interpreter.get_all_next_states(possible_state):
            roles_in_control = Interpreter.get_roles_in_control(next_state)
            key = (possible_state, turn)
            if self.role not in roles_in_control:
                if hidden_child is None:
                    hidden_child = HiddenInformationSetNode(role=self.role, parent=self)
                    fresh_nodes.append(hidden_child)
                child = hidden_child
            else:
                if visible_child is None:
                    visible_child = VisibleInformationSetNode(role=self.role, parent=self)
                    fresh_nodes.append(visible_child)
                child = visible_child
            child.possible_states.add(next_state)
            self.children[key] = child
        return fresh_nodes, (visible_child, hidden_child)

    def trim(self) -> None:
        if self.children is None or not self.children:
            return

        to_delete: MutableSequence[Tuple[State, Turn]] = []
        for state, turn in self.children:
            if (
                self.possible_turns is not None and turn not in self.possible_turns
            ) or state not in self.possible_states:
                to_delete.append((state, turn))

        for key in to_delete:
            del self.children[key]

    # Disables ARG002 (Unused method argument). Because: Implements a base class method.
    def gather_records(
        self,
        possible_states_record: MutableMapping[int, FrozenSet[State]],
        view_record: MutableMapping[int, Mapping[Role, View]],  # noqa: ARG002
        possible_turns_record: MutableMapping[int, FrozenSet[Turn]],
        rmm_record: MutableMapping[int, Mapping[Role, Move]],  # noqa: ARG002
        *,
        has_incomplete_information: bool = True,  # noqa: ARG002
    ) -> None:
        depth = self.depth
        possible_states_record[depth] = frozenset(self.possible_states)
        if self.possible_turns is not None:
            possible_turns_record[depth] = frozenset(self.possible_turns)

    def reset_records(self) -> None:
        self.possible_states.clear()
        if self.possible_turns is None:
            self.possible_turns = set()
        else:
            self.possible_turns.clear()

    def can_descend(self, state: State, turn: Turn) -> bool:
        return self.children is not None and (state, turn) in self.children

    def descend(self, state: State, turn: Turn) -> "ImperfectInformationNode[_U]":
        assert self.children is not None, "Assumption: self.children is not None (tree is expanded)"
        assert self.possible_turns is not None, "Assumption: self.possible_turns is not None (tree is expanded)"
        assert state in self.possible_states, "Assumption: state in self.possible_states (tree is expanded)"
        assert turn in self.possible_turns, "Assumption: turn in self.possible_turns (tree is expanded)"
        assert any(s == state for s, _ in self.children), (
            f"Assumption: (state, _) in self.children (tree is expanded, state={format_sorted_set(state)}, "
            f"self.children={', '.join(f'({format_sorted_set(s)}, {t})' for s, t in self.children)}"
        )
        assert any(
            t == turn for _, t in self.children
        ), f"Assumption: (_, turn) in self.children (tree is expanded, turn={turn})"
        assert (
            state,
            turn,
        ) in self.children, (
            "Assumption: (state, turn) in self.children "
            "(tree is expanded, "
            f"state={format_sorted_set(state)}, "
            f"turn={turn})"
        )
        return self.children[(state, turn)]

    def update_from_development_step(self, development_step: DevelopmentStep) -> None:
        self.possible_states.add(development_step.state)
        if self.possible_turns is None:
            self.possible_turns = set()
        if development_step.turn is not None:
            self.possible_turns.add(development_step.turn)


@dataclass(unsafe_hash=True)
class VisibleInformationSetNode(_AbstractInformationSetNode[_U, Move], Generic[_U]):
    role: Role = field(hash=True)
    possible_states: Set[State] = field(default_factory=set, hash=False)
    view: Optional[View] = field(default=None, hash=True)
    move: Optional[Move] = field(default=None, hash=True)
    valuation: Optional[Valuation[_U]] = field(default=None, hash=True)
    parent: Optional["ImperfectInformationNode[_U]"] = field(default=None, repr=False, hash=False)
    # Disables mypy. Because: ImperfectInformationNode is an InformationSetNode.
    children: Optional[
        MutableMapping[Tuple[State, Move], "ImperfectInformationNode[_U]"]
    ] = field(  # type: ignore[assignment]
        default=None,
        repr=False,
        hash=False,
    )

    def expand(self, interpreter: Interpreter) -> Mapping[Tuple[State, Move], "ImperfectInformationNode[_U]"]:
        if self.children is None:
            self.children = {}
            view_node_map: MutableMapping[View, VisibleInformationSetNode[_U]] = {}
            hidden_children: MutableMapping[Move, HiddenInformationSetNode[_U]] = {}
            for possible_state in self.possible_states:
                self.expand_by(
                    interpreter,
                    possible_state,
                    view_node_map=view_node_map,
                    hidden_children=hidden_children,
                )

        assert self.children is not None, "Guarantee: self.children is not None (expanded)"
        if __debug__ and self.view is not None:
            legal_moves = interpreter.get_legal_moves_by_role(self.view, self.role)
            possible_moves = {move for _, move in self.children}
            assert all(move in legal_moves for move in possible_moves), (
                "Guarantee: all moves are legal "
                f"(# of possible_states: {len(self.possible_states)}, "
                f"possible moves: {', '.join(str(move) for move in possible_moves)}, "
                f"legal moves: {', '.join(str(move) for move in legal_moves)})"
            )
        return self.children

    def expand_by(
        self,
        interpreter: Interpreter,
        possible_state: State,
        *,
        view_node_map: Optional[MutableMapping[View, "VisibleInformationSetNode[_U]"]] = None,
        hidden_children: Optional[MutableMapping[Move, HiddenInformationSetNode[_U]]] = None,
    ) -> Tuple[Iterable["ImperfectInformationNode[_U]"], Tuple[()]]:
        if self.children is None:
            self.children = {}
        child: ImperfectInformationNode[_U]
        move: Move
        view: View
        if view_node_map is None or hidden_children is None:
            if view_node_map is None:
                view_node_map = {}
            if hidden_children is None:
                hidden_children = {}
            self._restore_expand_state(interpreter, view_node_map, hidden_children)

        fresh_children: MutableSequence[ImperfectInformationNode[_U]] = []
        for turn, next_state in interpreter.get_all_next_states(possible_state):
            roles_in_control = Interpreter.get_roles_in_control(next_state)
            assert self.role in turn, f"Assumption: self.role in turn (role={self.role}, turn={turn})"
            move = turn[self.role]
            key = (possible_state, move)
            if self.role not in roles_in_control:
                if move not in hidden_children:
                    child = HiddenInformationSetNode(role=self.role, parent=self)
                    hidden_children[move] = child
                    fresh_children.append(child)
                child = hidden_children[move]
            else:
                view = interpreter.get_sees_by_role(next_state, self.role)
                if view not in view_node_map:
                    child = VisibleInformationSetNode(role=self.role, parent=self, view=view)
                    view_node_map[view] = child
                    fresh_children.append(child)
                child = view_node_map[view]
            child.possible_states.add(next_state)
            self.children[key] = child
        return (fresh_children, ())

    def _restore_expand_state(
        self,
        interpreter: Interpreter,
        view_node_map: MutableMapping[View, "VisibleInformationSetNode[_U]"],
        hidden_children: MutableMapping[Move, HiddenInformationSetNode[_U]],
    ) -> None:
        assert self.children is not None, "Assumption: self.children is not None"
        for (state, move), child in self.children.items():
            if move not in hidden_children and isinstance(child, HiddenInformationSetNode):
                hidden_children[move] = child
            elif isinstance(child, VisibleInformationSetNode):
                view = interpreter.get_sees_by_role(state, self.role)
                view_node_map[view] = child

    def trim(self) -> None:
        if self.children is None or not self.children:
            return

        to_delete: MutableSequence[Tuple[State, Move]] = []

        for state, move in self.children:
            if (self.move is not None and move != self.move) or state not in self.possible_states:
                to_delete.append((state, move))

        for key in to_delete:
            del self.children[key]

    def gather_records(
        self,
        possible_states_record: MutableMapping[int, FrozenSet[State]],
        view_record: MutableMapping[int, Mapping[Role, View]],
        # Disables ARG002 (Unused method argument). Because: Implements a base class method.
        possible_turns_record: MutableMapping[int, FrozenSet[Turn]],  # noqa: ARG002
        rmm_record: MutableMapping[int, Mapping[Role, Move]],
        *,
        has_incomplete_information: bool = True,
    ) -> None:
        depth = self.depth
        possible_states_record[depth] = frozenset(self.possible_states)
        if self.view is not None:
            if not has_incomplete_information:
                state = cast(State, self.view)
                possible_states_record[depth] = frozenset((state,))
            view_record[depth] = {self.role: self.view}
        if self.move is not None:
            rmm_record[depth] = {self.role: self.move}

    def reset_records(self) -> None:
        self.possible_states.clear()

    def can_descend(self, state: State, turn: Turn) -> bool:
        if self.children is None:
            return False
        assert (
            self.role in turn
        ), "Assumption: VisibleInformationSetNode only contains possible_states where the role is in control"
        move = turn[self.role]
        return (state, move) in self.children

    def descend(self, state: State, turn: Turn) -> "ImperfectInformationNode[_U]":
        assert self.children is not None, "Assumption: self.children is not None (tree is expanded)"
        assert (
            self.role in turn
        ), "Assumption: VisibleInformationSetNode only contains possible_states where the role is in control"
        move = turn[self.role]
        assert any(
            state == s for s, _ in self.children
        ), "Assumption: (state, _) is in self.children (tree is expanded)"
        assert any(move == m for _, m in self.children), "Assumption: (_, move) is in self.children (tree is expanded)"
        assert (state, move) in self.children, "Assumption: (state, move) in self.children (tree is expanded)"
        return self.children[(state, move)]

    def update_from_development_step(self, development_step: DevelopmentStep) -> None:
        self.possible_states.add(development_step.state)


ImperfectInformationNode = Union[HiddenInformationSetNode[_U], VisibleInformationSetNode[_U]]
