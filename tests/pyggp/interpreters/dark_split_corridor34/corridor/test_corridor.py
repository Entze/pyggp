from typing import Mapping

import pytest

import pyggp.game_description_language as gdl
import pyggp.interpreters.dark_split_corridor34.corridor as corridor
from pyggp.engine_primitives import Role, State
from pyggp.interpreters.dark_split_corridor34.corridor import Coordinates2D

state_corridor_by_role = (
    (
        State(
            frozenset(
                (
                    gdl.Subrelation(gdl.Relation("at", (corridor.left, corridor.b1))),
                    gdl.Subrelation(gdl.Relation("at", (corridor.right, corridor.b1))),
                    gdl.Subrelation(gdl.Relation("control", (corridor.left,))),
                )
            )
        ),
        {
            Role(corridor.left): corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
            Role(corridor.right): corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
        },
    ),
    (
        State(
            frozenset(
                (
                    gdl.Subrelation(gdl.Relation("at", (corridor.left, corridor.b1))),
                    gdl.Subrelation(gdl.Relation("at", (corridor.right, corridor.b1))),
                    gdl.Subrelation(
                        gdl.Relation(
                            "border", (corridor.right, gdl.Subrelation(gdl.Relation(None, (corridor.b1, corridor.b2))))
                        )
                    ),
                    gdl.Subrelation(gdl.Relation("control", (corridor.right,))),
                )
            )
        ),
        {
            Role(corridor.left): corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
            Role(corridor.right): corridor.Corridor(
                pawn_position=Coordinates2D(1, 0),
                borders=corridor._default_borders() | {Coordinates2D(1, 0.5): corridor.Border.BLOCKED},
            ),
        },
    ),
    (
        State(
            frozenset(
                (
                    gdl.Subrelation(gdl.Relation("at", (corridor.left, corridor.b1))),
                    gdl.Subrelation(gdl.Relation("at", (corridor.right, corridor.b1))),
                    gdl.Subrelation(
                        gdl.Relation(
                            "border", (corridor.right, gdl.Subrelation(gdl.Relation(None, (corridor.b1, corridor.b2))))
                        )
                    ),
                    gdl.Subrelation(
                        gdl.Relation(
                            "revealed",
                            (corridor.right, gdl.Subrelation(gdl.Relation(None, (corridor.b1, corridor.b2)))),
                        )
                    ),
                    gdl.Subrelation(gdl.Relation("control", (corridor.left,))),
                )
            )
        ),
        {
            Role(corridor.left): corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
            Role(corridor.right): corridor.Corridor(
                pawn_position=Coordinates2D(1, 0),
                borders=corridor._default_borders() | {Coordinates2D(1, 0.5): corridor.Border.REVEALED},
            ),
        },
    ),
    (
        State(
            frozenset(
                (
                    gdl.Subrelation(gdl.Relation("at", (corridor.left, corridor.b1))),
                    gdl.Subrelation(gdl.Relation("at", (corridor.right, corridor.b1))),
                    gdl.Subrelation(
                        gdl.Relation(
                            "border", (corridor.right, gdl.Subrelation(gdl.Relation(None, (corridor.b1, corridor.b2))))
                        )
                    ),
                    gdl.Subrelation(
                        gdl.Relation(
                            "revealed",
                            (corridor.right, gdl.Subrelation(gdl.Relation(None, (corridor.b1, corridor.b2)))),
                        )
                    ),
                    gdl.Subrelation(
                        gdl.Relation(
                            "border", (corridor.right, gdl.Subrelation(gdl.Relation(None, (corridor.a1, corridor.b1))))
                        )
                    ),
                    gdl.Subrelation(gdl.Relation("control", (corridor.right,))),
                )
            )
        ),
        {
            Role(corridor.left): corridor.Corridor(pawn_position=Coordinates2D(1, 0)),
            Role(corridor.right): corridor.Corridor(
                pawn_position=Coordinates2D(1, 0),
                borders=corridor._default_borders()
                | {Coordinates2D(0.5, 0): corridor.Border.BLOCKED, Coordinates2D(1, 0.5): corridor.Border.REVEALED},
            ),
        },
    ),
)


@pytest.mark.parametrize(("state", "expected_by_role"), state_corridor_by_role)
def test_from_state(state: State, expected_by_role: Mapping[Role, corridor.Corridor]):
    actual_left = corridor.Corridor.from_state(state, Role(corridor.left))
    assert actual_left == expected_by_role[Role(corridor.left)]
    actual_right = corridor.Corridor.from_state(state, Role(corridor.right))
    assert actual_right == expected_by_role[Role(corridor.right)]


@pytest.mark.parametrize(("expected", "corridors_by_role"), state_corridor_by_role)
def test_into_subrelations(expected: State, corridors_by_role: Mapping[Role, corridor.Corridor]):
    left = corridors_by_role[Role(corridor.left)]
    right = corridors_by_role[Role(corridor.right)]
    in_control: gdl.Subrelation = next(
        subrelation for subrelation in expected if subrelation.matches_signature(name="control", arity=1)
    )
    actual = State(
        frozenset((*left.into_subrelations(corridor.left), *right.into_subrelations(corridor.right), in_control))
    )
    assert actual == expected
