import pytest

import pyggp.game_description_language as gdl
import pyggp.interpreters.dark_split_corridor34.constants
import pyggp.interpreters.dark_split_corridor34.corridor as corridor
from pyggp.engine_primitives import Role, State
from pyggp.interpreters.dark_split_corridor34.coordinates2d import Coordinates2D

subrelation_coordinates = (
    (pyggp.interpreters.dark_split_corridor34.constants.a1, Coordinates2D(0, 0)),
    (pyggp.interpreters.dark_split_corridor34.constants.a2, Coordinates2D(0, 1)),
    (pyggp.interpreters.dark_split_corridor34.constants.a3, Coordinates2D(0, 2)),
    (pyggp.interpreters.dark_split_corridor34.constants.a4, Coordinates2D(0, 3)),
    (pyggp.interpreters.dark_split_corridor34.constants.b1, Coordinates2D(1, 0)),
    (pyggp.interpreters.dark_split_corridor34.constants.b2, Coordinates2D(1, 1)),
    (pyggp.interpreters.dark_split_corridor34.constants.b3, Coordinates2D(1, 2)),
    (pyggp.interpreters.dark_split_corridor34.constants.b4, Coordinates2D(1, 3)),
    (pyggp.interpreters.dark_split_corridor34.constants.c1, Coordinates2D(2, 0)),
    (pyggp.interpreters.dark_split_corridor34.constants.c2, Coordinates2D(2, 1)),
    (pyggp.interpreters.dark_split_corridor34.constants.c3, Coordinates2D(2, 2)),
    (pyggp.interpreters.dark_split_corridor34.constants.c4, Coordinates2D(2, 3)),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.a1,
                    pyggp.interpreters.dark_split_corridor34.constants.a2,
                ),
            )
        ),
        Coordinates2D(0, 0.5),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.a2,
                    pyggp.interpreters.dark_split_corridor34.constants.a3,
                ),
            )
        ),
        Coordinates2D(0, 1.5),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.a3,
                    pyggp.interpreters.dark_split_corridor34.constants.a4,
                ),
            )
        ),
        Coordinates2D(0, 2.5),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.b1,
                    pyggp.interpreters.dark_split_corridor34.constants.b2,
                ),
            )
        ),
        Coordinates2D(1, 0.5),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.b2,
                    pyggp.interpreters.dark_split_corridor34.constants.b3,
                ),
            )
        ),
        Coordinates2D(1, 1.5),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.b3,
                    pyggp.interpreters.dark_split_corridor34.constants.b4,
                ),
            )
        ),
        Coordinates2D(1, 2.5),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.c1,
                    pyggp.interpreters.dark_split_corridor34.constants.c2,
                ),
            )
        ),
        Coordinates2D(2, 0.5),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.c2,
                    pyggp.interpreters.dark_split_corridor34.constants.c3,
                ),
            )
        ),
        Coordinates2D(2, 1.5),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.c3,
                    pyggp.interpreters.dark_split_corridor34.constants.c4,
                ),
            )
        ),
        Coordinates2D(2, 2.5),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.a1,
                    pyggp.interpreters.dark_split_corridor34.constants.b1,
                ),
            )
        ),
        Coordinates2D(0.5, 0),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.b1,
                    pyggp.interpreters.dark_split_corridor34.constants.c1,
                ),
            )
        ),
        Coordinates2D(1.5, 0),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.a2,
                    pyggp.interpreters.dark_split_corridor34.constants.b2,
                ),
            )
        ),
        Coordinates2D(0.5, 1),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.b2,
                    pyggp.interpreters.dark_split_corridor34.constants.c2,
                ),
            )
        ),
        Coordinates2D(1.5, 1),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.a3,
                    pyggp.interpreters.dark_split_corridor34.constants.b3,
                ),
            )
        ),
        Coordinates2D(0.5, 2),
    ),
    (
        gdl.Subrelation(
            gdl.Relation(
                None,
                (
                    pyggp.interpreters.dark_split_corridor34.constants.b3,
                    pyggp.interpreters.dark_split_corridor34.constants.c3,
                ),
            )
        ),
        Coordinates2D(1.5, 2),
    ),
)


@pytest.mark.parametrize(("subrelation", "expected"), subrelation_coordinates)
def test_from_subrelation(subrelation: gdl.Subrelation, expected: Coordinates2D):
    actual = Coordinates2D.from_subrelation(subrelation)
    assert actual == expected


@pytest.mark.parametrize(("expected", "coordinates"), subrelation_coordinates)
def test_into_subrelation(expected: gdl.Subrelation, coordinates: Coordinates2D):
    actual = coordinates.into_subrelation()
    assert actual == expected
