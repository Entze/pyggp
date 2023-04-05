from unittest import mock

import pyggp.game_description_language as gdl
import pytest
from pyggp.agents import ArbitraryAgent
from pyggp.exceptions.agent_exceptions import InterpreterIsNoneInterpreterAgentError, RoleIsNoneInterpreterAgentError
from pyggp.interpreters import Move, State, View


def test_calculate_move() -> None:
    agent = ArbitraryAgent()
    interpreter = mock.MagicMock()
    interpreter.get_legal_moves_by_role.return_value = frozenset(
        {
            Move(gdl.Subrelation(gdl.Relation("a"))),
            Move(gdl.Subrelation(gdl.Relation("b"))),
        },
    )
    role = mock.MagicMock()
    agent._interpreter = interpreter
    agent._role = role
    view = View(State(frozenset()))
    with mock.patch("random.choice") as mock_choice:
        mock_choice.return_value = Move(gdl.Subrelation(gdl.Relation("a")))
        move = agent.calculate_move(0, 0, view)
    assert move == Move(gdl.Subrelation(gdl.Relation("a")))
    interpreter.get_legal_moves_by_role.assert_called_once_with(view, role)


def test_calculate_move_raises_on_no_interpreter() -> None:
    agent = ArbitraryAgent()
    view = View(State(frozenset()))
    with pytest.raises(InterpreterIsNoneInterpreterAgentError):
        agent.calculate_move(0, 0, view)


def test_calculate_move_raises_on_no_role() -> None:
    agent = ArbitraryAgent()
    interpreter = mock.MagicMock()
    agent._interpreter = interpreter
    view = View(State(frozenset()))
    with pytest.raises(RoleIsNoneInterpreterAgentError):
        agent.calculate_move(0, 0, view)
