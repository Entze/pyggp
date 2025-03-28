import copy
from dataclasses import dataclass
from typing import FrozenSet, Iterator, Mapping, NamedTuple, Self, Sequence, Tuple

import pyggp.engine_primitives as pyggp
from pyggp.interpreters.dark_split_corridor34 import constants, corridor
from pyggp.interpreters.dark_split_corridor34.actions import Action, BlockAction, MoveAction
from pyggp.interpreters.dark_split_corridor34.constants import control_left, control_right, left, right


@dataclass(frozen=False)
class State:
    left: corridor.Corridor
    right: corridor.Corridor
    in_control: pyggp.Role

    @classmethod
    def from_pyggp_state(cls, state: pyggp.State) -> Self:
        left_ = corridor.Corridor.from_state(state, constants.left)
        right_ = corridor.Corridor.from_state(state, constants.right)
        for subrelation in state:
            if not subrelation.matches_signature("control", 1):
                continue
            in_control = pyggp.Role(subrelation.symbol.arguments[0])
            return cls(left_, right_, in_control)
        raise ValueError("State does not have a subrelation control/1.")

    def into_pyggp_state(self) -> pyggp.State:
        in_control = control_left if self.in_control == left else control_right
        return pyggp.State(
            frozenset((in_control, *self.left.into_subrelations(left), *self.right.into_subrelations(right)))
        )

    def into_pyggp_view(self) -> Mapping[pyggp.Role, pyggp.View]:
        in_control = control_left if self.in_control == left else control_right
        left_view = pyggp.View(
            pyggp.State(
                frozenset(
                    (
                        in_control,
                        *self.left.into_view_subrelations(left, left),
                        *self.right.into_view_subrelations(right, left),
                    )
                )
            )
        )
        right_view = pyggp.View(
            pyggp.State(
                frozenset(
                    (
                        in_control,
                        *self.left.into_view_subrelations(left, right),
                        *self.right.into_view_subrelations(right, right),
                    )
                )
            )
        )
        return {left: left_view, right: right_view}

    def apply(self, turn: Mapping[pyggp.Role, pyggp.Move]):
        role: pyggp.Role
        move: pyggp.Move
        for role, move in turn.items():
            action: Action
            other_role: pyggp.Role = constants.left if role == right else constants.right
            is_move_action = True
            if move.matches_signature("move", 1):
                action = MoveAction.from_move(move)
            else:
                assert move.matches_signature("block", 1)
                action = BlockAction.from_move(move)
                is_move_action = False
            if role == constants.left and is_move_action or role == constants.right and not is_move_action:
                self.left.apply_action(action)
            else:
                assert role == constants.right and is_move_action or role == constants.left and not is_move_action
                self.right.apply_action(action)
            self.in_control = other_role

    def moves(self, role: pyggp.Role) -> FrozenSet[pyggp.Move]:
        actions: Sequence[Action]
        if role == self.in_control:
            actions = tuple(
                (
                    *self.left.actions(constants.left, self.in_control, role),
                    *self.right.actions(constants.right, self.in_control, role),
                )
            )
        else:
            actions = tuple(
                (
                    *self.left.actions(constants.left, self.in_control, role),
                    *self.right.actions(constants.right, self.in_control, role),
                )
            )
        return frozenset(action.into_subrelation() for action in actions)

    def enumerate_all_next_states(self) -> Iterator[Tuple[Action, Self]]:
        own_corridor = self.left
        other_corridor = self.right
        own_role = self.in_control
        other_role = constants.right
        if self.in_control == constants.right:
            own_corridor = self.right
            other_corridor = self.left
            other_role = constants.left

        move_action: MoveAction
        for move_action in own_corridor.move_actions():
            next_own_corridor = own_corridor.transform_with_move_action(move_action)
            left_corridor, right_corridor = self._get_perspective_corridors(next_own_corridor, other_corridor, own_role)
            next_state = State(left=left_corridor, right=right_corridor, in_control=other_role)
            yield move_action, next_state

        for block_action in other_corridor.block_actions():
            next_other_corridor = other_corridor.transform_with_block_action(block_action)
            left_corridor, right_corridor = self._get_perspective_corridors(own_corridor, next_other_corridor, own_role)
            next_state = State(left=left_corridor, right=right_corridor, in_control=other_role)
            yield block_action, next_state

    @staticmethod
    def _get_perspective_corridors(next_own_corridor, other_corridor, own_role):
        if own_role == constants.left:
            left_corridor = next_own_corridor
            right_corridor = other_corridor
        else:
            assert own_role == constants.right
            left_corridor = other_corridor
            right_corridor = next_own_corridor
        return left_corridor, right_corridor

    def get_all_next_states(self) -> Iterator[Tuple[pyggp.Turn, pyggp.State]]:
        yield from (
            (pyggp.Turn(((self.in_control, action.into_subrelation()),)), state.into_pyggp_state())
            for action, state in self.enumerate_all_next_states()
        )
