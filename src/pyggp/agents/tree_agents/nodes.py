import abc
from dataclasses import dataclass
from typing import Iterable, Iterator, Mapping, Optional, Self, Sequence, Tuple

from pyggp.agents.tree_agents.valuations import Valuation
from pyggp.exceptions.node_exceptions import (
    MultipleDevelopmentsStateNodeError,
    RoleMoveMappingMismatchNodeError,
    StateMismatchNodeError,
)
from pyggp.gdl import (
    ConcreteRole,
    ConcreteRoleMoveMapping,
    ConcreteRoleMoveMappingRecord,
    ConcreteRoleMovePairing,
    Development,
    Move,
    SeesRecord,
    State,
    StateRecord,
)
from pyggp.interpreters import Interpreter


@dataclass
class Node:
    parent: Optional[Self] = None
    role_move_mapping: Optional[ConcreteRoleMoveMapping] = None
    children: Optional[Mapping[ConcreteRoleMovePairing, Self]] = None
    valuation: Optional[Valuation] = None

    @property
    @abc.abstractmethod
    def states(self) -> Iterator[State]:
        raise NotImplementedError

    @property
    def root(self) -> Self:
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def is_terminal(self) -> bool:
        return self.is_expanded and not self.children

    @property
    def is_determined(self) -> bool:
        return self.role_move_mapping is not None

    @property
    def is_expanded(self) -> bool:
        return self.children is not None

    @property
    def depth(self) -> int:
        node = self
        depth = 0
        while node.parent is not None:
            node = node.parent
            depth += 1
        return depth

    @property
    def height(self) -> int:
        queue = [(0, self)]
        height = 0
        while queue:
            height, node = queue.pop(0)
            if node.is_expanded:
                queue.extend((height + 1, child) for child in node.children.values())
        return height

    @abc.abstractmethod
    def get_records(self) -> Tuple[StateRecord, SeesRecord, ConcreteRoleMoveMappingRecord]:
        raise NotImplementedError

    @abc.abstractmethod
    def reconstruct(self, *developments: Development) -> Self:
        raise NotImplementedError

    def trim(self) -> None:
        if not self.is_expanded or not self.is_determined:
            return
        role_move_pairing: ConcreteRoleMovePairing = frozenset(self.role_move_mapping.items())
        self.children = {role_move_pairing: self.children[role_move_pairing]}

    @abc.abstractmethod
    def expand(self, interpreter: Interpreter, /, max_width: Optional[int] = None) -> None:
        raise NotImplementedError


@dataclass
class StateNode(Node):
    state: Optional[State] = None

    def __post_init__(self) -> None:
        if self.state is None:
            raise TypeError(f"{self.__class__.__name__}.__init__() missing 1 required positional argument: 'state'")

    @property
    def states(self) -> Iterator[State]:
        yield self.state

    def get_records(self) -> Tuple[StateRecord, SeesRecord, ConcreteRoleMoveMappingRecord]:
        ply = self.depth
        node = self
        state_record = {ply: self.state}
        sees_record = {}
        move_record = {}
        if self.is_determined:
            move_record[ply] = self.role_move_mapping
        while not node.is_root:
            node = node.parent
            ply -= 1
            state_record[ply] = node.state
            if node.is_determined:
                move_record[ply] = node.role_move_mapping
        return state_record, sees_record, move_record

    def reconstruct(self, development: Development, *developments: Development) -> Self:
        if len(developments) > 0:
            raise MultipleDevelopmentsStateNodeError

        old_node = self
        old_ply = self.depth
        node = self
        ply = self.depth
        direction = -1
        while True:
            state, _sees, role_move_mapping = development[ply]
            if node.state != state:
                raise StateMismatchNodeError
            if node.role_move_mapping is not None:
                if node.role_move_mapping != role_move_mapping:
                    raise RoleMoveMappingMismatchNodeError
            else:
                node.role_move_mapping = role_move_mapping
            if node.is_root:
                direction = 1
                node = old_node
                ply = old_ply
                role_move_mapping = node.role_move_mapping
            if ply >= len(development) or not node.is_expanded or node.is_terminal:
                break
            ply += direction
            if direction > 0:
                role_move_pairing: ConcreteRoleMovePairing = frozenset(role_move_mapping.items())
                node = node.children[role_move_pairing]
            else:
                node = node.parent

        return node

    def expand(self, interpreter: Interpreter, /, max_width: Optional[int] = None) -> None:
        return
        if self.is_expanded:
            return
        self.children = {}
        legal_moves = interpreter.get_legal_moves(self.state)
        roles_in_control = Interpreter.get_roles_in_control(self.state)
        pools: Iterable[Sequence[Tuple[ConcreteRole, Move]]] = (
            tuple((role, move) for move in legal_moves[role]) for role in roles_in_control
        )
