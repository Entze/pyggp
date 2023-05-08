from typing import FrozenSet

import pytest
from pyggp.engine_primitives import Role, State, View
from pyggp.game_description_language import Relation, String, Subrelation
from pyggp.interpreters import Interpreter


@pytest.mark.parametrize(
    ("view", "expected"),
    [
        (View(State(frozenset())), frozenset()),
        (
            View(
                State(frozenset({Subrelation(Relation(name="control", arguments=(Subrelation(Relation(name="x")),)))})),
            ),
            frozenset({Role(Subrelation(Relation("x")))}),
        ),
        (
            View(
                State(
                    frozenset(
                        {
                            Subrelation(Relation(name="control", arguments=(Subrelation(Relation(name="x")),))),
                            Subrelation(Relation(name="control", arguments=(Subrelation(Relation(name="y")),))),
                            Subrelation(Relation(name="unrelated")),
                            Subrelation(String("unrelated")),
                        },
                    ),
                ),
            ),
            frozenset({Role(Subrelation(Relation("x"))), Role(Subrelation(Relation("y")))}),
        ),
    ],
)
def test_get_roles_in_control(view: View, expected: FrozenSet[Role]) -> None:
    actual = Interpreter.get_roles_in_control(view)
    assert actual == expected
