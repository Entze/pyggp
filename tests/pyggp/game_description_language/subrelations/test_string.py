import pytest

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
