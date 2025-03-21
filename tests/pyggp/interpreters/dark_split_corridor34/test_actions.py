import pytest

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Move
from pyggp.interpreters.dark_split_corridor34.actions import Action, BlockAction, MoveAction
from pyggp.interpreters.dark_split_corridor34.constants import a1, a2, a3, a4, b1, b2, b3, b4, c1, c2, c3, c4
from pyggp.interpreters.dark_split_corridor34.coordinates2d import Coordinates2D


@pytest.mark.parametrize(
    ("subrelation", "expected"),
    (
        (Move(gdl.Subrelation(gdl.Relation("move", (gdl.Subrelation(gdl.Relation("north")),)))), MoveAction.NORTH),
        (Move(gdl.Subrelation(gdl.Relation("move", (gdl.Subrelation(gdl.Relation("east")),)))), MoveAction.EAST),
        (Move(gdl.Subrelation(gdl.Relation("move", (gdl.Subrelation(gdl.Relation("south")),)))), MoveAction.SOUTH),
        (Move(gdl.Subrelation(gdl.Relation("move", (gdl.Subrelation(gdl.Relation("west")),)))), MoveAction.WEST),
    ),
)
def test_from_move(subrelation: Move, expected: MoveAction):
    actual = MoveAction.from_move(subrelation)
    assert actual == expected


@pytest.mark.parametrize(
    ("subrelation", "expected"),
    (
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (a1, a2))),)))),
            BlockAction(Coordinates2D(0, 0.5)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (a2, a3))),)))),
            BlockAction(Coordinates2D(0, 1.5)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (a3, a4))),)))),
            BlockAction(Coordinates2D(0, 2.5)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (b1, b2))),)))),
            BlockAction(Coordinates2D(1, 0.5)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (b2, b3))),)))),
            BlockAction(Coordinates2D(1, 1.5)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (b3, b4))),)))),
            BlockAction(Coordinates2D(1, 2.5)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (c1, c2))),)))),
            BlockAction(Coordinates2D(2, 0.5)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (c2, c3))),)))),
            BlockAction(Coordinates2D(2, 1.5)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (c3, c4))),)))),
            BlockAction(Coordinates2D(2, 2.5)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (a1, b1))),)))),
            BlockAction(Coordinates2D(0.5, 0)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (b1, c1))),)))),
            BlockAction(Coordinates2D(1.5, 0)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (a2, b2))),)))),
            BlockAction(Coordinates2D(0.5, 1)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (b2, c2))),)))),
            BlockAction(Coordinates2D(1.5, 1)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (a3, b3))),)))),
            BlockAction(Coordinates2D(0.5, 2)),
        ),
        (
            Move(gdl.Subrelation(gdl.Relation("block", (gdl.Subrelation(gdl.Relation(None, (b3, c3))),)))),
            BlockAction(Coordinates2D(1.5, 2)),
        ),
    ),
)
def test_from_move(subrelation: Move, expected: BlockAction):
    actual = BlockAction.from_move(subrelation)
    assert actual == expected
