from unittest import mock

import pyggp.game_description_language as gdl
import pytest
from pyggp.agents.tree_agents.nodes import (
    HiddenInformationSetNode,
    InformationSetNode,
    VisibleInformationSetNode,
)
from pyggp.engine_primitives import Move, Role, State, Turn, View
from pyggp.interpreters import ClingoInterpreter, Interpreter


@pytest.fixture()
def mock_role() -> Role:
    return mock.Mock(spec=Role, name="mock_role")


@pytest.fixture()
def mock_interpreter() -> Interpreter:
    return mock.Mock(spec=Interpreter, name="mock_interpreter")


def test_expand_to_visible_nodes(mock_interpreter) -> None:
    mock_role1 = mock.Mock(spec=Role, name="mock_role1")

    mock_state1 = mock.Mock(spec=State, name="mock_state1")
    mock_state2 = mock.Mock(spec=State, name="mock_state2")

    node = VisibleInformationSetNode(
        role=mock_role1,
        possible_states={mock_state1, mock_state2},
    )

    mock_child1_view = mock.Mock(spec=State, name="mock_child1_view")
    mock_child1_state1 = mock.Mock(spec=State, name="mock_child1_state1")
    mock_child1_state2 = mock.Mock(spec=State, name="mock_child1_state2")

    mock_role1_move = mock.Mock(spec=Move, name="mock_role1_move")

    child1 = VisibleInformationSetNode(
        view=mock_child1_view,
        role=mock_role1,
        parent=node,
        possible_states={mock_child1_state1, mock_child1_state2},
    )

    mock_child2_view = mock.Mock(spec=State, name="mock_child2_view")
    mock_child2_state = mock.Mock(spec=State, name="mock_child2_state")

    child2 = VisibleInformationSetNode(
        view=mock_child2_view,
        role=mock_role1,
        parent=node,
        possible_states={mock_child2_state},
    )

    children = {
        (mock_state1, mock_role1_move): child1,
        (mock_state2, mock_role1_move): child2,
    }

    mock_role2 = mock.Mock(spec=Role, name="mock_role2")
    mock_role2_move1 = mock.Mock(spec=Move, name="mock_role2_move1")
    mock_role2_move2 = mock.Mock(spec=Move, name="mock_role2_move2")

    turn1 = Turn({mock_role1: mock_role1_move, mock_role2: mock_role2_move1})
    turn2 = Turn({mock_role1: mock_role1_move, mock_role2: mock_role2_move2})

    state_tsp_map = {
        mock_state1: ((turn1, mock_child1_state1), (turn2, mock_child1_state2)),
        mock_state2: ((turn1, mock_child2_state),),
    }

    mock_interpreter.get_all_next_states.side_effect = lambda state: iter(state_tsp_map[state])

    state_view_map = {
        mock_child1_state1: mock_child1_view,
        mock_child1_state2: mock_child1_view,
        mock_child2_state: mock_child2_view,
    }

    mock_interpreter.get_sees_by_role.side_effect = lambda state, _: state_view_map[state]

    assert node.children is None

    with mock.patch.object(Interpreter, "get_roles_in_control") as mock_get_roles_in_control:
        mock_get_roles_in_control.return_value = frozenset({mock_role1})
        node.expand(mock_interpreter)

    assert node.children == children


def test_expand_to_hidden_nodes(mock_interpreter) -> None:
    mock_role1 = mock.Mock(spec=Role, name="mock_role1")

    mock_state1 = mock.Mock(spec=State, name="mock_state1")
    mock_state2 = mock.Mock(spec=State, name="mock_state2")

    node = VisibleInformationSetNode(
        role=mock_role1,
        possible_states={mock_state1, mock_state2},
    )

    mock_child1_state1 = mock.Mock(spec=State, name="mock_child1_state1")
    mock_child1_state2 = mock.Mock(spec=State, name="mock_child1_state2")
    mock_child1_state3 = mock.Mock(spec=State, name="mock_child1_state3")

    mock_role1_move = mock.Mock(spec=Move, name="mock_role1_move")

    child1 = HiddenInformationSetNode(
        role=mock_role1,
        parent=node,
        possible_states={mock_child1_state1, mock_child1_state2, mock_child1_state3},
    )

    mock_role2 = mock.Mock(spec=Role, name="mock_role2")
    mock_role2_move1 = mock.Mock(spec=Move, name="mock_role2_move1")
    mock_role2_move2 = mock.Mock(spec=Move, name="mock_role2_move2")

    turn1 = Turn({mock_role1: mock_role1_move, mock_role2: mock_role2_move1})
    turn2 = Turn({mock_role1: mock_role1_move, mock_role2: mock_role2_move2})

    state_tsp_map = {
        mock_state1: ((turn1, mock_child1_state1), (turn2, mock_child1_state2)),
        mock_state2: ((turn1, mock_child1_state3),),
    }

    mock_interpreter.get_all_next_states.side_effect = lambda state: iter(state_tsp_map[state])

    assert node.children is None

    with mock.patch.object(Interpreter, "get_roles_in_control") as mock_get_roles_in_control:
        mock_get_roles_in_control.return_value = frozenset({mock_role2})
        node.expand(mock_interpreter)

    children = {
        (mock_state1, mock_role1_move): child1,
        (mock_state2, mock_role1_move): child1,
    }

    assert node.children == children


def test_trim_noop_on_unexpanded_node() -> None:
    mock_view = mock.Mock(spec=View, name="mock_view")

    node = VisibleInformationSetNode(
        view=mock_view,
        role=mock.Mock(spec=Role, name="mock_role"),
    )

    assert node.children is None

    node.trim()

    assert node.children is None


def test_trim_removes_children_with_impossible_state_and_move(mock_role) -> None:
    mock_state1a = mock.Mock(spec=State, name="mock_state1a")
    mock_state1b = mock.Mock(spec=State, name="mock_state1b")

    mock_state2a = mock.Mock(spec=State, name="mock_state2a")

    mock_child1 = mock.Mock(spec=InformationSetNode, name="mock_child1")
    mock_child2 = mock.Mock(spec=InformationSetNode, name="mock_child2")
    mock_child3 = mock.Mock(spec=InformationSetNode, name="mock_child3")

    mock_move1 = mock.Mock(spec=Move, name="mock_move1a")
    mock_move2 = mock.Mock(spec=Move, name="mock_move1b")
    mock_move3 = mock.Mock(spec=Move, name="mock_move2a")

    children = {
        (mock_state1a, mock_move1): mock_child1,
        (mock_state1a, mock_move2): mock_child1,
        (mock_state1b, mock_move1): mock_child2,
        (mock_state2a, mock_move3): mock_child3,
    }

    node = VisibleInformationSetNode(
        role=mock_role,
        possible_states={mock_state1a, mock_state1b, mock_state2a},
        move=mock_move1,
        children=children,
    )

    node.trim()

    expected = {
        (mock_state1a, mock_move1): mock_child1,
        (mock_state1b, mock_move1): mock_child2,
    }

    assert node.children == expected


def test_trim_removes_children_with_impossible_state(mock_role) -> None:
    mock_state1a = mock.Mock(spec=State, name="mock_state1a")
    mock_state1b = mock.Mock(spec=State, name="mock_state1b")

    mock_state2a = mock.Mock(spec=State, name="mock_state2a")

    mock_child1 = mock.Mock(spec=InformationSetNode, name="mock_child1")
    mock_child2 = mock.Mock(spec=InformationSetNode, name="mock_child2")
    mock_child3 = mock.Mock(spec=InformationSetNode, name="mock_child3")

    mock_move1 = mock.Mock(spec=Move, name="mock_move1a")
    mock_move2 = mock.Mock(spec=Move, name="mock_move1b")
    mock_move3 = mock.Mock(spec=Move, name="mock_move2a")

    children = {
        (mock_state1a, mock_move1): mock_child1,
        (mock_state1a, mock_move2): mock_child1,
        (mock_state1b, mock_move1): mock_child2,
        (mock_state2a, mock_move3): mock_child3,
    }

    node = VisibleInformationSetNode(
        role=mock_role,
        possible_states={mock_state1a, mock_state1b},
        children=children,
    )

    node.trim()

    expected = {
        (mock_state1a, mock_move1): mock_child1,
        (mock_state1a, mock_move2): mock_child1,
        (mock_state1b, mock_move1): mock_child2,
    }

    assert node.children == expected


def test_trim_noops_on_trimmed_node(mock_role) -> None:
    mock_state1a = mock.Mock(spec=State, name="mock_state1a")
    mock_state1b = mock.Mock(spec=State, name="mock_state1b")

    mock_state2a = mock.Mock(spec=State, name="mock_state2a")

    mock_child1 = mock.Mock(spec=InformationSetNode, name="mock_child1")
    mock_child2 = mock.Mock(spec=InformationSetNode, name="mock_child2")

    mock_move1 = mock.Mock(spec=Move, name="mock_move1")

    children = {
        (mock_state1a, mock_move1): mock_child1,
        (mock_state1b, mock_move1): mock_child2,
    }

    node = VisibleInformationSetNode(
        role=mock_role,
        possible_states={mock_state1a, mock_state1b, mock_state2a},
        move=mock_move1,
        children=children,
    )

    assert node.children == children

    node.trim()
    expected = children

    assert node.children == expected


@pytest.fixture()
def ruleset_two_moves_max() -> gdl.Ruleset:
    return gdl.transformer.transform(
        gdl.parser.parse(
            """
    role(p1). role(p2).

    init(control(p1)).

    next(control(R2)) :-
        role(R1), role(R2),
        distinct(R1, R2),
        does(R1, _).

    next(p1(A)) :- does(p1, A).
    next(p2(A)) :- does(p2, A).

    legal(R, 1) :- role(R).
    legal(R, 2) :- role(R).
    legal(R, 3) :- role(R).

    goal(p1, 100) :- true(p1(1)).

    terminal :- true(p1(_A1)), true(p2(_A2)).

    """,
        ),
    )


@pytest.fixture()
def ruleset_three_moves_max() -> gdl.Ruleset:
    return gdl.transformer.transform(
        gdl.parser.parse(
            """
            role(p1). role(p2).
            init(control(p1)).

            next(control(R2)) :-
                role(R1), role(R2),
                distinct(R1, R2),
                does(R1, _).

            next(turn(1, A)) :-
                true(turn(1, A)).

            next(turn(2, A)) :-
                true(turn(2, A)).

            next(turn(3, A)) :-
                true(turn(3, A)).

            next(turn(1, A)) :-
                role(R),
                not true(turn(1, _A1)),
                not true(turn(2, _A2)),
                not true(turn(3, _A3)),
                does(R, A).

            next(turn(2, A)) :-
                role(R),
                true(turn(1, _A1)),
                not true(turn(2, _A2)),
                not true(turn(3, _A3)),
                does(R, A).

            next(turn(3, A)) :-
                role(R),
                true(turn(1, _A1)),
                true(turn(2, _A2)),
                not true(turn(3, _A3)),
                does(R, A).

            legal(R, 1) :- role(R).
            legal(R, 2) :- role(R).
            legal(R, 3) :- role(R).

            goal(p1, 100) :- true(turn(3, 1)).

            terminal :- true(turn(3, _A1)).

            """,
        ),
    )


def test_develop_on_perfect_view(ruleset_two_moves_max) -> None:
    role_p1 = Role(gdl.Subrelation(gdl.Relation("p1")))
    role_p2 = Role(gdl.Subrelation(gdl.Relation("p2")))

    interpreter = ClingoInterpreter.from_ruleset(ruleset_two_moves_max)
    init_state = interpreter.get_init_state()

    root = HiddenInformationSetNode(
        role=role_p2,
        possible_states={init_state},
    )

    control_p2 = gdl.Subrelation(gdl.Relation("control", (gdl.Subrelation(gdl.Relation("p2")),)))
    p1_1 = gdl.Subrelation(gdl.Relation("p1", (gdl.Subrelation(gdl.Number(1)),)))
    p1_2 = gdl.Subrelation(gdl.Relation("p1", (gdl.Subrelation(gdl.Number(2)),)))
    p1_3 = gdl.Subrelation(gdl.Relation("p1", (gdl.Subrelation(gdl.Number(3)),)))

    state1 = State(frozenset({control_p2, p1_1}))
    state2 = State(frozenset({control_p2, p1_2}))
    state3 = State(frozenset({control_p2, p1_3}))

    child = VisibleInformationSetNode(
        role=role_p2,
        possible_states={state1, state2, state3},
        parent=root,
    )

    move1 = Move(gdl.Subrelation(gdl.Number(1)))
    move2 = Move(gdl.Subrelation(gdl.Number(2)))
    move3 = Move(gdl.Subrelation(gdl.Number(3)))
    turn1 = Turn({role_p1: move1})
    turn2 = Turn({role_p1: move2})
    turn3 = Turn({role_p1: move3})

    children = {
        (init_state, turn1): child,
        (init_state, turn2): child,
        (init_state, turn3): child,
    }
    root.children = children

    view = View(state2)

    assert child.possible_states == {state1, state2, state3}
    assert child.view is None
    assert root.children == children

    tree = root.develop(interpreter=interpreter, view=view, ply=1)

    expected_children = {
        (init_state, turn2): child,
    }

    assert child.view == view
    assert tree is child
    assert child.possible_states == {state2}
    assert root.children == expected_children


# Disables PLR0915 (too many statements). Because: This is a long test and needs a lot of statements.
def test_develop_on_perfect_view_after_move(ruleset_three_moves_max) -> None:  # noqa: PLR0915
    role_p1 = Role(gdl.Subrelation(gdl.Relation("p1")))
    role_p2 = Role(gdl.Subrelation(gdl.Relation("p2")))

    interpreter = ClingoInterpreter.from_ruleset(ruleset_three_moves_max)
    init_state = interpreter.get_init_state()

    init_view = interpreter.get_sees_by_role(init_state, role_p1)

    root = VisibleInformationSetNode(
        possible_states={init_state},
        view=init_view,
        role=role_p1,
    )

    control_p2 = gdl.Subrelation(gdl.Relation("control", (gdl.Subrelation(gdl.Relation("p2")),)))
    t_1_1 = gdl.Subrelation(gdl.Relation("turn", (gdl.Subrelation(gdl.Number(1)), gdl.Subrelation(gdl.Number(1)))))
    t_1_2 = gdl.Subrelation(gdl.Relation("turn", (gdl.Subrelation(gdl.Number(1)), gdl.Subrelation(gdl.Number(2)))))
    t_1_3 = gdl.Subrelation(gdl.Relation("turn", (gdl.Subrelation(gdl.Number(1)), gdl.Subrelation(gdl.Number(3)))))

    state_child1_1 = State(frozenset({control_p2, t_1_1}))

    child1_1 = HiddenInformationSetNode(
        role=role_p1,
        possible_states={state_child1_1},
        parent=root,
    )

    state_child1_2 = State(frozenset({control_p2, t_1_2}))

    child1_2 = HiddenInformationSetNode(
        role=role_p1,
        possible_states={state_child1_2},
        parent=root,
    )

    state_child1_3 = State(frozenset({control_p2, t_1_3}))

    child1_3 = HiddenInformationSetNode(
        role=role_p1,
        possible_states={state_child1_3},
        parent=root,
    )

    m1 = Move(gdl.Subrelation(gdl.Number(1)))
    m2 = Move(gdl.Subrelation(gdl.Number(2)))
    m3 = Move(gdl.Subrelation(gdl.Number(3)))

    root_children = {
        (init_state, m1): child1_1,
        (init_state, m2): child1_2,
        (init_state, m3): child1_3,
    }

    root.children = root_children

    control_p1 = gdl.Subrelation(gdl.Relation("control", (gdl.Subrelation(gdl.Relation("p1")),)))
    t_2_1 = gdl.Subrelation(gdl.Relation("turn", (gdl.Subrelation(gdl.Number(2)), gdl.Subrelation(gdl.Number(1)))))
    t_2_2 = gdl.Subrelation(gdl.Relation("turn", (gdl.Subrelation(gdl.Number(2)), gdl.Subrelation(gdl.Number(2)))))
    t_2_3 = gdl.Subrelation(gdl.Relation("turn", (gdl.Subrelation(gdl.Number(2)), gdl.Subrelation(gdl.Number(3)))))

    state_child2_1_1 = State(frozenset({control_p1, t_1_1, t_2_1}))
    state_child2_1_2 = State(frozenset({control_p1, t_1_1, t_2_2}))
    state_child2_1_3 = State(frozenset({control_p1, t_1_1, t_2_3}))

    child2_1 = VisibleInformationSetNode(
        role=role_p1,
        possible_states={state_child2_1_1, state_child2_1_2, state_child2_1_3},
        parent=child1_1,
    )

    turn_child1_1 = Turn({role_p2: m1})
    turn_child1_2 = Turn({role_p2: m2})
    turn_child1_3 = Turn({role_p2: m3})

    child1_1_children = {
        (state_child1_1, turn_child1_1): child2_1,
        (state_child1_1, turn_child1_2): child2_1,
        (state_child1_1, turn_child1_3): child2_1,
    }
    child1_1.children = child1_1_children

    state_child2_2_1 = State(frozenset({control_p1, t_1_2, t_2_1}))
    state_child2_2_2 = State(frozenset({control_p1, t_1_2, t_2_2}))
    state_child2_2_3 = State(frozenset({control_p1, t_1_2, t_2_3}))

    child2_2 = VisibleInformationSetNode(
        role=role_p1,
        possible_states={state_child2_2_1, state_child2_2_2, state_child2_2_3},
        parent=child1_2,
    )

    child1_2_children = {
        (state_child1_2, turn_child1_1): child2_2,
        (state_child1_2, turn_child1_2): child2_2,
        (state_child1_2, turn_child1_3): child2_2,
    }
    child1_2.children = child1_2_children

    state_child2_3_1 = State(frozenset({control_p1, t_1_3, t_2_1}))
    state_child2_3_2 = State(frozenset({control_p1, t_1_3, t_2_2}))
    state_child2_3_3 = State(frozenset({control_p1, t_1_3, t_2_3}))

    child2_3 = VisibleInformationSetNode(
        role=role_p1,
        possible_states={state_child2_3_1, state_child2_3_2, state_child2_3_3},
        parent=child1_3,
    )

    child1_3_children = {
        (state_child1_3, turn_child1_1): child2_3,
        (state_child1_3, turn_child1_2): child2_3,
        (state_child1_3, turn_child1_3): child2_3,
    }
    child1_3.children = child1_3_children

    view = View(state_child2_1_2)
    ply = 2

    assert child1_1.children == child1_1_children

    tree = child1_1.develop(interpreter=interpreter, view=view, ply=ply)

    expected_children = {
        (state_child1_1, turn_child1_2): child2_1,
    }

    assert child1_1.children == expected_children
    assert tree == child2_1
    assert tree.possible_states == {state_child2_1_2}
    assert isinstance(tree, VisibleInformationSetNode)
    assert tree.view == view
