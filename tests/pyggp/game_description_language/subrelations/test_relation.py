from typing import Optional

import pytest
from pyggp.game_description_language.subrelations import Number, Relation, String, Subrelation, Variable


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        (Relation(), "()"),
        (Relation("a"), "a"),
        (Relation("a", (Subrelation(Relation("b")),)), "a(b)"),
        (Relation("a", (Subrelation(Relation("b")), Subrelation(Relation("c")))), "a(b,c)"),
        (Relation(arguments=(Subrelation(String("b")), Subrelation(Relation("b")))), '("b",b)'),
        (Relation("a1", (Subrelation(Number(1)),)), "a1(1)"),
    ],
)
def test_infix_str(relation: Relation, expected: str) -> None:
    actual = relation.infix_str
    assert actual == expected


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        (Relation(), "()"),
        (Relation("a"), "a"),
        (Relation("a", (Subrelation(Relation("b")),)), "a(b)"),
        (Relation("a", (Subrelation(Relation("b")), Subrelation(Relation("c")))), "a(b,c)"),
        (Relation(arguments=(Subrelation(String("b")), Subrelation(Relation("b")))), '("b",b)'),
        (Relation("a1", (Subrelation(Number(1)),)), "a1(1)"),
    ],
)
def test_dunder_str(relation: Relation, expected: str) -> None:
    actual = str(relation)
    assert actual == expected


@pytest.mark.parametrize(
    # Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
    ("relation",),  # noqa: PT006
    [
        (Relation(),),
        (Relation("a"),),
        (Relation("a", (Subrelation(Relation("b")),)),),
        (Relation("a", (Subrelation(Relation("b")), Subrelation(Relation("c")))),),
        (Relation(arguments=(Subrelation(String("b")), Subrelation(Relation("b")))),),
        (Relation("a1", (Subrelation(Number(1)),)),),
    ],
)
def test_dunder_rich(relation: Relation) -> None:
    actual = relation.__rich__()
    assert relation.name is None or relation.name in actual
    for argument in relation.arguments:
        assert argument.__rich__() in actual


@pytest.mark.parametrize(
    ("signature", "expected"),
    [(Relation.Signature("a", 3), "a/3"), (Relation.Signature("a", 0), "a/0"), (Relation.Signature(None, 3), "(3)")],
)
def test_signature_dunder_str(signature: Relation.Signature, expected: str) -> None:
    actual = str(signature)
    assert actual == expected


@pytest.mark.parametrize(
    # Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
    ("signature",),  # noqa: PT006
    [
        (Relation.Signature("a", 3),),
        (Relation.Signature("a", 0),),
        (Relation.Signature(None, 3),),
    ],
)
def test_signature_dunder_rich(signature: Relation.Signature) -> None:
    actual = signature.__rich__()
    if signature.name is not None:
        assert signature.name in actual
    assert str(signature.arity) in actual


@pytest.mark.parametrize(
    ("relation", "name", "arity", "expected"),
    [
        (Relation(), None, 0, True),
        (Relation("a"), "a", 0, True),
        (Relation("a", (Subrelation(Relation("b")),)), "a", 1, True),
        (Relation(), "a", 0, False),
        (Relation("a"), None, 0, False),
    ],
)
def test_matches_signature(relation: Relation, name: Optional[str], arity: int, expected: bool) -> None:
    actual = relation.matches_signature(name, arity)
    assert actual == expected


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        (Relation(), Relation.Signature(None, 0)),
        (Relation("a"), Relation.Signature("a", 0)),
        (Relation("a", (Subrelation(Relation("b")),)), Relation.Signature("a", 1)),
        (Relation("a", (Subrelation(Relation("b")), Subrelation(Relation("c")))), Relation.Signature("a", 2)),
        (Relation(arguments=(Subrelation(String("b")), Subrelation(Relation("b")))), Relation.Signature(None, 2)),
        (Relation("a1", (Subrelation(Number(1)),)), Relation.Signature("a1", 1)),
    ],
)
def test_signature(relation: Relation, expected: Relation.Signature) -> None:
    actual = relation.signature
    assert actual == expected


@pytest.mark.parametrize(
    ("relation1", "relation2", "expected"),
    [
        (Relation(), Relation(), True),
        (Relation("a"), Relation("a"), True),
        (
            Relation(arguments=(Subrelation(Variable("V")), Subrelation(Number(2)))),
            Relation(arguments=(Subrelation(Number(1)), Subrelation(Variable("V")))),
            True,
        ),
        (Relation("a", (Subrelation(Relation("b")),)), Relation("a", (Subrelation(Relation("b")),)), True),
        (Relation("a", (Subrelation(Relation("b")),)), Relation("a", (Subrelation(Relation("c")),)), False),
        (
            Relation("a", (Subrelation(Relation("b")),)),
            Relation("a", (Subrelation(Relation("b")), Subrelation(Relation("c")))),
            False,
        ),
        (
            Relation("a", (Subrelation(Relation("b")), Subrelation(Relation("c")))),
            Relation("a", (Subrelation(Relation("b")), Subrelation(Relation("c")))),
            True,
        ),
        (Relation("a", (Subrelation(Relation("b")),)), Relation("a", (Subrelation(Variable("V")),)), True),
        (Relation("b", (Subrelation(Relation("b")),)), Relation("a", (Subrelation(Variable("V")),)), False),
        (
            Relation("b", (Subrelation(Relation("b")), Subrelation(Relation("c")))),
            Relation("a", (Subrelation(Variable("V")),)),
            False,
        ),
        (Relation("a", (Subrelation(Relation()),)), Relation("a", (Subrelation(Variable("V")),)), True),
        (
            Relation("a", (Subrelation(Relation(arguments=(Subrelation(Number(1)), Subrelation(Number(2))))),)),
            Relation("a", (Subrelation(Variable("V")),)),
            True,
        ),
        (
            Relation("a", (Subrelation(Relation(arguments=(Subrelation(Number(1)), Subrelation(Variable("N"))))),)),
            Relation("a", (Subrelation(Variable("V")),)),
            True,
        ),
        (
            Relation(arguments=(Subrelation(Number(1)), Subrelation(Number(2)))),
            Relation(arguments=(Subrelation(Number(1)), Subrelation(Number(1)))),
            False,
        ),
        (
            Relation(arguments=(Subrelation(String("a")),)),
            Relation(arguments=(Subrelation(Relation("a")),)),
            False,
        ),
        (
            Relation(arguments=(Subrelation(String("a")),)),
            Relation(arguments=(Subrelation(Variable("A")),)),
            True,
        ),
        (
            Relation(arguments=(Subrelation(String("a")),)),
            Relation(arguments=(Subrelation(String("b")),)),
            False,
        ),
        (
            Relation(arguments=(Subrelation(String("a")),)),
            Relation(arguments=(Subrelation(String("a")),)),
            True,
        ),
    ],
)
def test_unifies(relation1: Relation, relation2: Relation, expected: bool) -> None:
    actual = relation1.unifies(relation2)
    assert actual == expected
