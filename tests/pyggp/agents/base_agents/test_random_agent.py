from unittest import mock

import pyggp.game_description_language as gdl
from pyggp.agents import RandomAgent
from pyggp.engine_primitives import Move, Role, State, View
from pyggp.interpreters import Interpreter


def test_calculate_move() -> None:
    agent = RandomAgent()
    interpreter = mock.Mock(spec=Interpreter)
    legal_moves = frozenset(
        {
            Move(gdl.Subrelation(gdl.Relation("a"))),
            Move(gdl.Subrelation(gdl.Relation("b"))),
        },
    )
    interpreter.get_legal_moves_by_role.return_value = legal_moves
    role = mock.Mock(spec=Role)
    agent.interpreter = interpreter
    agent.role = role
    view = View(State(frozenset()))
    actual = agent.calculate_move(0, 0, view)
    expected = legal_moves
    assert actual in expected
