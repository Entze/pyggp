from typing import Any, Callable
from unittest import mock

import pytest
from pyggp.agents.tree_agents.evaluators import Evaluator
from pyggp.agents.tree_agents.nodes import (
    HiddenInformationSetNode,
    _AbstractInformationSetNode,
)
from pyggp.agents.tree_agents.valuations import Valuation
from pyggp.engine_primitives import Role, View
from pyggp.interpreters import Interpreter


@pytest.fixture()
def mock_role() -> Role:
    return mock.Mock(spec=Role, name="mock_role")


@pytest.fixture()
def mock_interpreter() -> Interpreter:
    return mock.Mock(spec=Interpreter, name="mock_interpreter")


@pytest.fixture()
def mock_evaluator() -> Evaluator:
    return mock.Mock(spec=Evaluator, name="mock_evaluator")


@pytest.fixture()
def mock_valuation_factory() -> Callable[[Any], Valuation[Any]]:
    return mock.Mock(spec=Callable[[Any], Valuation[Any]], name="mock_valuation_factory")


@mock.patch.object(_AbstractInformationSetNode, "__abstractmethods__", frozenset())
def test_evaluate_sets_valuation(mock_interpreter, mock_evaluator, mock_valuation_factory) -> None:
    mock_utility = mock.Mock(name="mock_utility")
    mock_valuation = mock.Mock(spec=Valuation, name="mock_valuation")
    mock_valuation.utility = mock_utility

    mock_evaluator.return_value = mock_utility
    mock_valuation_factory.return_value = mock_valuation

    node = _AbstractInformationSetNode()

    mock_state = mock.Mock(name="mock_state")

    node.possible_states = frozenset({mock_state})
    node.valuation = None

    assert node.valuation is None
    mock_evaluator.assert_not_called()
    mock_valuation_factory.assert_not_called()

    actual = node.evaluate(mock_interpreter, mock_evaluator, mock_valuation_factory)

    assert actual == mock_utility
    assert node.valuation == mock_valuation
    mock_evaluator.assert_called_once_with(state=mock_state, interpreter=mock_interpreter)
    mock_valuation_factory.assert_called_once_with(mock_utility)


@mock.patch.object(_AbstractInformationSetNode, "__abstractmethods__", frozenset())
def test_develop_returns_node_as_is_on_same_height(mock_interpreter) -> None:
    parent = _AbstractInformationSetNode()
    parent.parent = None

    node = _AbstractInformationSetNode()
    node.parent = parent
    node.__class__ = HiddenInformationSetNode

    child = _AbstractInformationSetNode()
    child.parent = node

    mock_view = mock.Mock(spec=View, name="mock_view")
    ply = 1

    actual = node.develop(mock_interpreter, ply, mock_view)

    assert actual is node
