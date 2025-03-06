import pytest

from pyggp.game_description_language.subrelations import Variable


@pytest.mark.parametrize(
    ("variable", "expected"),
    [
        (Variable("a"), "a"),
        (Variable("_"), "_"),
        (Variable("_F"), "_F"),
    ],
)
def test_infix_str(variable: Variable, expected: str) -> None:
    actual = variable.infix_str
    assert actual == expected


@pytest.mark.parametrize(
    ("variable", "expected"),
    [
        (Variable("a"), False),
        (Variable("_"), True),
        (Variable("_F"), True),
    ],
)
def test_is_wildcard(variable: Variable, expected: bool) -> None:
    actual = variable.is_wildcard
    assert actual == expected


@pytest.mark.parametrize(
    ("variable", "expected"),
    [
        (Variable("a"), "a"),
        (Variable("_"), "_"),
        (Variable("_F"), "_F"),
    ],
)
def test_dunder_str(variable: Variable, expected: str) -> None:
    actual = str(variable)
    assert actual == expected


# Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
@pytest.mark.parametrize(("variable",), [(Variable("a"),), (Variable("_"),), (Variable("_F"),)])  # noqa: PT006
def test_dunder_rich(variable: Variable) -> None:
    actual = variable.__rich__()
    assert isinstance(actual, str)
    assert variable.infix_str in actual
