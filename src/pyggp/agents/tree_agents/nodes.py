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

from pyggp._logging import format_sorted_set, log_time, rich
from pyggp.agents.tree_agents.evaluators import Evaluator
from pyggp.agents.tree_agents.valuations import Valuation
from pyggp.engine_primitives import Development, Move, Role, State, Turn, View
from pyggp.interpreters import Interpreter
from pyggp.records import ImperfectInformationRecord, PerfectInformationRecord, Record

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

    @property
    def max_height(self) -> int:
        """Maximum height of the node in the tree defined by the distance to the leaves."""

    @property
    def root(self) -> "Node[_U, Any]":
        """Root of the tree."""

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

    @property
    def max_height(self) -> int:
        if self.children is None or not self.children:
            return 0
        return 1 + max(child.max_height for child in self.children.values())

    @property
    def root(self) -> "Node[_U, Any]":
        node = self
        while node.parent is not None:
            node = node.parent
        return node


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

    def __rich__(self) -> str:
        valuation_str = f"valuation={rich(self.valuation)}"
        depth_str = f"depth={self.depth}"
        max_height_str = f"max_height={self.max_height}"
        avg_height_str = f"avg_height={self.avg_height:.2f}"
        arity_str = f"arity={self.arity}"
        information_str = f"\\[{valuation_str}, {depth_str}, {max_height_str}, {avg_height_str}, {arity_str}]"
        return f"{self.__class__.__name__}{information_str}()"

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
    fully_enumerated: bool
    parent: Optional["InformationSetNode[_U, Any]"]
    # Disables mypy. Because: InformationSetNode is a Node
    children: Optional[MutableMapping[Tuple[State, _A], "InformationSetNode[_U, Any]"]]  # type: ignore[assignment]
    fully_expanded: bool

    def branch(self, interpreter: Interpreter, state: State) -> None:
        """Branches the tree assuming the given state."""

    def descend(self, state: State, turn: Turn) -> Optional["InformationSetNode[_U, Any]"]:
        """Descends the tree an edge consistent with the given state and turn or returns None if impossible."""

    def get_determinization(self) -> State:
        """Retrieves a possible state."""

    def cut(self, interpreter: Interpreter) -> None:
        """Remove impossible states from possible_states."""

    def gather_record(self, *, has_incomplete_information: bool = True) -> Record:
        """Gathers a minimal record to reconstruct current possible states."""

    def fill(self, interpreter: Interpreter) -> None:
        """Fills the node with all possible states consistent with the given views and moves."""


class _AbstractInformationSetNode(InformationSetNode[_U, _A], _AbstractNode[_U, _A], Generic[_U, _A], abc.ABC):
    def __rich__(self) -> str:
        valuation_str = f"valuation={rich(self.valuation)}"
        depth_str = f"depth={self.depth}"
        max_height_str = f"max_height={self.max_height}"
        avg_height_str = f"avg_height={self.avg_height:.2f}"
        arity_str = f"arity={self.arity}"
        fully_expanded_str = f"fully_expanded, " if self.fully_expanded else ""
        transitions_str = f"transitions={len(self.children) if self.children else 0}"
        fully_enumerated_str = f"fully_enumerated, " if self.fully_enumerated else ""
        possible_states_str = f"possible_states={len(self.possible_states)}"
        information_str = (
            f"\\[{valuation_str}, {depth_str}, {max_height_str}, {avg_height_str}, {arity_str}, "
            f"{fully_expanded_str}{transitions_str}, {fully_enumerated_str}{possible_states_str}]"
        )
        return f"{self.__class__.__name__}{information_str}()"

    def evaluate(
        self,
        interpreter: Interpreter,
        evaluator: Evaluator[_U],
        valuation_factory: Callable[[_U], Valuation[_U]],
        state: Optional[State] = None,
    ) -> _U:
        self.valuation: Optional[Valuation[_U]]  # needed for mypy
        if state is None:
            state = self.get_determinization()
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
        assert ply == node.depth, f"Guarantee: ply == node.depth == depth (ply={ply}, node.depth={node.depth})"
        assert isinstance(node, VisibleInformationSetNode), "Guarantee: node is VisibleInformationSetNode"
        assert node.view is None or node.view == view, "Assumption: node.view == view (consistency)"
        node.view = view

        if node.fully_enumerated:
            with log_time(
                log,
                logging.DEBUG,
                begin_msg=lambda: "Cutting node from %s possible_states" % len(node.possible_states),
                end_msg=lambda: "Cut node to %s possible_states" % len(node.possible_states),
                abort_msg="Aborted cutting node",
            ):
                node.cut(interpreter=interpreter)

            with log_time(
                log,
                logging.DEBUG,
                begin_msg=lambda: "Trimming node from %s transitions" % (len(self.children) if self.children else 0),
                end_msg=lambda: "Trimmed node to %s transitions" % (len(self.children) if self.children else 0),
                abort_msg="Aborted trimming node",
            ):
                node.trim()
            node.parent = None

        return node

    def _reroot(self, interpreter: Interpreter, ply: int, view: View) -> "VisibleInformationSetNode[_U]":
        node = self

        while node.depth < ply and node._can_walk(ply=ply, view=view):
            node = node._walk(ply=ply, view=view)

        if node.depth < ply:
            node = node._dig(interpreter=interpreter, ply=ply, view=view)

        assert node.depth == ply, f"Guarantee: node.depth == ply (node.depth={node.depth}, ply={ply})"
        assert isinstance(node, VisibleInformationSetNode), "Guarantee: node is VisibleInformationSetNode"
        return node

    def _dig(self, interpreter: Interpreter, ply: int, view: View) -> "VisibleInformationSetNode[_U]":
        record = self.gather_record(
            has_incomplete_information=interpreter.has_incomplete_information,
            views={ply: view},
        )

        developments = interpreter.get_developments(record=record)
        node = self
        while node.depth > record.offset:
            node = node.parent
        old_root = node
        for development in developments:
            node = old_root
            for step, development_step in enumerate(development):
                state = development_step.state
                turn = development_step.turn
                if turn is not None:
                    next_state = development[step + 1].state
                    node._initialize_children()
                    node._branch_by(
                        interpreter=interpreter,
                        state=state,
                        turn=turn,
                        next_state=next_state,
                        fully_enumerated=False,
                        fully_expanded=False,
                    )
                    node = node.descend(state, turn)

                if node is None or node.depth == ply:
                    break
            if node is not None and node.depth == ply and isinstance(node, VisibleInformationSetNode):
                break

        assert isinstance(node, VisibleInformationSetNode), "Guarantee: node is VisibleInformationSetNode"

        return node

    def _initialize_children(self) -> None:
        if self.children is None:
            self._reset_children()

    @abc.abstractmethod
    def _reset_children(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def _can_walk(self, ply: int, view: View) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def _walk(self, ply: int, view: View) -> "ImperfectInformationNode[_U]":
        raise NotImplementedError

    @abc.abstractmethod
    def _branch_by(
        self,
        interpreter: Interpreter,
        state: State,
        turn: Turn,
        next_state: State,
        *,
        fully_expanded=True,
        fully_enumerated=True,
    ) -> "ImperfectInformationNode[_U]":
        raise NotImplementedError

    def fill(self, interpreter: Interpreter) -> None:
        if self.fully_enumerated:
            return

        record = self.gather_record(has_incomplete_information=interpreter.has_incomplete_information)

        possible_states = interpreter.get_possible_states(record=record, ply=self.depth)
        self.possible_states = set(possible_states)
        self.fully_enumerated = True

    def gather_record(
        self,
        *,
        has_incomplete_information: bool = True,
        views: Optional[MutableMapping[int, View]] = None,
        moves: Optional[MutableMapping[int, Move]] = None,
    ) -> Record:
        if has_incomplete_information:
            return self._gather_record_incomplete_information(views=views, moves=moves)
        return self._gather_record_complete_information(views=views, moves=moves)

    def _gather_record_incomplete_information(
        self,
        *,
        views: Optional[MutableMapping[int, View]] = None,
        moves: Optional[MutableMapping[int, Move]] = None,
    ) -> ImperfectInformationRecord:
        last_known_possible_states = None
        last_known_ply = None
        if views is None:
            views = {}
        if moves is None:
            moves = {}

        node = self
        while node is not None and last_known_possible_states is None:
            if node.fully_enumerated:
                last_known_possible_states = node.possible_states
                last_known_ply = node.depth
            if isinstance(node, VisibleInformationSetNode):
                if node.view is not None:
                    views[node.depth] = node.view
                if node.move is not None:
                    moves[node.depth] = node.move
            node = node.parent

        assert last_known_possible_states is not None, "Assumption: last_known_possible_states is not None"
        assert last_known_ply is not None, "Assumption: last_known_ply is not None"

        return ImperfectInformationRecord(
            possible_states={last_known_ply: frozenset(last_known_possible_states)},
            views={ply: {self.role: view} for ply, view in views.items()},
            role_move_map={ply: {self.role: move} for ply, move in moves.items()},
        )

    def _gather_record_complete_information(
        self,
        *,
        views: Optional[MutableMapping[int, View]] = None,
        moves: Optional[MutableMapping[int, Move]] = None,
    ) -> PerfectInformationRecord:
        states = {}

        node = self
        while node is not None and not states:
            if isinstance(node, VisibleInformationSetNode):
                if node.view is not None:
                    state = cast(State, node.view)
                    states[node.depth] = state
            elif node.fully_enumerated and len(node.possible_states) == 1:
                (state,) = node.possible_states
                states[node.depth] = state
            node = node.parent

        if views is not None:
            states.update((ply, cast(State, view)) for ply, view in views.items())
        return PerfectInformationRecord(
            states={ply: state for ply, state in states.items()},
        )

    def get_determinization(self) -> State:
        if getattr(self, "_possible_state_seq", None) is None or len(self._possible_state_seq) != len(
            self.possible_states,
        ):
            self._possible_state_seq = tuple(self.possible_states)
        return random.choice(self._possible_state_seq)

    def is_in_control(self, role: Role) -> bool:
        assert any(role in Interpreter.get_roles_in_control(state) for state in self.possible_states) == all(
            role in Interpreter.get_roles_in_control(state) for state in self.possible_states
        ), "Assumption: If in any state role is in control, then in all states role is in control"
        return self.possible_states and role in Interpreter.get_roles_in_control(next(iter(self.possible_states)))


@dataclass(unsafe_hash=True)
class HiddenInformationSetNode(_AbstractInformationSetNode[_U, Turn], Generic[_U]):
    role: Role = field(hash=True)
    possible_states: Set[State] = field(default_factory=set, hash=False)
    fully_enumerated: bool = field(default=False, hash=False)
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
    fully_expanded: bool = field(default=False, hash=False)
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

    @property
    def max_height(self) -> int:
        if self.visible_child is None and self.hidden_child is None:
            return 0
        if self.visible_child is None:
            return 1 + self.hidden_child.max_height
        if self.hidden_child is None:
            return 1 + self.visible_child.max_height
        return 1 + max(self.visible_child.max_height, self.hidden_child.max_height)

    def _can_walk(self, ply: int, view: View) -> bool:
        return (
            ply <= self.depth
            or (ply == self.depth + 1 and self.visible_child is not None)
            or (ply > self.depth + 1 and self.hidden_child is not None)
        )

    def _walk(self, ply: int, view: View) -> "ImperfectInformationNode[_U]":
        if ply == self.depth:
            return self
        if ply < self.depth:
            return self.parent
        if ply == self.depth + 1:
            return self.visible_child
        return self.hidden_child

    def expand(self, interpreter: Interpreter) -> Mapping[Tuple[State, Turn], "ImperfectInformationNode[_U]"]:
        if not self.fully_expanded or self.children is None:
            self._initialize_children()
            for possible_state in self.possible_states:
                for turn, next_state in interpreter.get_all_next_states(possible_state):
                    self._branch_by(
                        interpreter=interpreter,
                        state=possible_state,
                        turn=turn,
                        next_state=next_state,
                        fully_expanded=False,
                        fully_enumerated=self.fully_enumerated,
                    )
            self.fully_expanded = self.fully_enumerated

        assert self.children is not None, "Guarantee: self.children is not None"
        assert self.fully_expanded == self.fully_enumerated, "Guarantee: self.fully_expanded == self.fully_enumerated"
        return self.children

    def _reset_children(self) -> None:
        self.fully_expanded = False
        self.children = {}
        self.hidden_child = None
        self.visible_child = None

    def branch(self, interpreter: Interpreter, state: State) -> None:
        if self.children is None or (self.children is not None and not self.fully_expanded):
            self._initialize_children()
            for turn, next_state in interpreter.get_all_next_states(state):
                self._branch_by(
                    interpreter=interpreter,
                    state=state,
                    turn=turn,
                    next_state=next_state,
                    fully_expanded=False,
                    fully_enumerated=False,
                )
            if self.fully_enumerated and all(
                any(possible_state == state for (state, _) in self.children) for possible_state in self.possible_states
            ):
                self.fully_expanded = True
                if self.visible_child is not None:
                    self.visible_child.fully_enumerated = True
                if self.hidden_child is not None:
                    self.hidden_child.fully_enumerated = True

        assert self.children is not None, "Guarantee: self.children is not None"

    def _branch_by(
        self,
        interpreter: Interpreter,
        state: State,
        turn: Turn,
        next_state: State,
        *,
        fully_expanded=True,
        fully_enumerated=True,
    ) -> None:
        roles_in_control = Interpreter.get_roles_in_control(next_state)
        key = (state, turn)
        if key in self.children:
            child = self.children[key]
        elif self.role not in roles_in_control:
            if self.hidden_child is None:
                self.hidden_child = HiddenInformationSetNode(
                    role=self.role,
                    parent=self,
                    depth=self.depth + 1,
                    fully_expanded=fully_expanded,
                    fully_enumerated=fully_enumerated,
                )
            child = self.hidden_child
        else:
            if self.visible_child is None:
                self.visible_child = VisibleInformationSetNode(
                    role=self.role,
                    parent=self,
                    depth=self.depth + 1,
                    fully_expanded=fully_expanded,
                    fully_enumerated=fully_enumerated,
                )
            child = self.visible_child
        child.possible_states.add(next_state)
        self.children[key] = child

    def descend(self, state: State, turn: Turn) -> Optional["InformationSetNode[_U, Any]"]:
        if self.children is None:
            return None
        return self.children.get((state, turn))

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
    fully_enumerated: bool = field(default=False, hash=False)
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
    fully_expanded: bool = field(default=False, hash=False)
    view_to_visiblechild: Optional[MutableMapping[View, "VisibleInformationSetNode[_U]"]] = field(
        default=None,
        repr=False,
        hash=False,
    )
    move_to_hiddenchild: Optional[MutableMapping[Move, HiddenInformationSetNode[_U]]] = field(
        default=None,
        repr=False,
        hash=False,
    )

    @property
    def arity(self) -> int:
        visible_children = 0 if self.view_to_visiblechild is None else len(self.view_to_visiblechild)
        hidden_children = 0 if self.move_to_hiddenchild is None else len(self.move_to_hiddenchild)
        return visible_children + hidden_children

    @property
    def avg_height(self) -> float:
        if self.children is None or not self.children:
            return 0
        total_visible_avg_height = 0
        if self.view_to_visiblechild:
            total_visible_avg_height = sum(child.avg_height for child in self.view_to_visiblechild.values())
        total_hidden_avg_height = 0
        if self.move_to_hiddenchild:
            total_hidden_avg_height = sum(child.avg_height for child in self.move_to_hiddenchild.values())
        total_avg_height = total_visible_avg_height + total_hidden_avg_height
        if total_avg_height == 0:
            return total_avg_height
        return 1 + (total_avg_height / self.arity)

    @property
    def max_height(self) -> int:
        if self.children is None or not self.children:
            return 0
        max_visible_height = 0
        if self.view_to_visiblechild:
            max_visible_height = max(child.max_height for child in self.view_to_visiblechild.values())
        max_hidden_height = 0
        if self.move_to_hiddenchild:
            max_hidden_height = max(child.max_height for child in self.move_to_hiddenchild.values())
        max_height = max(max_visible_height, max_hidden_height)
        if max_height == 0:
            return max_height
        return 1 + max_height

    def _can_walk(self, ply: int, view: View) -> bool:
        return ply <= self.depth or (
            self.children
            and (
                (ply == self.depth + 1 and self.view_to_visiblechild is not None and view in self.view_to_visiblechild)
                or (
                    ply > self.depth + 1
                    and self.move_to_hiddenchild is not None
                    and self.move in self.move_to_hiddenchild
                )
            )
        )

    def _walk(self, ply: int, view: View) -> "ImperfectInformationNode[_U]":
        if ply == self.depth:
            return self
        if ply < self.depth:
            return self.parent
        if ply == self.depth + 1:
            return self.view_to_visiblechild[view]
        return self.move_to_hiddenchild[self.move]

    def expand(self, interpreter: Interpreter) -> Mapping[Tuple[State, Move], "ImperfectInformationNode[_U]"]:
        if not self.fully_expanded or self.children is None:
            self._initialize_children()
            for possible_state in self.possible_states:
                for turn, next_state in interpreter.get_all_next_states(possible_state):
                    self._branch_by(
                        interpreter=interpreter,
                        state=possible_state,
                        turn=turn,
                        next_state=next_state,
                        fully_expanded=False,
                        fully_enumerated=self.fully_enumerated,
                    )
            self.fully_expanded = self.fully_enumerated

        assert self.children is not None, "Guarantee: self.children is not None (expanded)"
        return self.children

    def _reset_children(self) -> None:
        self.children = {}
        self.view_to_visiblechild = {}
        self.move_to_hiddenchild = {}

    def branch(self, interpreter: Interpreter, state: State) -> None:
        if self.children is None or (self.children is not None and not self.fully_expanded):
            self._initialize_children()
            for turn, next_state in interpreter.get_all_next_states(state):
                self._branch_by(
                    interpreter=interpreter,
                    state=state,
                    turn=turn,
                    next_state=next_state,
                    fully_expanded=False,
                    fully_enumerated=False,
                )
            if self.fully_enumerated and all(
                any(possible_state == state for (state, _) in self.children) for possible_state in self.possible_states
            ):
                self.fully_expanded = True
                for child in self.view_to_visiblechild.values():
                    child.fully_enumerated = True
                for child in self.move_to_hiddenchild.values():
                    child.fully_enumerated = True

        assert self.children is not None, "Guarantee: self.children is not None"

    def _branch_by(
        self,
        interpreter: Interpreter,
        state: State,
        turn: Turn,
        next_state: State,
        *,
        fully_expanded=True,
        fully_enumerated=True,
    ) -> None:
        roles_in_control = Interpreter.get_roles_in_control(next_state)
        assert self.role in turn, f"Assumption: self.role in turn (role={self.role}, turn={turn})"
        move = turn[self.role]
        key = (state, move)
        if key in self.children:
            child = self.children[key]
        elif self.role not in roles_in_control:
            if move not in self.move_to_hiddenchild:
                child = HiddenInformationSetNode(
                    role=self.role,
                    parent=self,
                    depth=self.depth + 1,
                    fully_expanded=fully_expanded,
                    fully_enumerated=fully_enumerated,
                )
                self.move_to_hiddenchild[move] = child
            child = self.move_to_hiddenchild[move]
        else:
            view = interpreter.get_sees_by_role(next_state, self.role)
            if view not in self.view_to_visiblechild:
                child = VisibleInformationSetNode(
                    role=self.role,
                    parent=self,
                    view=view,
                    depth=self.depth + 1,
                    fully_expanded=fully_expanded,
                    fully_enumerated=fully_enumerated,
                )
                self.view_to_visiblechild[view] = child
            child = self.view_to_visiblechild[view]
        child.possible_states.add(next_state)
        self.children[key] = child

    def descend(self, state: State, turn: Turn) -> Optional["InformationSetNode[_U, Any]"]:
        if self.children is None or self.role not in turn:
            return None
        move = turn[self.role]
        key = (state, move)
        return self.children.get(key)

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
