from typing import FrozenSet, Mapping

import pytest

from pyggp.engine_primitives import Move, Play, Role, Turn
from pyggp.game_description_language import Number, Relation, Subrelation


@pytest.mark.parametrize(
    ("mapping", "expected"),
    [
        ({}, Turn()),
        (
            {Role(Subrelation(Relation("x"))): Move(Subrelation(Relation("move")))},
            Turn({(Role(Subrelation(Relation("x"))), Move(Subrelation(Relation("move"))))}),
        ),
        (
            {
                Role(Subrelation(Relation("x"))): Move(Subrelation(Number(1))),
                Role(Subrelation(Relation("y"))): Move(Subrelation(Number(2))),
            },
            Turn(
                {
                    (Role(Subrelation(Relation("x"))), Move(Subrelation(Number(1)))),
                    (Role(Subrelation(Relation("y"))), Move(Subrelation(Number(2)))),
                },
            ),
        ),
    ],
)
def test_dunder_init(mapping: Mapping[Role, Move], expected: Turn) -> None:
    actual = Turn(mapping)
    assert actual == expected


@pytest.mark.parametrize(
    ("turn", "role", "expected"),
    [
        (
            Turn({(Role(Subrelation(Relation("x"))), Move(Subrelation(Relation("move"))))}),
            Role(Subrelation(Relation("x"))),
            Move(Subrelation(Relation("move"))),
        ),
    ],
)
def test_dunder_get_item(turn: Turn, role: Role, expected: Move) -> None:
    actual = turn[role]
    assert actual == expected


@pytest.mark.parametrize(
    ("turn", "role"),
    [
        (Turn(), Role(Subrelation(Relation("x")))),
    ],
)
def test_dunder_get_item_raises_key_error(turn: Turn, role: Role) -> None:
    with pytest.raises(KeyError):
        # Disables PyCharm warning about unused variable. Because testing side effect.
        # noinspection PyStatementEffect
        turn[role]


@pytest.mark.parametrize(
    ("turn", "expected"),
    [
        (Turn(), 0),
        (Turn({(Role(Subrelation(Relation("x"))), Move(Subrelation(Relation("move"))))}), 1),
    ],
)
def test_dunder_len(turn: Turn, expected: int) -> None:
    actual = len(turn)
    assert actual == expected


@pytest.mark.parametrize(
    ("turn", "expected"),
    [
        (Turn(), ()),
        (
            Turn({(Role(Subrelation(Relation("x"))), Move(Subrelation(Relation("move"))))}),
            ((Role(Subrelation(Relation("x")))),),
        ),
    ],
)
def test_dunder_iter(turn: Turn, expected: tuple) -> None:
    actual = tuple(turn)
    assert actual == expected


@pytest.mark.parametrize(
    ("turn", "expected"),
    [
        (Turn(), frozenset()),
        (
            Turn(frozenset({(Role(Subrelation(Relation("x"))), Move(Subrelation(Relation("move"))))})),
            frozenset(
                {
                    Play(
                        Relation(
                            "does",
                            arguments=(Role(Subrelation(Relation("x"))), Move(Subrelation(Relation("move")))),
                        ),
                    ),
                },
            ),
        ),
    ],
)
def test_as_plays(turn: Turn, expected: FrozenSet[Play]) -> None:
    actual = frozenset(turn.as_plays())
    assert actual == expected
