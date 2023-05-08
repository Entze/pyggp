from unittest import mock

import pyggp.game_description_language as gdl
import pytest
from pyggp.agents.tree_agents.nodes import (
    HiddenInformationSetNode,
    ImperfectInformationNode,
    VisibleInformationSetNode,
)
from pyggp.engine_primitives import Development, DevelopmentStep, Move, Role, State, Turn, View
from pyggp.interpreters import ClingoInterpreter, Interpreter


@pytest.fixture()
def mock_interpreter() -> Interpreter:
    return mock.Mock(spec=Interpreter, name="mock_interpreter")


@pytest.fixture()
def mock_role() -> Role:
    return mock.Mock(spec=Role, name="mock_role")


def test_expand_to_visible_nodes(mock_interpreter) -> None:
    mock_role1 = mock.Mock(spec=Role, name="mock_role1")

    mock_state1 = mock.Mock(spec=State, name="mock_state1")
    mock_state2 = mock.Mock(spec=State, name="mock_state2")

    node = HiddenInformationSetNode(
        role=mock_role1,
        possible_states={mock_state1, mock_state2},
    )

    mock_child_state1 = mock.Mock(spec=State, name="mock_child_state1")
    mock_child_state2 = mock.Mock(spec=State, name="mock_child_state2")
    mock_child_state3 = mock.Mock(spec=State, name="mock_child_state3")

    child = VisibleInformationSetNode(
        role=mock_role1,
        parent=node,
        possible_states={mock_child_state1, mock_child_state2, mock_child_state3},
    )

    mock_turn1 = mock.Mock(spec=Turn, name="mock_turn1")
    mock_turn2 = mock.Mock(spec=Turn, name="mock_turn2")

    state_tsp_map = {
        mock_state1: ((mock_turn1, mock_child_state1), (mock_turn2, mock_child_state2)),
        mock_state2: ((mock_turn1, mock_child_state3),),
    }

    mock_interpreter.get_all_next_states.side_effect = lambda state: iter(state_tsp_map[state])

    children = {
        (mock_state1, mock_turn1): child,
        (mock_state1, mock_turn2): child,
        (mock_state2, mock_turn1): child,
    }

    assert node.children is None

    with mock.patch.object(Interpreter, "get_roles_in_control") as mock_get_roles_in_control:
        mock_get_roles_in_control.return_value = frozenset({mock_role1})
        node.expand(mock_interpreter)

    assert node.children == children


def test_expand_to_hidden_nodes(mock_interpreter) -> None:
    mock_role1 = mock.Mock(spec=Role, name="mock_role1")

    mock_state1 = mock.Mock(spec=State, name="mock_state1")
    mock_state2 = mock.Mock(spec=State, name="mock_state2")

    node = HiddenInformationSetNode(
        role=mock_role1,
        possible_states={mock_state1, mock_state2},
    )

    mock_child_state1 = mock.Mock(spec=State, name="mock_child_state1")
    mock_child_state2 = mock.Mock(spec=State, name="mock_child_state2")
    mock_child_state3 = mock.Mock(spec=State, name="mock_child_state3")

    child = HiddenInformationSetNode(
        role=mock_role1,
        parent=node,
        possible_states={mock_child_state1, mock_child_state2, mock_child_state3},
    )

    mock_turn1 = mock.Mock(spec=Turn, name="mock_turn1")
    mock_turn2 = mock.Mock(spec=Turn, name="mock_turn2")

    state_tsp_map = {
        mock_state1: ((mock_turn1, mock_child_state1), (mock_turn2, mock_child_state2)),
        mock_state2: ((mock_turn1, mock_child_state3),),
    }

    mock_interpreter.get_all_next_states.side_effect = lambda state: iter(state_tsp_map[state])

    children = {
        (mock_state1, mock_turn1): child,
        (mock_state1, mock_turn2): child,
        (mock_state2, mock_turn1): child,
    }

    assert node.children is None

    mock_role2 = mock.Mock(spec=Role, name="mock_role2")

    with mock.patch.object(Interpreter, "get_roles_in_control") as mock_get_roles_in_control:
        mock_get_roles_in_control.return_value = frozenset({mock_role2})
        node.expand(mock_interpreter)

    assert node.children == children


def test_trim_returns_as_is_on_unexpanded(mock_role) -> None:
    mock_state = mock.Mock(spec=State, name="mock_state")

    node = HiddenInformationSetNode(
        role=mock_role,
        possible_states={mock_state},
    )

    assert node.children is None

    node.trim()

    assert node.children is None


def test_trim_removes_impossible_states(mock_role) -> None:
    mock_state1 = mock.Mock(spec=State, name="mock_state1")
    mock_state2 = mock.Mock(spec=State, name="mock_state2")

    mock_child = mock.Mock(spec=ImperfectInformationNode, name="mock_child")

    mock_turn1 = mock.Mock(spec=Turn, name="mock_turn1")
    mock_turn2 = mock.Mock(spec=Turn, name="mock_turn2")

    children = {
        (mock_state1, mock_turn1): mock_child,
        (mock_state1, mock_turn2): mock_child,
        (mock_state2, mock_turn2): mock_child,
    }

    node = HiddenInformationSetNode(
        role=mock_role,
        possible_states={mock_state1},
        children=children,
    )

    assert node.children == children

    node.trim()

    expected = {
        (mock_state1, mock_turn1): mock_child,
        (mock_state1, mock_turn2): mock_child,
    }

    assert node.children == expected


def test_trim_removes_unreachable_children(mock_role) -> None:
    mock_state1 = mock.Mock(spec=State, name="mock_state1")
    mock_state2 = mock.Mock(spec=State, name="mock_state2")

    mock_child1 = mock.Mock(spec=ImperfectInformationNode, name="mock_child1")
    mock_child2 = mock.Mock(spec=ImperfectInformationNode, name="mock_child2")

    mock_turn1 = mock.Mock(spec=Turn, name="mock_turn1")
    mock_turn2 = mock.Mock(spec=Turn, name="mock_turn2")

    children = {
        (mock_state1, mock_turn1): mock_child1,
        (mock_state1, mock_turn2): mock_child2,
        (mock_state2, mock_turn1): mock_child1,
    }

    node = HiddenInformationSetNode(
        role=mock_role,
        possible_states={mock_state1},
        possible_turns={mock_turn1},
        children=children,
    )

    assert node.children is children

    node.trim()

    expected = {(mock_state1, mock_turn1): mock_child1}

    assert node.children == expected


def test_develop_prunes_possible_states_in_unambiguous_visible_child(mock_interpreter, mock_role) -> None:
    mock_root_state = mock.Mock(spec=State, name="mock_root_state")

    mock_root_turn1 = mock.Mock(spec=Turn, name="mock_root_turn1")
    mock_root_turn2 = mock.Mock(spec=Turn, name="mock_root_turn2")

    root = HiddenInformationSetNode(
        role=mock_role,
        possible_states={mock_root_state},
        possible_turns={mock_root_turn1, mock_root_turn2},
    )

    mock_node1_state1 = mock.Mock(spec=State, name="mock_node1_state1")
    mock_node1_state2 = mock.Mock(spec=State, name="mock_node1_state2")

    node1 = VisibleInformationSetNode(
        role=mock_role,
        possible_states={mock_node1_state1, mock_node1_state2},
        parent=root,
    )

    root.children = {
        (mock_root_state, mock_root_turn1): node1,
        (mock_root_state, mock_root_turn2): node1,
    }

    mock_node1_state1_view = mock.Mock(spec=View, name="mock_node1_view")

    development1_step0 = DevelopmentStep(state=mock_root_state, turn=mock_root_turn1)
    development1_step1 = DevelopmentStep(state=mock_node1_state1, turn=None)

    development1 = Development((development1_step0, development1_step1))

    developments_seq = (development1,)

    mock_interpreter.get_developments.side_effect = lambda _: iter(developments_seq)

    assert node1.view is None
    assert node1.possible_states == {mock_node1_state1, mock_node1_state2}

    current = root.develop(interpreter=mock_interpreter, ply=1, view=mock_node1_state1_view)

    assert current is node1
    assert node1.view == mock_node1_state1_view
    assert node1.possible_states == {mock_node1_state1}


def test_develop_keeps_possible_states_in_ambiguous_visible_child(mock_interpreter, mock_role) -> None:
    mock_root_state = mock.Mock(spec=State, name="mock_root_state")

    mock_root_turn1 = mock.Mock(spec=Turn, name="mock_root_turn1")
    mock_root_turn2 = mock.Mock(spec=Turn, name="mock_root_turn2")

    root = HiddenInformationSetNode(
        role=mock_role,
        possible_states={mock_root_state},
        possible_turns={mock_root_turn1, mock_root_turn2},
    )

    mock_node1_state1 = mock.Mock(spec=State, name="mock_node1_state1")
    mock_node1_state2 = mock.Mock(spec=State, name="mock_node1_state2")

    node1 = VisibleInformationSetNode(
        role=mock_role,
        possible_states={mock_node1_state1, mock_node1_state2},
        parent=root,
    )

    root.children = {
        (mock_root_state, mock_root_turn1): node1,
        (mock_root_state, mock_root_turn2): node1,
    }

    mock_node1_view = mock.Mock(spec=View, name="mock_node1_view")

    development1_step0 = DevelopmentStep(state=mock_root_state, turn=mock_root_turn1)
    development1_step1 = DevelopmentStep(state=mock_node1_state1, turn=None)

    development1 = Development((development1_step0, development1_step1))

    development2_step0 = DevelopmentStep(state=mock_root_state, turn=mock_root_turn2)
    development2_step1 = DevelopmentStep(state=mock_node1_state2, turn=None)

    development2 = Development((development2_step0, development2_step1))

    developments_seq = (development1, development2)

    mock_interpreter.get_developments.side_effect = lambda _: iter(developments_seq)

    assert node1.view is None
    assert node1.possible_states == {mock_node1_state1, mock_node1_state2}

    current = root.develop(interpreter=mock_interpreter, ply=1, view=mock_node1_view)

    assert current is node1
    assert node1.view == mock_node1_view
    assert node1.possible_states == {mock_node1_state1, mock_node1_state2}


def test_develop_returns_visible_if_visible_and_hidden_children(mock_interpreter, mock_role) -> None:
    mock_node_state1 = mock.Mock(spec=State, name="mock_node_state1")
    mock_node_state2 = mock.Mock(spec=State, name="mock_node_state2")
    mock_node_turn1 = mock.Mock(spec=Turn, name="mock_node_turn1")

    node = HiddenInformationSetNode(
        role=mock_role,
        possible_states={mock_node_state1, mock_node_state2},
        possible_turns={mock_node_turn1},
    )

    mock_child1_state1 = mock.Mock(spec=State, name="mock_child1_state1")
    mock_child1_state2 = mock.Mock(spec=State, name="mock_child1_state2")

    child1 = VisibleInformationSetNode(
        role=mock_role,
        parent=node,
        possible_states={mock_child1_state1, mock_child1_state2},
    )

    mock_child2_state = mock.Mock(spec=State, name="mock_child2_state")

    child2 = HiddenInformationSetNode(
        role=mock_role,
        parent=node,
        possible_states={mock_child2_state},
    )

    node.children = {
        (mock_node_state1, mock_node_turn1): child1,
        (mock_node_state2, mock_node_turn1): child2,
    }

    mock_child1_view = mock.Mock(spec=View, name="mock_child1_view")

    development1_step0 = DevelopmentStep(
        state=mock_node_state1,
        turn=mock_node_turn1,
    )
    development1_step1 = DevelopmentStep(
        state=mock_child1_state1,
        turn=None,
    )

    development1 = Development((development1_step0, development1_step1))

    developments_seq = (development1,)

    mock_interpreter.get_developments.side_effect = lambda _: iter(developments_seq)

    current = node.develop(interpreter=mock_interpreter, ply=1, view=mock_child1_view)

    assert current is child1
    assert node.possible_turns == {mock_node_turn1}


def test_develop_returns_deeper_visible_if_visible_and_hidden_children(mock_interpreter, mock_role) -> None:
    mock_node_state = mock.Mock(spec=State, name="mock_node_state")
    mock_turn1_a = mock.Mock(spec=Turn, name="mock_turn1_a")
    mock_turn1_b = mock.Mock(spec=Turn, name="mock_turn1_b")

    node = HiddenInformationSetNode(
        role=mock_role,
        possible_states={mock_node_state},
        possible_turns={mock_turn1_a, mock_turn1_b},
    )

    mock_child1_a_state = mock.Mock(spec=State, name="mock_child1_a_state")

    child1_a = HiddenInformationSetNode(
        role=mock_role,
        parent=node,
        possible_states={mock_child1_a_state},
    )

    mock_child1_b_state = mock.Mock(spec=State, name="mock_child1_b_state")

    child1_b = VisibleInformationSetNode(
        role=mock_role,
        parent=node,
        possible_states={mock_child1_b_state},
    )

    node.children = {
        (mock_node_state, mock_turn1_a): child1_a,
        (mock_node_state, mock_turn1_b): child1_b,
    }

    mock_child2_state = mock.Mock(spec=State, name="mock_child2_state")

    child2 = VisibleInformationSetNode(
        parent=child1_a,
        role=mock_role,
        possible_states={mock_child2_state},
    )

    mock_move2 = mock.Mock(spec=Move, name="mock_move2")
    turn2 = Turn({mock_role: mock_move2})

    child1_a.children = {
        (mock_child1_a_state, turn2): child2,
    }

    development1_step0 = DevelopmentStep(
        state=mock_node_state,
        turn=mock_turn1_a,
    )
    development1_step1 = DevelopmentStep(state=mock_child1_a_state, turn=turn2)
    development1_step2 = DevelopmentStep(
        state=mock_child2_state,
        turn=None,
    )

    development1 = Development((development1_step0, development1_step1, development1_step2))

    developments_seq = (development1,)

    mock_interpreter.get_developments.side_effect = lambda _: iter(developments_seq)

    mock_child2_view = mock.Mock(spec=View, name="mock_child2_view")

    current = node.develop(interpreter=mock_interpreter, ply=2, view=mock_child2_view)

    assert current is child2
    assert child2.view == mock_child2_view


@pytest.fixture()
def tic_tac_toe_ruleset() -> gdl.Ruleset:
    tic_tac_toe = """
    role(x). role(o).

    init(control(x)).

    cell(1, 1). cell(2, 1). cell(3, 1).
    cell(1, 2). cell(2, 2). cell(3, 2).
    cell(1, 3). cell(2, 3). cell(3, 3).

    row(M, P) :-
        role(P),
        cell(M, 1), cell(M, 2), cell(M, 3),
        true(cell(M, 1, P)),
        true(cell(M, 2, P)),
        true(cell(M, 3, P)).

    column(N, P) :-
        role(P),
        cell(1, N), cell(2, N), cell(3, N),
        true(cell(1, N, P)),
        true(cell(2, N, P)),
        true(cell(3, N, P)).

    diagonal(P) :-
        role(P),
        cell(1, 1), cell(2, 2), cell(3, 3),
        true(cell(1, 1, P)),
        true(cell(2, 2, P)),
        true(cell(3, 3, P)).

    diagonal(P) :-
        role(P),
        cell(1, 3), cell(2, 2), cell(3, 1),
        true(cell(1, 3, P)),
        true(cell(2, 2, P)),
        true(cell(3, 1, P)).

    line(P) :-
        role(P),
        row(_M, P).

    line(P) :-
        role(P),
        column(_N, P).

    line(P) :-
        role(P),
        diagonal(P).

    open :-
        cell(M, N),
        not true(cell(M, N, _P)).

    next(cell(M, N, P)) :-
        role(P),
        cell(M, N),
        does(P, cell(M, N)).

    next(cell(M, N, P)) :-
        role(P),
        cell(M, N),
        true(cell(M, N, P)).

    next(control(P1)) :-
        role(P1), role(P2),
        distinct(P1, P2),
        open,
        true(control(P2)).

    legal(P, cell(M, N)) :-
        role(P),
        cell(M, N),
        not true(cell(M, N, _P)).

    goal(P1, 0) :-
        role(P1), role(P2), distinct(P1, P2),
        line(P2).

    goal(P1, 50) :-
        role(P1), role(P2), distinct(P1, P2),
        not line(P1), not line(P2),
        not open.

    goal(P, 100) :-
        role(P), line(P).

    terminal :-
        role(P),
        line(P).

    terminal :-
        not open.
    """
    return gdl.transformer.transform(gdl.parser.parse(tic_tac_toe))


def test_tic_tac_toe(tic_tac_toe_ruleset) -> None:
    interpreter = ClingoInterpreter.from_ruleset(tic_tac_toe_ruleset)

    x = Role(gdl.Subrelation(gdl.Relation("x")))
    o = Role(gdl.Subrelation(gdl.Relation("o")))

    init_state = interpreter.get_init_state()
    init_view = interpreter.get_sees_by_role(init_state, role=x)

    root = VisibleInformationSetNode(view=init_view, possible_states={init_state}, role=x)

    root.expand(interpreter)
    # for child in root.children.values():
    #    child.expand(interpreter)
    # for grandchild in child.children.values():
    #    grandchild.expand(interpreter)

    cell_2_2 = gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(2)), gdl.Subrelation(gdl.Number(2)))))
    m1 = Move(cell_2_2)

    root.move = m1

    node = root.children[(init_state, m1)]

    control_x = gdl.Subrelation(gdl.Relation("control", (gdl.Subrelation(gdl.Relation("x")),)))
    cell_2_2_x = gdl.Subrelation(
        gdl.Relation(
            "cell",
            (gdl.Subrelation(gdl.Number(2)), gdl.Subrelation(gdl.Number(2)), gdl.Subrelation(gdl.Relation("x"))),
        ),
    )
    cell_3_1_o = gdl.Subrelation(
        gdl.Relation(
            "cell",
            (gdl.Subrelation(gdl.Number(3)), gdl.Subrelation(gdl.Number(1)), gdl.Subrelation(gdl.Relation("o"))),
        ),
    )
    state = State(frozenset({control_x, cell_2_2_x, cell_3_1_o}))
    view = View(state)

    tree = node.develop(interpreter=interpreter, ply=2, view=view)

    assert tree.view == view
    assert tree.possible_states == {state}
    assert tree.children is None
