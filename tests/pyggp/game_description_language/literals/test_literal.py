import pytest
from pyggp.game_description_language.literals import Literal
from pyggp.game_description_language.subrelations import Relation


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
