from typing import Sequence

import pytest
from pyggp.game_description_language.literals import Literal
from pyggp.game_description_language.rulesets import get_related_rules
from pyggp.game_description_language.sentences import Sentence
from pyggp.game_description_language.subrelations import Number, Relation, Subrelation


@pytest.mark.parametrize(
    ("rules", "name", "arity", "expected"),
    [
        ((), "role", 1, ()),
        ((Sentence(head=Relation("pos")),), "target", 1, ()),
        (
            (
                Sentence(
                    head=Relation("pos", arguments=(Subrelation(Number(1)),)),
                    body=(
                        Literal(Relation("pos", arguments=(Subrelation(Number(2)),))),
                        Literal(Relation("pos", arguments=(Subrelation(Number(2)),))),
                    ),
                ),
                Sentence(
                    head=Relation("pos", arguments=(Subrelation(Number(2)),)),
                    body=(),
                ),
                Sentence(
                    head=Relation("target"),
                    body=(Literal(Relation("pos", arguments=(Subrelation(Number(1)),))),),
                ),
            ),
            "target",
            0,
            (
                Sentence(
                    head=Relation("pos", arguments=(Subrelation(Number(1)),)),
                    body=(
                        Literal(Relation("pos", arguments=(Subrelation(Number(2)),))),
                        Literal(Relation("pos", arguments=(Subrelation(Number(2)),))),
                    ),
                ),
                Sentence(
                    head=Relation("pos", arguments=(Subrelation(Number(2)),)),
                    body=(),
                ),
                Sentence(
                    head=Relation("target"),
                    body=(Literal(Relation("pos", arguments=(Subrelation(Number(1)),))),),
                ),
            ),
        ),
    ],
)
def test_get_related_rules(rules: Sequence[Sentence], name: str, arity: int, expected: Sequence[Sentence]) -> None:
    actual = tuple(get_related_rules(rules, name, arity))
    assert actual == expected
