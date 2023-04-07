import clingo.ast as clingo_ast
import pyggp._clingo as clingo_helper
import pytest
from pyggp.game_description_language.literals import Literal
from pyggp.game_description_language.subrelations import Relation, Subrelation


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        (Literal(atom=Relation(name="atom")), "atom"),
        (Literal(atom=Relation(name="atom"), sign=Literal.Sign.NEGATIVE), "not atom"),
    ],
)
def test_to_infix_str(literal: Literal, expected: str) -> None:
    actual = literal.infix_str
    assert actual == expected


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        (Literal(atom=Relation(name="atom")), Literal(atom=Relation(name="atom"), sign=Literal.Sign.NEGATIVE)),
        (Literal(atom=Relation(name="atom"), sign=Literal.Sign.NEGATIVE), Literal(atom=Relation(name="atom"))),
    ],
)
def test_dunder_neg(literal: Literal, expected: Literal) -> None:
    actual = -literal
    assert actual == expected


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        (Literal(atom=Relation(name="atom")), "atom"),
        (Literal(atom=Relation(name="atom"), sign=Literal.Sign.NEGATIVE), "not atom"),
        (
            Literal(
                atom=Relation(
                    name="__comp_not_equal",
                    arguments=(Subrelation(Relation("a")), Subrelation(Relation("b"))),
                ),
            ),
            "a != b",
        ),
        (
            Literal(
                atom=Relation(
                    name="__comp_not_equal",
                    arguments=(Subrelation(Relation("a")), Subrelation(Relation("b"))),
                ),
                sign=Literal.Sign.NEGATIVE,
            ),
            "a = b",
        ),
        (
            Literal(
                atom=Relation(
                    name="__comp_not_equal",
                    arguments=(Subrelation(Relation("a")), Subrelation(Relation("b")), Subrelation(Relation("c"))),
                ),
            ),
            "a != b != c",
        ),
    ],
)
def test_dunder_str(literal: Literal, expected: str) -> None:
    actual = str(literal)
    assert actual == expected


@pytest.mark.parametrize(
    # Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
    ("literal",),  # noqa: PT006
    [
        (Literal(atom=Relation(name="atom")),),
        (Literal(atom=Relation(name="atom"), sign=Literal.Sign.NEGATIVE),),
    ],
)
def test_dunder_rich(literal: Literal) -> None:
    actual = literal.__rich__()
    assert isinstance(actual, str)
    if literal.sign == Literal.Sign.NEGATIVE:
        assert "not" in actual
    assert literal.atom.infix_str in actual


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        (
            Literal(atom=Relation(name="atom")),
            clingo_helper.create_literal(
                atom=clingo_helper.create_atom(clingo_helper.create_function(name="atom")),
                sign=clingo_ast.Sign.NoSign,
            ),
        ),
        (
            Literal(atom=Relation(name="atom"), sign=Literal.Sign.NEGATIVE),
            clingo_helper.create_literal(
                atom=clingo_helper.create_atom(clingo_helper.create_function(name="atom")),
                sign=clingo_ast.Sign.Negation,
            ),
        ),
        (
            Literal(
                atom=Relation(
                    name="__comp_not_equal",
                    arguments=(Subrelation(Relation("a")), Subrelation(Relation("b"))),
                ),
            ),
            clingo_helper.create_literal(
                atom=clingo_helper.create_comparison(
                    term=clingo_helper.create_function(name="a"),
                    guards=(
                        clingo_helper.create_guard(
                            comparison=clingo_ast.ComparisonOperator.NotEqual,
                            term=clingo_helper.create_function(name="b"),
                        ),
                    ),
                ),
            ),
        ),
        (
            Literal(
                atom=Relation(
                    name="__comp_not_equal",
                    arguments=(Subrelation(Relation("a")), Subrelation(Relation("b"))),
                ),
                sign=Literal.Sign.NEGATIVE,
            ),
            clingo_helper.create_literal(
                atom=clingo_helper.create_comparison(
                    term=clingo_helper.create_function(name="a"),
                    guards=(
                        clingo_helper.create_guard(
                            comparison=clingo_ast.ComparisonOperator.Equal,
                            term=clingo_helper.create_function(name="b"),
                        ),
                    ),
                ),
            ),
        ),
    ],
)
def test_as_clingo_ast(literal: Literal, expected: clingo_ast.AST) -> None:
    actual = literal.as_clingo_ast()
    assert actual == expected
