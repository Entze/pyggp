import unittest.mock as mock

import pytest

import pyggp.agents
from pyggp.commands import load_by_name


@pytest.mark.skip
@pytest.mark.parametrize(
    "input,expected",
    [
        ("pyggp.agents.ArbitraryAgent", pyggp.agents.ArbitraryAgent),
        ("ArbitraryAgent", pyggp.agents.ArbitraryAgent),
    ],
)
def test_as_expected(input, expected) -> None:
    assert load_by_name(input) == expected


@pytest.mark.skip
def test_raises_no_matches() -> None:
    with pytest.raises(ValueError, match="No resources for pyggp.agents.__NonexistentAgent"):
        load_by_name("pyggp.agents.__NonexistentAgent")


@pytest.mark.skip
def test_raises_multiple_matches() -> None:
    __called_once = False

    def once_false(*args, **kwargs) -> bool:
        nonlocal __called_once
        if __called_once:
            return True
        __called_once = True
        return False

    mock_exists = mock.PropertyMock(side_effect=once_false)

    with mock.patch("pyggp.commands.DynamicLoader.exists", mock_exists):
        with pytest.raises(ValueError, match="Multiple resources for ArbitraryAgent: .*"):
            load_by_name("ArbitraryAgent")
