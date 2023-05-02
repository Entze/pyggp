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
