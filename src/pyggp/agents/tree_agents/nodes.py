"""Nodes for tree agents.

Nodes can be used to represent the game tree.

"""
import abc
import logging
import random
import time
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

from pyggp._logging import format_amount, format_timedelta
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
    children: Optional[Mapping[_K, "Node[_U, Any]"]]

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

    def develop(self, interpreter: Interpreter, ply: int, view: View) -> Self:
        ...


class _AbstractNode(Node[_U, _K], Generic[_U, _K], abc.ABC):
    @property
    def depth(self) -> int:
        node = self
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
    children: Optional[Mapping[Turn, Self]] = field(default=None, repr=False, hash=False)

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

        self.children = {turn: child for turn, child in self.children.items() if self.turn == turn}

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
    children: Optional[Mapping[Tuple[State, _A], "InformationSetNode[_U, Any]"]]

    def descend(self, state: State, turn: Turn) -> "ImperfectInformationNode[_U]":
        raise NotImplementedError


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

    def develop(self, interpreter: Interpreter, ply: int, view: View) -> Self:
        if ply == self.depth:
            return self

        log.debug("Gathering all records")
        start = time.monotonic_ns()
        record, root = self.gather_all_records(
            ply,
            view,
            has_incomplete_information=interpreter.has_incomplete_information,
        )
        log.debug("Gathered all records in %s", format_timedelta((time.monotonic_ns() - start) * 1e-9))

        developments: Iterable[Development] = interpreter.get_developments(record)

        log.debug("Resetting all records")
        start = time.monotonic_ns()
        self.reset_all_records_below(max_depth=ply)
        log.debug("Reset all records in %s", format_timedelta((time.monotonic_ns() - start) * 1e-9))

        log.debug("Updating tree")
        start = time.monotonic_ns()
        node, visited_nodes = root.update_all_from_developments(interpreter, developments)
        log.debug(
            "Updated tree, visited %s nodes in %s",
            format_amount(len(visited_nodes)),
            format_timedelta((time.monotonic_ns() - start) * 1e-9),
        )
        assert node in visited_nodes, "Guarantee: node in visited_nodes (node was visited)"

        assert isinstance(node, VisibleInformationSetNode), "Assumption: providing a view implies visible information"
        assert node.view is None or node.view == view, "Assumption: current.view == view (consistency)"
        node.view = view

        log.debug("Trimming tree")
        start = time.monotonic_ns()
        root.trim()
        for visited in visited_nodes:
            visited.trim()
        log.debug("Trimmed tree in %s", format_timedelta((time.monotonic_ns() - start) * 1e-9))

        assert node.depth == ply, "Guarantee: current.depth == ply (developed the tree to current depth)"

        return node

    def reset_all_records_below(self, max_depth: Optional[int] = None) -> None:
        stack = [self]
        while stack:
            node = stack.pop()
            node.reset_records()
            if node.children is not None and (max_depth is None or node.depth < max_depth):
                stack.extend(node.children.values())

    def trim_all_below(self) -> None:
        stack = [self]
        while stack:
            node = stack.pop()
            node.trim()
            if node.children is not None:
                stack.extend(node.children.values())

    def gather_all_records(
        self,
        ply: int,
        view: View,
        *,
        has_incomplete_information: bool = False,
    ) -> Tuple[ImperfectInformationRecord, Self]:
        possible_states_record: MutableMapping[int, FrozenSet[State]] = {}
        view_record: MutableMapping[int, Mapping[Role, View]] = {ply: {self.role: view}}
        possible_turns_record: MutableMapping[int, FrozenSet[Turn]] = {}
        rmm_record: MutableMapping[int, Mapping[Role, Move]] = {}
        node = self

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
    ) -> Tuple[Self, Sequence["ImperfectInformationNode[_U]"]]:
        node = self
        visited: MutableSequence[ImperfectInformationNode[_U]] = []
        for development in developments:
            node = self
            for step, development_step in enumerate(development):
                assert step == node.depth, "Assumption: step == node.depth (tree consistency)"
                node.update_from_development_step(development_step)
                state, turn = development_step
                if turn is not None:
                    # TODO: find out if this is the cause for the bug
                    if node.children is None:
                        node.expand(interpreter)
                        assert node.children is not None, "Assumption: node.children is not None"
                        for child in node.children.values():
                            child.reset_records()
                    node = node.descend(state, turn)
                    visited.append(node)

        return node, visited

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

    def reset_records(self) -> None:
        raise NotImplementedError

    def descend(self, state: State, turn: Turn) -> "ImperfectInformationNode[_U]":
        raise NotImplementedError

    def update_from_development_step(self, development_step: DevelopmentStep) -> None:
        raise NotImplementedError


@dataclass(unsafe_hash=True)
class HiddenInformationSetNode(_AbstractInformationSetNode[_U, Turn], Generic[_U]):
    role: Role = field(hash=True)
    possible_states: Set[State] = field(default_factory=set, hash=False)
    possible_turns: Optional[Set[Turn]] = field(default=None, hash=True)
    valuation: Optional[Valuation[_U]] = field(default=None, hash=True)
    parent: Optional["ImperfectInformationNode[_U]"] = field(default=None, repr=False, hash=False)
    children: Optional[Mapping[Tuple[State, Turn], "ImperfectInformationNode[_U]"]] = field(
        default=None,
        repr=False,
        hash=False,
    )

    def expand(self, interpreter: Interpreter) -> Mapping[Tuple[State, Turn], "ImperfectInformationNode[_U]"]:
        if self.children is None:
            visible_child: Optional[VisibleInformationSetNode[_U]] = None
            hidden_child: Optional[HiddenInformationSetNode[_U]] = None
            visible_keys = set()
            hidden_keys = set()
            for possible_state in self.possible_states:
                for turn, next_state in interpreter.get_all_next_states(possible_state):
                    roles_in_control = Interpreter.get_roles_in_control(next_state)
                    key = (possible_state, turn)
                    child: ImperfectInformationNode[_U]
                    if self.role not in roles_in_control:
                        if hidden_child is None:
                            hidden_child = HiddenInformationSetNode(role=self.role, parent=self)
                        child = hidden_child
                        hidden_keys.add(key)
                    else:
                        if visible_child is None:
                            visible_child = VisibleInformationSetNode(role=self.role, parent=self)
                        child = visible_child
                        visible_keys.add(key)
                    child.possible_states.add(next_state)

            self.children = {
                key: child
                for child, keys in zip((visible_child, hidden_child), (visible_keys, hidden_keys))
                if child is not None
                for key in keys
            }
        assert self.children is not None, "Guarantee: self.children is not None (expanded)"
        return self.children

    def trim(self) -> None:
        if self.children is None or not self.children:
            return
        self.children = {
            (state, turn): child
            for (state, turn), child in self.children.items()
            if (self.possible_turns is None or turn in self.possible_turns) and state in self.possible_states
        }

    def gather_records(
        self,
        possible_states_record: MutableMapping[int, FrozenSet[State]],
        # Disables ARG002 (Unused method argument). Because: Implements a base class method.
        view_record: MutableMapping[int, Mapping[Role, View]],  # noqa: ARG002
        possible_turns_record: MutableMapping[int, FrozenSet[Turn]],
        rmm_record: MutableMapping[int, Mapping[Role, Move]],  # noqa: ARG002
        *,
        has_incomplete_information: bool = True,
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

    def descend(self, state: State, turn: Turn) -> "ImperfectInformationNode[_U]":
        assert self.children is not None, "Assumption: self.children is not None (tree is expanded)"
        assert state in self.possible_states, "Assumption: state in self.possible_states (tree is expanded)"
        assert turn in self.possible_turns, "Assumption: turn in self.possible_turns (tree is expanded)"
        assert (
            state,
            turn,
        ) in self.children, (
            f"Assumption: (state, turn) in self.children (tree is expanded, {set(self.children.keys())})"
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
    children: Optional[Mapping[Tuple[State, Move], "ImperfectInformationNode[_U]"]] = field(
        default=None,
        repr=False,
        hash=False,
    )

    def expand(self, interpreter: Interpreter) -> Mapping[Tuple[State, Move], "ImperfectInformationNode[_U]"]:
        if self.children is None:
            children: MutableMapping[Tuple[State, Move], ImperfectInformationNode[_U]] = {}
            view_node_map: MutableMapping[View, VisibleInformationSetNode[_U]] = {}
            hidden_children: MutableMapping[Move, HiddenInformationSetNode[_U]] = {}
            for possible_state in self.possible_states:
                for turn, next_state in interpreter.get_all_next_states(possible_state):
                    roles_in_control = Interpreter.get_roles_in_control(next_state)
                    assert self.role in turn, (
                        "Assumption: "
                        "VisibleInformationSetNode only contains possible_states where the role is in control"
                    )
                    move = turn[self.role]
                    key = (possible_state, move)
                    child: ImperfectInformationNode[_U]
                    if self.role not in roles_in_control:
                        if move not in hidden_children:
                            child = HiddenInformationSetNode(role=self.role, parent=self)
                            hidden_children[move] = child
                        child = hidden_children[move]
                    else:
                        view = interpreter.get_sees_by_role(next_state, self.role)
                        if view not in view_node_map:
                            view_node_map[view] = VisibleInformationSetNode(role=self.role, parent=self, view=view)
                        child = view_node_map[view]
                    child.possible_states.add(next_state)
                    children[key] = child

            self.children = children

        assert self.children is not None, "Guarantee: self.children is not None (expanded)"
        if __debug__ and self.view is not None:
            projected_states = {state for state, _ in self.children}
            assert projected_states <= self.possible_states, (
                f"Guarantee: projected_states ({len(projected_states)}) <= "
                f"self.possible_states ({len(self.possible_states)})"
            )
            legal_moves = interpreter.get_legal_moves_by_role(self.view, self.role)
            possible_moves = {move for _, move in self.children}
            assert all(move in legal_moves for move in possible_moves), (
                "Guarantee: all moves are legal "
                f"(# of possible_states: {len(self.possible_states)}, "
                f"possible moves: {', '.join(str(move) for move in possible_moves)}, "
                f"legal moves: {', '.join(str(move) for move in legal_moves)})"
            )
        return self.children

    def trim(self) -> None:
        if self.children is None or not self.children:
            return

        self.children = {
            (state, move): child
            for (state, move), child in self.children.items()
            if (self.move is None or move == self.move) and state in self.possible_states
        }

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
