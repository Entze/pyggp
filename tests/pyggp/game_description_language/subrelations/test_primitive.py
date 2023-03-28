import lark
import pytest
from pyggp.exceptions.subrelation_exceptions import MalformedTreeSubrelationError, ParsingSubrelationError
from pyggp.game_description_language.subrelations import Number, Primitive, String, Variable


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        ('"a"', String("a")),
        ('"_"', String("_")),
        ("A", Variable("A")),
        ("_", Variable("_")),
        ("_F", Variable("_F")),
        ("1", Number(1)),
    ],
)
def test_from_str_valid_strs(string: str, expected: Primitive) -> None:
    actual = Primitive.from_str(string)
    assert actual == expected


# Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
@pytest.mark.parametrize(
    ("string",),  # noqa: PT006
    [
        ("",),
        ("'",),
        ('"',),
        ("'a",),
        ("a'",),
        ('"a',),
        ('a"',),
        ("'\"",),
        ("1starts_with_digits",),
        ("small_caps",),
        ("_small_caps",),
    ],
)
def test_from_str_invalid_strs(string: str) -> None:
    with pytest.raises(ParsingSubrelationError):
        Primitive.from_str(string)


@pytest.mark.parametrize(
    "tree",
    [
        lark.Tree(data="malformed", children=[]),
        lark.Tree(data="primitive", children=[lark.Token("", "malformed")]),
        lark.Tree(data="primitive", children=[lark.Tree(data="malformed", children=[])]),
    ],
)
def test_from_tree_invalid_tree(tree: lark.Tree[lark.Token]) -> None:
    with pytest.raises(MalformedTreeSubrelationError):
        Primitive.from_tree(tree)
