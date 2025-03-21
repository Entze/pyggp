from typing import FrozenSet, Mapping, NamedTuple, Self, Sequence

import pyggp.engine_primitives as pyggp
from pyggp.interpreters.dark_split_corridor34 import constants, corridor
from pyggp.interpreters.dark_split_corridor34.actions import Action, BlockAction, MoveAction
from pyggp.interpreters.dark_split_corridor34.constants import control_left, control_right, left, right


class State(NamedTuple):
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
        in_control = control_left if self.in_control == right else control_right
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

    def moves(self, role: pyggp.Role) -> FrozenSet[pyggp.Move]:
        moves: Sequence[Action]
        if role == self.in_control:
            moves = tuple(
                (
                    *self.left.actions(constants.left, self.in_control, role),
                    *self.right.actions(constants.right, self.in_control, role),
                )
            )
        else:
            moves = tuple(
                (
                    *self.left.actions(constants.left, self.in_control, role),
                    *self.right.actions(constants.right, self.in_control, role),
                )
            )
        return frozenset(move.into_subrelation() for move in moves)
