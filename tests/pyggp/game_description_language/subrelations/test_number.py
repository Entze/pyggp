import lark
import pytest
from pyggp.exceptions.subrelation_exceptions import MalformedTreeSubrelationError
from pyggp.game_description_language.subrelations import Number


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (Number(0), "0"),
        (Number(1), "1"),
    ],
)
def test_infix_str(number: Number, expected: str) -> None:
    actual = number.infix_str
    assert actual == expected


@pytest.mark.parametrize(
    "tree",
    [
        lark.Tree(data="malformed", children=[]),
        lark.Tree(data="number", children=[lark.Tree(data="malformed", children=[])]),
    ],
)
def test_from_tree_invalid_tree(tree: lark.Tree[lark.Token]) -> None:
    with pytest.raises(MalformedTreeSubrelationError):
        Number.from_tree(tree)


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (Number(0), "0"),
        (Number(1), "1"),
    ],
)
def test_dunder_str(number: Number, expected: str) -> None:
    actual = str(number)
    assert actual == expected


# Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
@pytest.mark.parametrize(("number",), [(Number(0),), (Number(1),)])  # noqa: PT006
def test_dunder_rich(number: Number) -> None:
    actual = number.__rich__()
    assert isinstance(actual, str)
    assert number.infix_str in actual
