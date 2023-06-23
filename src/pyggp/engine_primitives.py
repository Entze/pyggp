from typing import Final, FrozenSet, Iterator, Literal, NamedTuple, NewType, Optional, Sequence, Tuple, Union

import clingo.ast as clingo_ast

import pyggp._clingo as clingo_helper
from pyggp import game_description_language as gdl
from pyggp.mappings import FrozenDict

_State = FrozenSet[gdl.Subrelation]
State = NewType("State", _State)
"""States are sets of subrelations."""

View = NewType("View", State)
"""Views are (partial) states."""

Role = NewType("Role", gdl.Subrelation)
"""Roles are relations, numbers, or string."""

Play = NewType("Play", gdl.Relation)
"""Plays are does/2 relations.

Plays are of the form does(Subrelation(Role), Subrelation(Move)).

"""

Move = NewType("Move", gdl.Subrelation)
"""Moves are relations, numbers, or strings."""

RANDOM: Final[Role] = Role(gdl.Subrelation(gdl.Relation("random")))


class Turn(FrozenDict[Role, Move]):
    """Mapping of roles to a move.

    Resembles a collection of plays.

    """

    def as_plays(self) -> Iterator[Play]:
        """Return the plays of the turn.

        Returns:
            Plays of the turn

        """
        return (Play(gdl.Relation("does", arguments=(role, move))) for role, move in self._pairs)

    def get_assertions(self, current_time: clingo_ast.AST) -> Iterator[clingo_ast.AST]:
        for role, move in self.items():
            role_ast = role.as_clingo_ast()
            move_ast = move.as_clingo_ast()
            yield clingo_helper.create_rule(
                body=(
                    clingo_helper.create_literal(
                        sign=clingo_ast.Sign.Negation,
                        atom=clingo_helper.create_atom(
                            clingo_helper.create_function(
                                name="does_at",
                                arguments=(role_ast, move_ast, current_time),
                            ),
                        ),
                    ),
                ),
            )


class DevelopmentStep(NamedTuple):
    """Describes a possible state and a turn that leads to the next state."""

    state: State
    """State of that step."""
    turn: Optional[Turn]
    """Turn of that step, None if ambiguous."""


_Development = Sequence[DevelopmentStep]
Development = NewType("Development", _Development)
"""A sequence of development steps."""

ParallelMode = Union[int, Tuple[int, Literal["compete", "split"]]]

StateShape = FrozenSet[gdl.Subrelation]
ActionShape = FrozenDict[Role, FrozenSet[Move]]
SeesShape = FrozenDict[Role, FrozenSet[gdl.Subrelation]]
GoalShape = FrozenDict[Role, FrozenSet[int]]


def in_state_shape(state_shape: StateShape, subrelation: gdl.Subrelation) -> bool:
    if subrelation in state_shape:
        return True
    return subrelation.matches_signature(name="true", arity=1) and subrelation.symbol.arguments[0] in state_shape


def invert_state(state_shape: StateShape, current: Union[State, View]) -> State:
    inverted = state_shape - current
    return State(inverted)


def in_action_shape(action_shape: ActionShape, __play_or_role: Union[Play, Role], move: Optional[Move] = None) -> bool:
    role = None
    if __play_or_role in action_shape:
        role = __play_or_role
    elif __play_or_role.matches_signature(name="does", arity=2):
        role = __play_or_role.symbol.arguments[0]
        move = __play_or_role.symbol.arguments[1]
    return role in action_shape and move in action_shape[role]


def invert_does(action_shape: ActionShape, role: Role, move: Move) -> FrozenSet[Move]:
    return frozenset(m for m in action_shape[role] if m != move)


def in_sees_shape(
    sees_shape: ActionShape, __sees_or_role: Union[gdl.Subrelation, Role], subrelation: Optional[gdl.Subrelation] = None
) -> bool:
    role = None
    if __sees_or_role in sees_shape:
        role = __sees_or_role
    elif __sees_or_role.matches_signature(name="sees", arity=2):
        role = __sees_or_role.symbol.arguments[0]
        subrelation = __sees_or_role.symbol.arguments[1]
    return role in sees_shape and subrelation in sees_shape[role]


def invert_sees(sees_shape: SeesShape, role: Role, view: View) -> View:
    inverted = sees_shape[role] - view
    return View(inverted)


def in_goal_shape(
    goal_shape: GoalShape, __goal_or_role: Union[gdl.Subrelation, Role], value: Optional[int] = None
) -> bool:
    role = None
    if __goal_or_role in goal_shape:
        role = __goal_or_role
    elif __goal_or_role.matches_signature(name="goal", arity=2):
        role = __goal_or_role.symbol.arguments[0]
        value = __goal_or_role.symbol.arguments[1]
    return role in goal_shape and value in goal_shape[role]
