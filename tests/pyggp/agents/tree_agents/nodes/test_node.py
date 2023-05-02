from typing import TYPE_CHECKING, Type
from unittest import mock

from pyggp.agents.tree_agents.nodes import Node

if TYPE_CHECKING:
    from pyggp.agents.tree_agents.perspectives import Perspective
    from pyggp.interpreters import State


@mock.patch.object(Node, "__abstractmethods__", set())
def test_from_state() -> None:
    mock_state: State = mock.MagicMock()
    mock_parent: Node = mock.MagicMock()
    # noinspection PyTypeChecker
    mock_perspective_type: Type[Perspective] = mock.MagicMock()

    Node.perspective_type = mock_perspective_type

    mock_perspective_type.from_state.assert_not_called()

    node = Node.from_state(mock_state, parent=mock_parent)
    assert node.parent is mock_parent

    mock_perspective_type.from_state.assert_called_once_with(mock_state)


@mock.patch.object(Node, "__abstractmethods__", set())
def test_evaluate_with_evaluator_with_valuation() -> None:
    mock_interpreter = mock.MagicMock()
    mock_evaluator = mock.MagicMock()
    mock_perspective = mock.MagicMock()
    mock_existing_valuation = mock.MagicMock()
    mock_return_valuation = mock.MagicMock()

    mock_evaluator.return_value = mock_return_valuation

    node = Node(perspective=mock_perspective, valuation=mock_existing_valuation)

    mock_evaluator.assert_not_called()
    mock_existing_valuation.propagate.assert_not_called()

    node.evaluate(interpreter=mock_interpreter, evaluator=mock_evaluator)

    mock_evaluator.assert_called_once_with(mock_interpreter, mock_perspective)
    mock_existing_valuation.propagate.assert_called_once_with(mock_return_valuation)


@mock.patch.object(Node, "__abstractmethods__", set())
def test_evaluate_with_evaluator_without_valuation() -> None:
    mock_interpreter = mock.MagicMock()
    mock_evaluator = mock.MagicMock()
    mock_perspective = mock.MagicMock()
    mock_return_valuation = mock.MagicMock()

    mock_evaluator.return_value = mock_return_valuation

    node = Node(perspective=mock_perspective)

    mock_evaluator.assert_not_called()
    assert node.valuation is None

    node.evaluate(interpreter=mock_interpreter, evaluator=mock_evaluator)

    mock_evaluator.assert_called_once_with(mock_interpreter, mock_perspective)
    assert node.valuation == mock_return_valuation


@mock.patch.object(Node, "__abstractmethods__", set())
def test_evaluate_without_evaluator() -> None:
    mock_interpreter = mock.MagicMock()
    mock_default_evaluator = mock.MagicMock()
    mock_perspective = mock.MagicMock()
    mock_return_valuation = mock.MagicMock()

    mock_default_evaluator.return_value = mock_return_valuation

    Node.default_evaluator = mock_default_evaluator
    node = Node(perspective=mock_perspective)

    mock_default_evaluator.assert_not_called()
    assert node.valuation is None

    node.evaluate(interpreter=mock_interpreter)

    mock_default_evaluator.assert_called_once_with(mock_interpreter, mock_perspective)
    assert node.valuation == mock_return_valuation


@mock.patch.object(Node, "__abstractmethods__", set())
def test_propagate_back() -> None:
    mock_root_perspective = mock.MagicMock()
    mock_parent_perspective = mock.MagicMock()
    mock_parent_valuation = mock.MagicMock()
    mock_node_perspective = mock.MagicMock()
    mock_node_valuation = mock.MagicMock()

    root = Node(perspective=mock_root_perspective)
    parent = Node(perspective=mock_parent_perspective, valuation=mock_parent_valuation, parent=root)
    node = Node(perspective=mock_node_perspective, valuation=mock_node_valuation, parent=parent)

    mock_return_valuation = mock.MagicMock()

    assert root.valuation is None
    mock_parent_valuation.propagate.assert_not_called()
    mock_node_valuation.propagate.assert_not_called()

    node.propagate_back(valuation=mock_return_valuation)

    assert root.valuation == parent.valuation
    mock_parent_valuation.propagate.assert_called_once_with(mock_return_valuation)
    mock_node_valuation.propagate.assert_not_called()


@mock.patch.object(Node, "__abstractmethods__", set())
def test_propagate_back_root() -> None:
    mock_perspective = mock.MagicMock()
    mock_existing_valuation = mock.MagicMock()
    mock_return_valuation = mock.MagicMock()

    root = Node(perspective=mock_perspective, valuation=mock_existing_valuation)

    mock_existing_valuation.propagate.assert_not_called()

    root.propagate_back(mock_return_valuation)

    mock_existing_valuation.propagate.assert_not_called()
