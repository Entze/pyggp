from typing import Mapping, Optional
from unittest import mock

import pytest
from pyggp.agents.tree_agents.evaluators import (
    default_evaluator,
    default_factory_evaluator,
    final_goal_normalized_utility_evaluator,
)
from pyggp.engine_primitives import Role, State
from pyggp.interpreters import Interpreter


@pytest.fixture()
def mock_interpreter() -> Interpreter:
    return mock.Mock(spec=Interpreter)


@pytest.fixture()
def mock_state() -> State:
    return mock.Mock(spec=State)


def test_default_evaluator(mock_interpreter, mock_state) -> None:
    mock_default = mock.Mock()

    actual = default_evaluator(interpreter=mock_interpreter, perspective=mock_state, default=mock_default)

    expected = mock_default
    assert actual == expected


def test_default_factory_evaluator(mock_interpreter, mock_state) -> None:
    mock_default_factory = mock.Mock()
    mock_default = mock.Mock()
    mock_default_factory.return_value = mock_default

    mock_default_factory.assert_not_called()

    actual = default_factory_evaluator(
        interpreter=mock_interpreter,
        perspective=mock_state,
        default_factory=mock_default_factory,
    )

    mock_default_factory.assert_called_once_with()

    expected = mock_default
    assert actual == expected


@pytest.mark.parametrize(
    ("goals", "role", "expected"),
    [
        ({0: 100, 1: 0}, 0, 1.0),
        ({0: 100, 1: 0}, 1, 0.0),
        ({0: 50, 1: 50}, 0, 1 / 2),
        ({0: 50, 1: 50}, 1, 1 / 2),
        ({0: 100, 1: 50, 2: 50, 3: 0}, 0, 1.0),
        ({0: 100, 1: 50, 2: 50, 3: 0}, 1, 1 / 3),
        ({0: 100, 1: 50, 2: 50, 3: 0}, 2, 1 / 3),
        ({0: 100, 1: 50, 2: 50, 3: 0}, 3, 0.0),
        ({0: 100, 1: 50, 2: 0, 3: 0}, 0, 1.0),
        ({0: 100, 1: 50, 2: 0, 3: 0}, 1, 2 / 3),
        ({0: 100, 1: 50, 2: 0, 3: 0}, 2, 1 / 6),
        ({0: 100, 1: 50, 2: 0, 3: 0}, 3, 1 / 6),
    ],
)
def test_final_goal_normalized_utility_evaluator(
    mock_interpreter,
    mock_state,
    goals: Mapping[Role, Optional[int]],
    role: Role,
    expected: float,
) -> None:
    mock_interpreter.get_goals.return_value = goals

    actual = final_goal_normalized_utility_evaluator(state=mock_state, role=role, interpreter=mock_interpreter)
    assert pytest.approx(actual) == expected
