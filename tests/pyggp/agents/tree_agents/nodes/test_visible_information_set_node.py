from unittest import mock

import pyggp.game_description_language as gdl
import pytest
from pyggp.agents.tree_agents.nodes import (
    HiddenInformationSetNode,
    ImperfectInformationNode,
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
        fully_enumerated=True,
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
        depth=node.depth + 1,
        fully_enumerated=True,
    )

    mock_child2_view = mock.Mock(spec=State, name="mock_child2_view")
    mock_child2_state = mock.Mock(spec=State, name="mock_child2_state")

    child2 = VisibleInformationSetNode(
        view=mock_child2_view,
        role=mock_role1,
        parent=node,
        possible_states={mock_child2_state},
        depth=node.depth + 1,
        fully_enumerated=True,
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
        fully_enumerated=True,
    )

    mock_child1_state1 = mock.Mock(spec=State, name="mock_child1_state1")
    mock_child1_state2 = mock.Mock(spec=State, name="mock_child1_state2")
    mock_child1_state3 = mock.Mock(spec=State, name="mock_child1_state3")

    mock_role1_move = mock.Mock(spec=Move, name="mock_role1_move")

    child1 = HiddenInformationSetNode(
        role=mock_role1,
        parent=node,
        possible_states={mock_child1_state1, mock_child1_state2, mock_child1_state3},
        depth=node.depth + 1,
        fully_enumerated=True,
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
        fully_enumerated=True,
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
        depth=root.depth + 1,
        fully_enumerated=True,
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
    root.visible_child = child

    view = View(state2)

    assert child.possible_states == {state1, state2, state3}
    assert child.view is None
    assert root.children == children

    tree = root.develop(interpreter=interpreter, view=view, ply=1)

    expected_children = {
        (init_state, turn1): child,
        (init_state, turn2): child,
        (init_state, turn3): child,
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
        fully_enumerated=True,
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
        depth=root.depth + 1,
        fully_enumerated=True,
    )

    state_child1_2 = State(frozenset({control_p2, t_1_2}))

    child1_2 = HiddenInformationSetNode(
        role=role_p1,
        possible_states={state_child1_2},
        parent=root,
        depth=root.depth + 1,
        fully_enumerated=True,
    )

    state_child1_3 = State(frozenset({control_p2, t_1_3}))

    child1_3 = HiddenInformationSetNode(
        role=role_p1,
        possible_states={state_child1_3},
        parent=root,
        depth=root.depth + 1,
        fully_enumerated=True,
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
    root.move_to_hiddenchild = {m1: child1_1, m2: child1_2, m3: child1_3}
    root.view_to_visiblechild = {}

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
        depth=child1_1.depth + 1,
        fully_enumerated=True,
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
    child1_1.visible_child = child2_1

    state_child2_2_1 = State(frozenset({control_p1, t_1_2, t_2_1}))
    state_child2_2_2 = State(frozenset({control_p1, t_1_2, t_2_2}))
    state_child2_2_3 = State(frozenset({control_p1, t_1_2, t_2_3}))

    child2_2 = VisibleInformationSetNode(
        role=role_p1,
        possible_states={state_child2_2_1, state_child2_2_2, state_child2_2_3},
        parent=child1_2,
        depth=child1_2.depth + 1,
        fully_enumerated=True,
    )

    child1_2_children = {
        (state_child1_2, turn_child1_1): child2_2,
        (state_child1_2, turn_child1_2): child2_2,
        (state_child1_2, turn_child1_3): child2_2,
    }
    child1_2.children = child1_2_children
    child1_2.visible_child = child2_2

    state_child2_3_1 = State(frozenset({control_p1, t_1_3, t_2_1}))
    state_child2_3_2 = State(frozenset({control_p1, t_1_3, t_2_2}))
    state_child2_3_3 = State(frozenset({control_p1, t_1_3, t_2_3}))

    child2_3 = VisibleInformationSetNode(
        role=role_p1,
        possible_states={state_child2_3_1, state_child2_3_2, state_child2_3_3},
        parent=child1_3,
        depth=child1_3.depth + 1,
        fully_enumerated=True,
    )

    child1_3_children = {
        (state_child1_3, turn_child1_1): child2_3,
        (state_child1_3, turn_child1_2): child2_3,
        (state_child1_3, turn_child1_3): child2_3,
    }
    child1_3.children = child1_3_children
    child1_3.visible_child = child2_3

    view = View(state_child2_1_2)
    ply = 2

    assert child1_1.children == child1_1_children

    tree = child1_1.develop(interpreter=interpreter, view=view, ply=ply)

    expected_children = {
        (state_child1_1, turn_child1_1): child2_1,
        (state_child1_1, turn_child1_2): child2_1,
        (state_child1_1, turn_child1_3): child2_1,
    }

    assert child1_1.children == expected_children
    assert tree == child2_1
    assert tree.possible_states == {state_child2_1_2}
    assert isinstance(tree, VisibleInformationSetNode)
    assert tree.view == view


@pytest.fixture()
def ruleset_phantom_connect_5_6_4() -> gdl.Ruleset:
    rules = """
role(x). role(o).

init(control(x)).

row(1). row(2). row(3). row(4). row(5).
col(1). col(2). col(3). col(4). col(5). col(6).
win(4).

succ(0, 1). succ(1, 2). succ(2, 3). succ(3, 4). succ(4, 5). succ(5, 6). succ(6,7). succ(7,8).

next(control(R1)) :-
    role(R1), role(R2), distinct(R1,R2), row(Row), col(Col),
    true(control(R2)),
    not true(cell(Row, Col, _Role)),
    does(R2, cell(Row, Col)).

next(control(R)) :-
    role(R), row(Row), col(Col),
    true(control(R)),
    true(cell(Row, Col, _Role)),
    does(R, cell(Row, Col)).

next(cell(Row,Col,Role)) :-
    row(Row), col(Col), role(Role),
    true(cell(Row,Col,Role)).

next(cell(Row,Col,Role)) :-
    row(Row), col(Col), role(Role),
    not true(cell(Row,Col,_Role)),
    does(Role, cell(Row, Col)).

next(revealed(Role, cell(Row,Col))) :-
    role(Role), row(Row), col(Col),
    true(revealed(Role, cell(Row,Col))).

next(revealed(Role, cell(Row,Col))) :-
    role(Role), row(Row), col(Col),
    does(Role, cell(Row, Col)).

sees(Everyone, control(Role)) :-
    role(Everyone), role(Role),
    true(control(Role)).

sees(Role1, revealed(Role2, cell(Row, Col))) :-
    role(Role1), role(Role2), row(Row), col(Col),
    true(revealed(Role1, cell(Row,Col))),
    true(revealed(Role2, cell(Row,Col))).

sees(Role1, cell(Row,Col,Role2)) :-
    role(Role1), row(Row), col(Col), role(Role2),
    true(revealed(Role1, cell(Row,Col))),
    true(cell(Row,Col,Role2)).

legal(Role, cell(Row, Col)) :-
    role(Role), row(Row), col(Col),
    not true(revealed(Role, cell(Row,Col))).

open :-
    row(Row), col(Col),
    not true(cell(Row,Col,_)).

connects(Role, Row1, Col, Row2, Col, 2) :-
    role(Role), row(Row1), row(Row2), col(Col),
    succ(Row1, Row2),
    true(cell(Row1,Col,Role)),
    true(cell(Row2,Col,Role)).

connects(Role, Row1, Col, Row2, Col, N) :-
    role(Role), row(Row1), row(Row2), col(Col),
    row(Row0),
    succ(M, N), succ(Row0, Row1), succ(Row1, Row2),
    true(cell(Row1,Col,Role)),
    true(cell(Row2,Col,Role)),
    connects(Role, Row0, Col, Row1, Col, M).


connects(Role, Row, Col1, Row, Col2, 2) :-
    role(Role), row(Row), col(Col1), col(Col2),
    succ(Col1, Col2),
    true(cell(Row,Col1,Role)),
    true(cell(Row,Col2,Role)).

connects(Role, Row, Col1, Row, Col2, N) :-
    role(Role), row(Row), col(Col1), col(Col2),
    col(Col0),
    succ(M, N), succ(Col0, Col1), succ(Col1, Col2),
    true(cell(Row,Col1,Role)),
    true(cell(Row,Col2,Role)),
    connects(Role, Row, Col0, Row, Col1, M).


connects(Role, Row1, Col1, Row2, Col2, 2) :-
    role(Role), row(Row1), row(Row2), col(Col1), col(Col2),
    succ(Row1, Row2), succ(Col1, Col2),
    true(cell(Row1,Col1,Role)),
    true(cell(Row2,Col2,Role)).

connects(Role, Row1, Col1, Row2, Col2, N) :-
    role(Role), row(Row1), row(Row2), col(Col1), col(Col2),
    row(Row0), col(Col0),
    succ(M, N),
    succ(Row0, Row1), succ(Row1, Row2),
    succ(Col0, Col1), succ(Col1, Col2),
    true(cell(Row1,Col1,Role)),
    true(cell(Row2,Col2,Role)),
    connects(Role, Row0, Col0, Row1, Col1, M).


connects(Role, Row2, Col1, Row1, Col2, 2) :-
    role(Role), row(Row1), row(Row2), col(Col1), col(Col2),
    succ(Row1, Row2), succ(Col1, Col2),
    true(cell(Row1,Col2,Role)),
    true(cell(Row2,Col1,Role)).

connects(Role, Row3, Col1, Row2, Col2, N) :-
    role(Role),
    row(Row1), row(Row2), row(Row3),
    col(Col1), col(Col2), col(Col3),
    succ(M, N),
    succ(Row1, Row2), succ(Row2, Row3),
    succ(Col1, Col2), succ(Col2, Col3),
    true(cell(Row3,Col1,Role)),
    true(cell(Row2,Col2,Role)),
    connects(Role, Row2, Col2, Row1, Col3, M).


line(Role) :-
    role(Role),
    connects(Role, _Row1, _Col1, _Row2, _Col2, N),
    win(N).

goal(Role1, 0) :-
    role(Role1), role(Role2), distinct(Role1, Role2),
    line(Role2).

goal(Role1, 50) :-
    role(Role1), role(Role2), distinct(Role1, Role2),
    not open,
    not line(Role1),
    not line(Role2).

goal(Role1, 100) :-
    role(Role1),
    line(Role1).

terminal :-
    not open.

terminal :-
    line(_Role).
    """
    return gdl.transformer.transform(gdl.parser.parse(rules))


def test_phantom_connect_5_6_4_revealing(ruleset_phantom_connect_5_6_4) -> None:
    interpreter = ClingoInterpreter.from_ruleset(ruleset_phantom_connect_5_6_4)

    x = Role(gdl.Subrelation(gdl.Relation("x")))
    o = Role(gdl.Subrelation(gdl.Relation("o")))

    init_state = interpreter.get_init_state()
    state_0 = init_state
    view_0 = interpreter.get_sees_by_role(state_0, x)

    tree_x: ImperfectInformationNode[float] = VisibleInformationSetNode(
        possible_states={state_0},
        role=x,
        fully_enumerated=True,
    )
    tree_o: ImperfectInformationNode[float] = HiddenInformationSetNode(
        possible_states={state_0},
        role=o,
        fully_enumerated=True,
    )

    tree_x = tree_x.develop(interpreter, 0, view_0)
    tree_x.fill(interpreter)

    cell_1_1 = Move(
        gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(1)), gdl.Subrelation(gdl.Number(1))))),
    )
    state_1 = interpreter.get_next_state(state_0, Turn({x: cell_1_1}))
    view_1 = interpreter.get_sees_by_role(state_1, o)
    tree_x.move = cell_1_1

    tree_o = tree_o.develop(interpreter, 1, view_1)
    tree_o.fill(interpreter)

    state_2 = interpreter.get_next_state(state_1, Turn({o: cell_1_1}))
    view_2 = interpreter.get_sees_by_role(state_2, o)
    tree_o.move = cell_1_1

    tree_o = tree_o.develop(interpreter, 2, view_2)
    tree_o.fill(interpreter)

    tree_o.expand(interpreter)

    assert tree_o.children
