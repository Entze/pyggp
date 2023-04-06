import pytest
from pyggp.game_description_language.subrelations import Number, Relation, String, Subrelation


@pytest.mark.parametrize(
    ("subrelation", "expected"),
    [
        (Subrelation(Relation("a")), "a"),
        (Subrelation(Number(1)), "1"),
        (Subrelation(String("")), '""'),
        (Subrelation(Relation.from_symbols("a", Relation("b"))), "a(b)"),
    ],
)
def test_dunder_str(subrelation: Subrelation, expected: str) -> None:
    actual = str(subrelation)
    assert actual == expected


@pytest.mark.parametrize(
    ("subrelation1", "subrelation2", "expected"),
    [
        (Subrelation(Relation("a")), Subrelation(Relation("a")), False),
        (Subrelation(Relation("a")), Subrelation(Relation("b")), True),
        (Subrelation(Relation("a")), Subrelation(Relation("a", arguments=(Subrelation(Number(1)),))), True),
        (Subrelation(Relation("a", arguments=(Subrelation(Number(1)),))), Subrelation(Relation("a")), False),
        (Subrelation(String("a")), Subrelation(Relation("b")), False),
        (Subrelation(Relation("a")), Subrelation(String("a")), True),
    ],
)
def test_dunder_lt(subrelation1: Subrelation, subrelation2: Subrelation, expected: bool) -> None:
    actual = subrelation1 < subrelation2
    assert actual == expected


@pytest.mark.parametrize(
    ("subrelation1", "subrelation2", "expected"),
    [
        (Subrelation(Relation("a")), Subrelation(Relation("a")), False),
        (Subrelation(Relation("a")), Subrelation(Relation("b")), False),
        (Subrelation(Relation("a")), Subrelation(Relation("a", arguments=(Subrelation(Number(1)),))), False),
        (Subrelation(Relation("a", arguments=(Subrelation(Number(1)),))), Subrelation(Relation("a")), True),
        (Subrelation(String("a")), Subrelation(Relation("b")), True),
        (Subrelation(Relation("a")), Subrelation(String("a")), False),
    ],
)
def test_dunder_gt(subrelation1: Subrelation, subrelation2: Subrelation, expected: bool) -> None:
    actual = subrelation1 > subrelation2
    assert actual == expected
