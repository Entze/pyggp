import pytest

from pyggp.game_description_language.literals import Literal
from pyggp.game_description_language.rulesets import Ruleset
from pyggp.game_description_language.sentences import Sentence
from pyggp.game_description_language.subrelations import Number, Relation, Subrelation, Variable


@pytest.mark.parametrize(
    ("ruleset", "expected"),
    [
        (Ruleset(), ""),
        (Ruleset((Sentence(Relation(name="atom")),)), "atom."),
    ],
)
def test_infix_str(ruleset: Ruleset, expected: str) -> None:
    actual = ruleset.infix_str
    assert actual == expected


@pytest.mark.parametrize(
    ("ruleset", "expected"),
    [
        (Ruleset(), ""),
        (Ruleset((Sentence(Relation(name="atom")),)), "atom."),
    ],
)
def test_dunder_str(ruleset: Ruleset, expected: str) -> None:
    actual = str(ruleset)
    assert actual == expected


def test_from_rules_empty() -> None:
    rules = ()
    actual = Ruleset.from_rules(rules)
    expected = Ruleset()
    assert actual == expected


def test_from_rules() -> None:
    rules = (
        Sentence(
            head=Relation(name="role", arguments=(Subrelation(Relation(name="x")),)),
        ),  # 0
        Sentence(
            head=Relation(
                name="init",
                arguments=(
                    Subrelation(
                        Relation(
                            "control",
                            arguments=(Subrelation(Relation(name="x")),),
                        ),
                    ),
                ),
            ),
        ),  # 1
        Sentence(
            head=Relation(name="unrelated"),
            body=(
                Literal(Relation(name="unrelated_pos")),
                Literal(Relation(name="unrelated_neg"), sign=Literal.Sign.NEGATIVE),
            ),
        ),  # 2
        Sentence(
            head=Relation(name="related_to_next", arguments=(Subrelation(Number(1)),)),
            body=(
                Literal(Relation(name="related_to_next_pos", arguments=(Subrelation(Number(1)),))),
                Literal(
                    Relation(name="related_to_next_neg", arguments=(Subrelation(Number(1)),)),
                    sign=Literal.Sign.NEGATIVE,
                ),
            ),
        ),  # 3
        Sentence(
            head=Relation(name="related_to_legal_but_not_included", arguments=(Subrelation(Number(1)),)),
        ),  # 4
        Sentence(
            head=Relation(
                name="next",
                arguments=(
                    Subrelation(
                        Relation(
                            "control",
                            arguments=(Subrelation(Relation(name="x")),),
                        ),
                    ),
                ),
            ),
            body=(
                Literal(
                    Relation(
                        name="related_to_next",
                        arguments=(Subrelation(Variable("N")),),
                    ),
                ),
            ),
        ),  # 5
        Sentence(
            head=Relation(
                name="legal",
                arguments=(
                    Subrelation(Relation(name="x")),
                    Subrelation(
                        Relation(name="move"),
                    ),
                ),
            ),
            body=(
                Literal(
                    Relation(
                        name="related_to_legal_but_not_included",
                        arguments=(Subrelation(Number(2)),),
                    ),
                ),
            ),
        ),  # 6
    )
    actual = Ruleset.from_rules(rules)
    expected = Ruleset(
        rules=rules,
        role_rules=rules[0:1],
        init_rules=rules[1:2],
        next_rules=(rules[3], rules[5]),
        legal_rules=rules[6:7],
    )
    assert actual == expected, f"{actual} != {expected}"
