import pytest

import pyggp.game_description_language as gdl
import pyggp.interpreters.dark_split_corridor34.corridor as corridor
from pyggp.engine_primitives import Role, State
from pyggp.interpreters.dark_split_corridor34.corridor import Coordinates2D

subrelation_coordinates = (
    (corridor.a1, Coordinates2D(0, 0)),
    (corridor.a2, Coordinates2D(0, 1)),
    (corridor.a3, Coordinates2D(0, 2)),
    (corridor.a4, Coordinates2D(0, 3)),
    (corridor.b1, Coordinates2D(1, 0)),
    (corridor.b2, Coordinates2D(1, 1)),
    (corridor.b3, Coordinates2D(1, 2)),
    (corridor.b4, Coordinates2D(1, 3)),
    (corridor.c1, Coordinates2D(2, 0)),
    (corridor.c2, Coordinates2D(2, 1)),
    (corridor.c3, Coordinates2D(2, 2)),
    (corridor.c4, Coordinates2D(2, 3)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.a1, corridor.a2))), Coordinates2D(0, 0.5)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.a2, corridor.a3))), Coordinates2D(0, 1.5)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.a3, corridor.a4))), Coordinates2D(0, 2.5)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.b1, corridor.b2))), Coordinates2D(1, 0.5)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.b2, corridor.b3))), Coordinates2D(1, 1.5)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.b3, corridor.b4))), Coordinates2D(1, 2.5)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.c1, corridor.c2))), Coordinates2D(2, 0.5)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.c2, corridor.c3))), Coordinates2D(2, 1.5)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.c3, corridor.c4))), Coordinates2D(2, 2.5)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.a1, corridor.b1))), Coordinates2D(0.5, 0)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.b1, corridor.c1))), Coordinates2D(1.5, 0)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.a2, corridor.b2))), Coordinates2D(0.5, 1)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.b2, corridor.c2))), Coordinates2D(1.5, 1)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.a3, corridor.b3))), Coordinates2D(0.5, 2)),
    (gdl.Subrelation(gdl.Relation(None, (corridor.b3, corridor.c3))), Coordinates2D(1.5, 2)),
)


@pytest.mark.parametrize(("subrelation", "expected"), subrelation_coordinates)
def test_from_subrelation(subrelation: gdl.Subrelation, expected: Coordinates2D):
    actual = Coordinates2D.from_subrelation(subrelation)
    assert actual == expected


@pytest.mark.parametrize(("expected", "coordinates"), subrelation_coordinates)
def test_into_subrelation(expected: gdl.Subrelation, coordinates: Coordinates2D):
    actual = coordinates.into_subrelation()
    assert actual == expected
