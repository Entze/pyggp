from idlelib.debugger_r import close_remote_debugger
from typing import Mapping, Set

import pytest

import pyggp.game_description_language as gdl
import pyggp.interpreters.dark_split_corridor34.corridor as corridor
from pyggp.engine_primitives import Role, State, View
from pyggp.interpreters.dark_split_corridor34 import constants
from pyggp.interpreters.dark_split_corridor34.actions import BlockAction, MoveAction
from pyggp.interpreters.dark_split_corridor34.coordinates2d import Coordinates2D

state1 = State(
    frozenset(
        (
            gdl.Subrelation(gdl.Relation("at", (constants.left, constants.b1))),
            gdl.Subrelation(gdl.Relation("at", (constants.right, constants.b1))),
            gdl.Subrelation(gdl.Relation("control", (constants.left,))),
        )
    )
)

state2 = State(
    frozenset(
        (
            gdl.Subrelation(gdl.Relation("at", (constants.left, constants.b1))),
            gdl.Subrelation(gdl.Relation("at", (constants.right, constants.b1))),
            gdl.Subrelation(
                gdl.Relation(
                    "border", (constants.right, gdl.Subrelation(gdl.Relation(None, (constants.b1, constants.b2))))
                )
            ),
            gdl.Subrelation(gdl.Relation("control", (constants.right,))),
        )
    )
)

state3 = State(
    frozenset(
        (
            gdl.Subrelation(gdl.Relation("at", (constants.left, constants.b1))),
            gdl.Subrelation(gdl.Relation("at", (constants.right, constants.b1))),
            gdl.Subrelation(
                gdl.Relation(
                    "border", (constants.right, gdl.Subrelation(gdl.Relation(None, (constants.b1, constants.b2))))
                )
            ),
            gdl.Subrelation(
                gdl.Relation(
                    "revealed",
                    (constants.right, gdl.Subrelation(gdl.Relation(None, (constants.b1, constants.b2)))),
                )
            ),
            gdl.Subrelation(gdl.Relation("control", (constants.left,))),
        )
    )
)
state4 = State(
    frozenset(
        (
            gdl.Subrelation(gdl.Relation("at", (constants.left, constants.b1))),
            gdl.Subrelation(gdl.Relation("at", (constants.right, constants.b1))),
            gdl.Subrelation(
                gdl.Relation(
                    "border", (constants.right, gdl.Subrelation(gdl.Relation(None, (constants.b1, constants.b2))))
                )
            ),
            gdl.Subrelation(
                gdl.Relation(
                    "revealed",
                    (constants.right, gdl.Subrelation(gdl.Relation(None, (constants.b1, constants.b2)))),
                )
            ),
            gdl.Subrelation(
                gdl.Relation(
                    "border", (constants.right, gdl.Subrelation(gdl.Relation(None, (constants.a1, constants.b1))))
                )
            ),
            gdl.Subrelation(gdl.Relation("control", (constants.right,))),
        )
    )
)
state_corridor_by_role = (
    (
        state1,
        {
            Role(constants.left): corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
            Role(constants.right): corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
        },
    ),
    (
        state2,
        {
            Role(constants.left): corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
            Role(constants.right): corridor.Corridor(
                pawn_position=Coordinates2D(1, 0),
                borders=corridor._default_borders() | {Coordinates2D(1, 0.5): corridor.Border.BLOCKED},
            ),
        },
    ),
    (
        state3,
        {
            Role(constants.left): corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
            Role(constants.right): corridor.Corridor(
                pawn_position=Coordinates2D(1, 0),
                borders=corridor._default_borders() | {Coordinates2D(1, 0.5): corridor.Border.REVEALED},
            ),
        },
    ),
    (
        state4,
        {
            Role(constants.left): corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
            Role(constants.right): corridor.Corridor(
                pawn_position=Coordinates2D(1, 0),
                borders=corridor._default_borders()
                | {Coordinates2D(0.5, 0): corridor.Border.BLOCKED, Coordinates2D(1, 0.5): corridor.Border.REVEALED},
            ),
        },
    ),
)

corridor_role_observer_view = (
    (
        corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
        constants.left,
        constants.left,
        {
            gdl.Subrelation(gdl.Relation("at", (constants.left, constants.b1))),
        },
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
        constants.left,
        constants.right,
        {
            gdl.Subrelation(gdl.Relation("at", (constants.left, constants.b1))),
        },
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
        constants.right,
        constants.left,
        {
            gdl.Subrelation(gdl.Relation("at", (constants.right, constants.b1))),
        },
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
        constants.right,
        constants.right,
        {
            gdl.Subrelation(gdl.Relation("at", (constants.right, constants.b1))),
        },
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(1, 0),
            borders=corridor._default_borders() | {Coordinates2D(0.5, 0): corridor.Border.BLOCKED},
        ),
        constants.left,
        constants.left,
        {
            gdl.Subrelation(gdl.Relation("at", (constants.left, constants.b1))),
        },
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(1, 0),
            borders=corridor._default_borders() | {Coordinates2D(0.5, 0): corridor.Border.BLOCKED},
        ),
        constants.left,
        constants.right,
        {
            gdl.Subrelation(gdl.Relation("at", (constants.left, constants.b1))),
            gdl.Subrelation(
                gdl.Relation(
                    "border", (constants.left, gdl.Subrelation(gdl.Relation(None, (constants.a1, constants.b1))))
                )
            ),
        },
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(1, 0),
            borders=corridor._default_borders() | {Coordinates2D(0.5, 0): corridor.Border.BLOCKED},
        ),
        constants.right,
        constants.left,
        {
            gdl.Subrelation(gdl.Relation("at", (constants.right, constants.b1))),
            gdl.Subrelation(
                gdl.Relation(
                    "border", (constants.right, gdl.Subrelation(gdl.Relation(None, (constants.a1, constants.b1))))
                )
            ),
        },
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(1, 0),
            borders=corridor._default_borders() | {Coordinates2D(0.5, 0): corridor.Border.BLOCKED},
        ),
        constants.right,
        constants.right,
        {
            gdl.Subrelation(gdl.Relation("at", (constants.right, constants.b1))),
        },
    ),
)

corridor_role_incontrol_mover_actions = (
    (
        corridor.Corridor(pawn_position=Coordinates2D(0, 0)),
        constants.left,
        constants.left,
        constants.left,
        {
            MoveAction.EAST,
            MoveAction.SOUTH,
        },
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
        constants.left,
        constants.left,
        constants.left,
        {MoveAction.EAST, MoveAction.SOUTH, MoveAction.WEST},
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(2, 0)),
        constants.left,
        constants.left,
        constants.left,
        {MoveAction.SOUTH, MoveAction.WEST},
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(1, 1)),
        constants.left,
        constants.left,
        constants.left,
        {MoveAction.NORTH, MoveAction.EAST, MoveAction.SOUTH, MoveAction.WEST},
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(0, 0)),
        constants.right,
        constants.right,
        constants.right,
        {
            MoveAction.EAST,
            MoveAction.SOUTH,
        },
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
        constants.right,
        constants.right,
        constants.right,
        {MoveAction.EAST, MoveAction.SOUTH, MoveAction.WEST},
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(2, 0)),
        constants.right,
        constants.right,
        constants.right,
        {MoveAction.SOUTH, MoveAction.WEST},
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(1, 1)),
        constants.right,
        constants.right,
        constants.right,
        {MoveAction.NORTH, MoveAction.EAST, MoveAction.SOUTH, MoveAction.WEST},
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(1, 1),
            borders=corridor._default_borders() | {Coordinates2D(1, 0.5): corridor.Border.REVEALED},
        ),
        constants.left,
        constants.left,
        constants.left,
        {MoveAction.EAST, MoveAction.SOUTH, MoveAction.WEST},
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(1, 1),
            borders=corridor._default_borders() | {Coordinates2D(1, 1.5): corridor.Border.REVEALED},
        ),
        constants.left,
        constants.left,
        constants.left,
        {MoveAction.EAST, MoveAction.NORTH, MoveAction.WEST},
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(1, 1),
            borders=corridor._default_borders() | {Coordinates2D(0.5, 1): corridor.Border.REVEALED},
        ),
        constants.left,
        constants.left,
        constants.left,
        {MoveAction.EAST, MoveAction.NORTH, MoveAction.SOUTH},
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(1, 1),
            borders=corridor._default_borders() | {Coordinates2D(1.5, 1): corridor.Border.REVEALED},
        ),
        constants.left,
        constants.left,
        constants.left,
        {MoveAction.WEST, MoveAction.NORTH, MoveAction.SOUTH},
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(1, 1),
            borders=corridor._default_borders()
            | {Coordinates2D(1.5, 1): corridor.Border.REVEALED, Coordinates2D(1, 0.5): corridor.Border.REVEALED},
        ),
        constants.left,
        constants.left,
        constants.left,
        {MoveAction.WEST, MoveAction.SOUTH},
    ),
    (
        corridor.Corridor(pawn_position=Coordinates2D(1, 1), borders=corridor._default_borders()),
        constants.left,
        constants.right,
        constants.right,
        {BlockAction(crossing) for crossing in corridor._default_borders().keys() if crossing.y < 3},
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(1, 2),
            borders=corridor._default_borders()
            | {
                Coordinates2D(1, 1.5): corridor.Border.REVEALED,
                Coordinates2D(0.5, 2): corridor.Border.REVEALED,
                Coordinates2D(1.5, 2): corridor.Border.REVEALED,
            },
        ),
        constants.left,
        constants.right,
        constants.right,
        {
            BlockAction(Coordinates2D(0.5, 0)),
            BlockAction(Coordinates2D(1.5, 0)),
            BlockAction(Coordinates2D(0, 0.5)),
            BlockAction(Coordinates2D(1, 0.5)),
            BlockAction(Coordinates2D(2, 0.5)),
            BlockAction(Coordinates2D(0.5, 1)),
            BlockAction(Coordinates2D(1.5, 1)),
            BlockAction(Coordinates2D(0, 1.5)),
            BlockAction(Coordinates2D(2, 1.5)),
            BlockAction(Coordinates2D(0, 2.5)),
            BlockAction(Coordinates2D(2, 2.5)),
        },
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(2, 2),
            borders=corridor._default_borders()
            | {
                Coordinates2D(2, 2.5): corridor.Border.BLOCKED,
                Coordinates2D(1.5, 2): corridor.Border.BLOCKED,
                Coordinates2D(1, 1.5): corridor.Border.REVEALED,
                Coordinates2D(0.5, 1): corridor.Border.BLOCKED,
                Coordinates2D(1, 0.5): corridor.Border.REVEALED,
            },
        ),
        constants.right,
        constants.left,
        constants.left,
        {
            BlockAction(Coordinates2D(0.5, 2)),
            BlockAction(Coordinates2D(1, 2.5)),
            BlockAction(Coordinates2D(0, 2.5)),
            BlockAction(Coordinates2D(1.5, 1)),
        },
    ),
    (
        corridor.Corridor(
            pawn_position=Coordinates2D(2, 2),
            borders=corridor._default_borders()
            | {
                Coordinates2D(2, 2.5): corridor.Border.BLOCKED,
                Coordinates2D(1.5, 2): corridor.Border.BLOCKED,
                Coordinates2D(1, 1.5): corridor.Border.REVEALED,
                Coordinates2D(0.5, 1): corridor.Border.BLOCKED,
                Coordinates2D(1, 0.5): corridor.Border.REVEALED,
            },
        ),
        constants.right,
        constants.right,
        constants.left,
        set(),
    ),
)


@pytest.mark.parametrize(("state", "expected_by_role"), state_corridor_by_role)
def test_from_state(state: State, expected_by_role: Mapping[Role, corridor.Corridor]):
    actual_left = corridor.Corridor.from_state(state, Role(constants.left))
    assert actual_left == expected_by_role[Role(constants.left)]
    actual_right = corridor.Corridor.from_state(state, Role(constants.right))
    assert actual_right == expected_by_role[Role(constants.right)]


@pytest.mark.parametrize(("expected", "corridors_by_role"), state_corridor_by_role)
def test_into_subrelations(expected: State, corridors_by_role: Mapping[Role, corridor.Corridor]):
    left = corridors_by_role[Role(constants.left)]
    right = corridors_by_role[Role(constants.right)]
    in_control: gdl.Subrelation = next(
        subrelation for subrelation in expected if subrelation.matches_signature(name="control", arity=1)
    )
    actual = State(
        frozenset((*left.into_subrelations(constants.left), *right.into_subrelations(constants.right), in_control))
    )
    assert actual == expected


@pytest.mark.parametrize(
    ("actual", "move_action", "expected"),
    (
        (
            corridor.Corridor(pawn_position=Coordinates2D(1, 0), borders=corridor._default_borders()),
            MoveAction.SOUTH,
            corridor.Corridor(pawn_position=Coordinates2D(1, 1), borders=corridor._default_borders()),
        ),
        (
            corridor.Corridor(pawn_position=Coordinates2D(1, 0), borders=corridor._default_borders()),
            MoveAction.EAST,
            corridor.Corridor(pawn_position=Coordinates2D(2, 0), borders=corridor._default_borders()),
        ),
        (
            corridor.Corridor(pawn_position=Coordinates2D(1, 0), borders=corridor._default_borders()),
            MoveAction.WEST,
            corridor.Corridor(pawn_position=Coordinates2D(0, 0), borders=corridor._default_borders()),
        ),
        (
            corridor.Corridor(pawn_position=Coordinates2D(1, 1), borders=corridor._default_borders()),
            MoveAction.NORTH,
            corridor.Corridor(pawn_position=Coordinates2D(1, 0), borders=corridor._default_borders()),
        ),
        (
            corridor.Corridor(
                pawn_position=Coordinates2D(1, 0),
                borders=corridor._default_borders() | {Coordinates2D(1, 0.5): corridor.Border.BLOCKED},
            ),
            MoveAction.SOUTH,
            corridor.Corridor(
                pawn_position=Coordinates2D(1, 0),
                borders=corridor._default_borders() | {Coordinates2D(1, 0.5): corridor.Border.REVEALED},
            ),
        ),
    ),
)
def test_apply_move_action(actual: corridor.Corridor, move_action: MoveAction, expected: corridor.Corridor):
    actual.apply_action(move_action)
    assert actual == expected


@pytest.mark.parametrize(
    ("actual", "block_action", "expected"),
    (
        (
            corridor.Corridor(pawn_position=Coordinates2D(1, 0), borders=corridor._default_borders()),
            BlockAction(Coordinates2D(1, 0.5)),
            corridor.Corridor(
                pawn_position=Coordinates2D(1, 0),
                borders=corridor._default_borders() | {Coordinates2D(1, 0.5): corridor.Border.BLOCKED},
            ),
        ),
        (
            corridor.Corridor(pawn_position=Coordinates2D(1, 0), borders=corridor._default_borders()),
            BlockAction(Coordinates2D(1.5, 2)),
            corridor.Corridor(
                pawn_position=Coordinates2D(1, 0),
                borders=corridor._default_borders() | {Coordinates2D(1.5, 2): corridor.Border.BLOCKED},
            ),
        ),
    ),
)
def test_apply_block_action(actual: corridor.Corridor, block_action: BlockAction, expected: corridor.Corridor):
    actual.apply_action(block_action)
    assert actual == expected


@pytest.mark.parametrize(("corridor_", "role", "observer", "expected"), corridor_role_observer_view)
def test_into_view_subrelations(
    corridor_: corridor.Corridor, role: Role, observer: Role, expected: Set[gdl.Subrelation]
):
    actual = set(corridor_.into_view_subrelations(role, observer))
    assert actual == expected


@pytest.mark.parametrize(
    ("corridor_", "role", "in_control", "mover", "expected"), corridor_role_incontrol_mover_actions
)
def test_actions(
    corridor_: corridor.Corridor, role: Role, in_control: Role, mover: Role, expected: Set[MoveAction | BlockAction]
):
    actual = set(corridor_.actions(role, in_control, mover))
    assert actual == expected
