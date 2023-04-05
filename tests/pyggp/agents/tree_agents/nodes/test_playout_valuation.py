import pytest
from pyggp.agents.tree_agents.valuations import PlayoutValuation


@pytest.mark.parametrize(
    ("this", "other", "expected"),
    [
        (
            PlayoutValuation({0: 0}, {0: 0}, {0: 0}),
            PlayoutValuation({0: 1}, {0: 0}, {0: 0}),
            PlayoutValuation({0: 1}, {0: 0}, {0: 0}),
        ),
        (
            PlayoutValuation({0: 1, 1: 5}, {0: 5, 1: 2}, {0: 0, 1: 1}),
            PlayoutValuation({0: 1, 1: 0}, {0: 0, 1: 0}, {0: 0, 1: 0}),
            PlayoutValuation({0: 2, 1: 5}, {0: 5, 1: 2}, {0: 0, 1: 1}),
        ),
    ],
)
def test_backpropagate(this: PlayoutValuation, other: PlayoutValuation, expected: PlayoutValuation) -> None:
    actual = this.backpropagate(other)
    assert actual == expected
