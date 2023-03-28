import lark
import pytest
from pyggp.exceptions.subrelation_exceptions import MalformedTreeSubrelationError
from pyggp.game_description_language.subrelations import String


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        (String("a"), '"a"'),
        (String("_"), '"_"'),
        (String("_F"), '"_F"'),
        (String("1"), '"1"'),
    ],
)
def test_infix_str(string: String, expected: str) -> None:
    actual = string.infix_str
    assert actual == expected


@pytest.mark.parametrize(
    # Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
    ("tree",),  # noqa: PT006
    [
        (lark.Tree(data="malformed", children=[]),),
        (lark.Tree(data="string", children=[lark.Tree(data="malformed", children=[])]),),
    ],
)
def test_from_tree_invalid_tree(tree: lark.Tree[lark.Token]) -> None:
    with pytest.raises(MalformedTreeSubrelationError):
        String.from_tree(tree)


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        (String("a"), '"a"'),
        (String("_"), '"_"'),
        (String("_F"), '"_F"'),
        (String("1"), '"1"'),
    ],
)
def test_dunder_str(string: String, expected: str) -> None:
    actual = str(string)
    assert actual == expected


@pytest.mark.parametrize(
    # Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
    ("string",),  # noqa: PT006
    [
        (String("a"),),
        (String("_"),),
        (String("_F"),),
        (String("1"),),
    ],
)
def test_dunder_rich(string: String) -> None:
    actual = string.__rich__()
    assert isinstance(actual, str)
    assert string.infix_str in actual
