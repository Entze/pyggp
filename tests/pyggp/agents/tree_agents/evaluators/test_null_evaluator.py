from typing import TYPE_CHECKING, Type
from unittest import mock

from pyggp.agents.tree_agents.evaluators import NullEvaluator

if TYPE_CHECKING:
    from pyggp.agents.tree_agents.perspectives import Perspective
    from pyggp.agents.tree_agents.valuations import Valuation
    from pyggp.interpreters import Interpreter


def test_null_evaluator() -> None:
    # noinspection PyTypeChecker
    mock_valuation_type: Type[Valuation] = mock.MagicMock()
    mock_interpreter: Interpreter = mock.MagicMock()
    mock_perspective: Perspective = mock.MagicMock()
    evaluator = NullEvaluator(mock_valuation_type)

    mock_valuation_type.assert_not_called()

    evaluator(mock_interpreter, mock_perspective)

    mock_valuation_type.assert_called_once_with()
