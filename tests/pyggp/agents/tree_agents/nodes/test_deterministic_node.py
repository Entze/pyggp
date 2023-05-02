from unittest import mock

import pyggp.game_description_language as gdl
from pyggp.agents.tree_agents.nodes import DeterministicNode
from pyggp.agents.tree_agents.perspectives import DeterministicPerspective
from pyggp.interpreters import DevelopmentStep, Interpreter, Move, Role, State, Turn, View


@mock.patch.object(DeterministicNode, "__abstractmethods__", set())
def test_develop() -> None:
    mock_interpreter: Interpreter = mock.MagicMock()

    ply = 1
    view: View = View(
        State(
            frozenset(
                {
                    gdl.Subrelation(gdl.Relation("heads")),
                    gdl.Subrelation(gdl.Relation("control", (gdl.Subrelation(gdl.Relation("player")),))),
                },
            ),
        ),
    )
    DeterministicNode.perspective_type = DeterministicPerspective

    root_state = State(
        frozenset(
            {
                gdl.Subrelation(gdl.Relation("heads")),
                gdl.Subrelation(gdl.Relation("control", (gdl.Subrelation(gdl.Relation("player")),))),
            },
        ),
    )
    root = DeterministicNode.from_state(root_state)

    flip_state = State(
        frozenset(
            {
                gdl.Subrelation(gdl.Relation("tails")),
                gdl.Subrelation(gdl.Relation("control", (gdl.Subrelation(gdl.Relation("player")),))),
            },
        ),
    )
    flip_turn = Turn.from_mapping(
        {Role(gdl.Subrelation(gdl.Relation("player"))): Move(gdl.Subrelation(gdl.Relation("flip")))},
    )
    flip_child = DeterministicNode.from_state(flip_state, parent=root)

    pass_state = State(
        frozenset(
            {
                gdl.Subrelation(gdl.Relation("heads")),
                gdl.Subrelation(gdl.Relation("control", (gdl.Subrelation(gdl.Relation("player")),))),
            },
        ),
    )
    pass_turn = Turn.from_mapping(
        {Role(gdl.Subrelation(gdl.Relation("player"))): Move(gdl.Subrelation(gdl.Relation("pass")))},
    )

    pass_child = DeterministicNode.from_state(pass_state, parent=root)

    root.children = {flip_turn: flip_child, pass_turn: pass_child}

    development = (DevelopmentStep(state=root_state, turn=pass_turn), DevelopmentStep(state=pass_state, turn=None))
    developments = (development,)

    mock_interpreter.get_developments.return_value = iter(developments)

    with mock.patch.object(DeterministicNode, "expand") as mock_expand:
        mock_expand.return_value = None
        child = root.develop(mock_interpreter, ply, view)

    assert child == pass_child
