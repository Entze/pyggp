import lark
import pytest
from pyggp.exceptions.subrelation_exceptions import MalformedTreeSubrelationError, ParsingSubrelationError
from pyggp.game_description_language.subrelations import Number, Relation, String, Subrelation, Variable


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        ("()", Relation()),
        ("a", Relation("a")),
        ("a()", Relation("a")),
        ("a(b)", Relation.from_symbols("a", Relation("b"))),
        ("a(b, c)", Relation.from_symbols("a", Relation("b"), Relation("c"))),
        ("a(             b)", Relation.from_symbols("a", Relation("b"))),
        ("a(1,2,3)", Relation.from_symbols("a", Number(1), Number(2), Number(3))),
        ("(1, (2,3), ())", Relation.get_tuple(Number(1), Relation.get_tuple(Number(2), Number(3)), Relation())),
        ('a("b")', Relation.from_symbols("a", String("b"))),
        ("a(())", Relation.from_symbols("a", Relation())),
        ('a(("b"))', Relation.from_symbols("a", Relation.get_tuple(String("b")))),
        ("a(_)", Relation.from_symbols("a", Variable("_"))),
        ("a(_F)", Relation.from_symbols("a", Variable("_F"))),
        ("a(__test)", Relation.from_symbols("a", Relation("__test"))),
    ],
)
def test_from_str(string: str, expected: Relation) -> None:
    actual = Relation.from_str(string)
    assert actual == expected


@pytest.mark.parametrize(
    # Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
    ("string",),  # noqa: PT006
    [
        ("",),
        ("a(",),
        ("a)",),
    ],
)
def test_from_str_raises_on_invalid_str(string: str) -> None:
    with pytest.raises(ParsingSubrelationError):
        Relation.from_str(string)


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        (Relation(), "()"),
        (Relation("a"), "a"),
        (Relation("a", (Subrelation(Relation("b")),)), "a(b)"),
        (Relation("a", (Subrelation(Relation("b")), Subrelation(Relation("c")))), "a(b, c)"),
        (Relation(arguments=(Subrelation(String("b")), Subrelation(Relation("b")))), '("b", b)'),
        (Relation("a1", (Subrelation(Number(1)),)), "a1(1)"),
    ],
)
def test_infix_str(relation: Relation, expected: str) -> None:
    actual = relation.infix_str
    assert actual == expected


@pytest.mark.parametrize(
    # Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
    ("tree",),  # noqa: PT006
    [
        (lark.Tree(data="malformed", children=[]),),
        (lark.Tree(data="relation", children=[lark.Token(type="malformed", value="")]),),
        (
            lark.Tree(
                data="relation",
                children=[
                    lark.Tree(data="atom", children=[]),
                    lark.Tree(data="tuple", children=[]),
                    lark.Tree(data="malformed", children=[]),
                ],
            ),
        ),
        (
            lark.Tree(
                data="relation",
                children=[
                    lark.Tree(data="atom", children=[]),
                    lark.Tree(data="malformed", children=[]),
                ],
            ),
        ),
        (
            lark.Tree(
                data="relation",
                children=[
                    lark.Tree(
                        data="tuple",
                        children=[
                            lark.Token(type="malformed", value=""),
                        ],
                    ),
                ],
            ),
        ),
        (
            lark.Tree(
                data="relation",
                children=[
                    lark.Tree(data="atom", children=[]),
                    lark.Tree(data="tuple", children=[lark.Token(type="malformed", value="")]),
                ],
            ),
        ),
    ],
)
def test_from_tree_invalid_tree(tree: lark.Tree[lark.Token]) -> None:
    with pytest.raises(MalformedTreeSubrelationError):
        Relation.from_tree(tree)


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        (Relation(), "()"),
        (Relation("a"), "a"),
        (Relation("a", (Subrelation(Relation("b")),)), "a(b)"),
        (Relation("a", (Subrelation(Relation("b")), Subrelation(Relation("c")))), "a(b, c)"),
        (Relation(arguments=(Subrelation(String("b")), Subrelation(Relation("b")))), '("b", b)'),
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
