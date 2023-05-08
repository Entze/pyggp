from typing import Any, Callable
from unittest import mock

import pytest
from pyggp.agents.tree_agents.evaluators import Evaluator
from pyggp.agents.tree_agents.nodes import PerfectInformationNode
from pyggp.agents.tree_agents.valuations import Valuation
from pyggp.engine_primitives import DevelopmentStep, State, Turn, View
from pyggp.interpreters import Interpreter


@pytest.fixture()
def mock_state() -> State:
    return mock.Mock(spec=State)


@pytest.fixture()
def mock_interpreter() -> Interpreter:
    return mock.Mock(spec=Interpreter)


@pytest.fixture()
def mock_evaluator() -> Evaluator:
    return mock.Mock(spec=Evaluator)


@pytest.fixture()
def mock_valuation_factory() -> Callable[[Any], Valuation[Any]]:
    return mock.Mock(spec=Callable)


@pytest.fixture()
def mock_utility() -> Any:
    return mock.Mock()


@pytest.fixture()
def mock_valuation() -> Valuation[Any]:
    return mock.Mock(spec=Valuation)


def test_trim_noops_on_unexpanded_node(mock_state) -> None:
    node = PerfectInformationNode(state=mock_state)

    assert node.children is None

    node.trim()

    assert node.children is None


def test_trim_noops_on_no_turn(mock_state) -> None:
    node = PerfectInformationNode(state=mock_state)

    child1 = PerfectInformationNode(state=mock_state)
    child2 = PerfectInformationNode(state=mock_state)

    mock_turn_1 = mock.Mock(spec=Turn)
    mock_turn_2 = mock.Mock(spec=Turn)

    node.children = {
        mock_turn_1: child1,
        mock_turn_2: child2,
    }

    assert node.turn is None
    assert len(node.children) == 2

    node.trim()

    assert node.turn is None
    assert len(node.children) == 2


def test_trim_removes_unreachable_children(mock_state) -> None:
    node = PerfectInformationNode(state=mock_state)

    child1 = PerfectInformationNode(state=mock_state)
    child2 = PerfectInformationNode(state=mock_state)

    mock_turn_1 = mock.Mock(spec=Turn)
    mock_turn_2 = mock.Mock(spec=Turn)

    node.children = {
        mock_turn_1: child1,
        mock_turn_2: child2,
    }

    node.turn = mock_turn_1

    assert len(node.children) == 2

    node.trim()

    assert len(node.children) == 1
    assert node.children[mock_turn_1] == child1


def test_expand(mock_interpreter) -> None:
    mock_state = mock.Mock(spec=State)

    node = PerfectInformationNode(state=mock_state)

    mock_child_state_1 = mock.Mock(spec=State)
    child1 = PerfectInformationNode(state=mock_child_state_1, parent=node)
    mock_child_state_2 = mock.Mock(spec=State)
    child2 = PerfectInformationNode(state=mock_child_state_2, parent=node)
    mock_turn_1 = mock.Mock(spec=Turn)
    mock_turn_2 = mock.Mock(spec=Turn)

    children = {
        mock_turn_1: child1,
        mock_turn_2: child2,
    }

    all_next_states_seq = (
        (mock_turn_1, mock_child_state_1),
        (mock_turn_2, mock_child_state_2),
    )

    mock_interpreter.get_all_next_states.return_value = iter(all_next_states_seq)

    assert node.children is None

    node.expand(mock_interpreter)

    assert node.children is not None
    assert node.children == children


def test_evaluate(
    mock_state,
    mock_evaluator,
    mock_utility,
    mock_valuation,
    mock_interpreter,
    mock_valuation_factory,
) -> None:
    node = PerfectInformationNode(state=mock_state)

    mock_evaluator.return_value = mock_utility
    mock_valuation_factory.return_value = mock_valuation
    mock_valuation.utility = mock_utility

    assert node.valuation is None
    mock_valuation_factory.assert_not_called()

    node.evaluate(interpreter=mock_interpreter, evaluator=mock_evaluator, valuation_factory=mock_valuation_factory)

    assert node.valuation == mock_valuation
    mock_valuation_factory.assert_called_once_with(mock_utility)


def test_develop(mock_interpreter) -> None:
    mock_root_state = mock.Mock(spec=State)
    mock_root_turn = mock.Mock(spec=Turn)
    root = PerfectInformationNode(state=mock_root_state, turn=mock_root_turn)

    mock_parent_state = mock.Mock(spec=State)
    mock_parent_turn = mock.Mock(spec=Turn)
    parent = PerfectInformationNode(state=mock_parent_state, turn=mock_parent_turn, parent=root)

    root.children = {
        mock_root_turn: parent,
    }

    mock_state = mock.Mock(spec=State)
    node = PerfectInformationNode(state=mock_state, parent=parent)

    parent.children = {
        mock_parent_turn: node,
    }

    mock_child_1_state = mock.Mock(spec=State)
    child1 = PerfectInformationNode(state=mock_child_1_state, parent=node)
    mock_turn_1 = mock.Mock(spec=Turn)

    mock_child_2_state = mock.Mock(spec=State)
    child2 = PerfectInformationNode(state=mock_child_2_state, parent=node)
    mock_turn_2 = mock.Mock(spec=Turn)

    node.children = {
        mock_turn_1: child1,
        mock_turn_2: child2,
    }

    development_step_0 = DevelopmentStep(state=mock_root_state, turn=mock_root_turn)
    development_step_1 = DevelopmentStep(state=mock_parent_state, turn=mock_parent_turn)
    development_step_2 = DevelopmentStep(state=mock_state, turn=mock_turn_1)
    development_step_3 = DevelopmentStep(state=mock_child_1_state, turn=None)
    development = (development_step_0, development_step_1, development_step_2, development_step_3)
    developments = (development,)

    mock_interpreter.get_developments.return_value = iter(developments)
    mock_interpreter.get_all_next_states.return_value = iter(())

    center = node.develop(mock_interpreter, 3, View(mock_child_1_state))

    assert center == child1
