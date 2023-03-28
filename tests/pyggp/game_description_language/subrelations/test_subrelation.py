import lark
import pytest
from pyggp.exceptions.subrelation_exceptions import MalformedTreeSubrelationError, ParsingSubrelationError
from pyggp.game_description_language.subrelations import Number, Relation, String, Subrelation, Variable


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        ("a", Subrelation(Relation("a"))),
        ("1", Subrelation(Number(1))),
        ('""', Subrelation(String(""))),
        ("a(b)", Subrelation(Relation.from_symbols("a", Relation("b")))),
        ("a(1)", Subrelation(Relation.from_symbols("a", Number(1)))),
        ("a(1,  2, 3)", Subrelation(Relation.from_symbols("a", Number(1), Number(2), Number(3)))),
        ('a("b")', Subrelation(Relation.from_symbols("a", String("b")))),
        ("a()", Subrelation(Relation("a"))),
        ("()", Subrelation(Relation())),
        ("a((1,2))", Subrelation(Relation.from_symbols("a", Relation.from_symbols(None, Number(1), Number(2))))),
        ("a(V)", Subrelation(Relation.from_symbols("a", Variable("V")))),
    ],
)
def test_from_str(string: str, expected: Subrelation) -> None:
    actual = Subrelation.from_str(string)
    assert actual == expected


@pytest.mark.parametrize(
    # Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
    ("string",),  # noqa: PT006
    [
        ("a(b",),
        ("a(,)",),
        ("'a",),
        ("'a\"",),
        ("a(b,c",),
        ("a(b,)",),
    ],
)
def test_from_str_raises(string: str) -> None:
    with pytest.raises(ParsingSubrelationError):
        Subrelation.from_str(string)


@pytest.mark.parametrize(
    # Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
    ("tree",),  # noqa: PT006
    [
        (lark.Tree(data="malformed", children=[]),),
        (lark.Tree(data="subrelation", children=[lark.Token(type="malformed", value="")]),),
        (lark.Tree(data="subrelation", children=[lark.Tree(data="malformed", children=[])]),),
    ],
)
def test_from_tree_raises_on_invalid_tree(tree: lark.Tree[lark.Token]) -> None:
    with pytest.raises(MalformedTreeSubrelationError):
        Subrelation.from_tree(tree)


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
