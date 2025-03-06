from unittest import mock

import pytest

import pyggp.game_description_language as gdl
from pyggp.agents.tree_agents.nodes import (
    HiddenInformationSetNode,
    ImperfectInformationNode,
    VisibleInformationSetNode,
)
from pyggp.engine_primitives import Development, DevelopmentStep, Move, Role, State, Turn, View
from pyggp.interpreters import ClingoInterpreter, Interpreter


@pytest.fixture
def mock_interpreter() -> Interpreter:
    return mock.Mock(spec=Interpreter, name="mock_interpreter")


@pytest.fixture
def mock_role() -> Role:
    return mock.Mock(spec=Role, name="mock_role")


def test_expand_to_visible_nodes(mock_interpreter) -> None:
    mock_role1 = mock.Mock(spec=Role, name="mock_role1")

    mock_state1 = mock.Mock(spec=State, name="mock_state1")
    mock_state2 = mock.Mock(spec=State, name="mock_state2")

    node = HiddenInformationSetNode(
        role=mock_role1,
        possible_states={mock_state1, mock_state2},
        depth=0,
        fully_enumerated=True,
    )

    mock_child_state1 = mock.Mock(spec=State, name="mock_child_state1")
    mock_child_state2 = mock.Mock(spec=State, name="mock_child_state2")
    mock_child_state3 = mock.Mock(spec=State, name="mock_child_state3")

    child = VisibleInformationSetNode(
        role=mock_role1,
        parent=node,
        possible_states={mock_child_state1, mock_child_state2, mock_child_state3},
        depth=1,
        fully_enumerated=True,
        fully_expanded=False,
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
        depth=0,
        fully_enumerated=True,
    )

    mock_child_state1 = mock.Mock(spec=State, name="mock_child_state1")
    mock_child_state2 = mock.Mock(spec=State, name="mock_child_state2")
    mock_child_state3 = mock.Mock(spec=State, name="mock_child_state3")

    child = HiddenInformationSetNode(
        role=mock_role1,
        parent=node,
        possible_states={mock_child_state1, mock_child_state2, mock_child_state3},
        depth=1,
        fully_enumerated=True,
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
        children=children,
    )

    assert node.children is children

    node.trim()

    expected = {(mock_state1, mock_turn1): mock_child1, (mock_state1, mock_turn2): mock_child2}

    assert node.children == expected


def test_develop_returns_visible_if_visible_and_hidden_children(mock_interpreter, mock_role) -> None:
    mock_node_state1 = mock.Mock(spec=State, name="mock_node_state1")
    mock_node_state2 = mock.Mock(spec=State, name="mock_node_state2")
    mock_node_turn1 = mock.Mock(spec=Turn, name="mock_node_turn1")

    node = HiddenInformationSetNode(
        role=mock_role,
        possible_states={mock_node_state1, mock_node_state2},
        fully_enumerated=True,
    )

    mock_child1_state1 = mock.Mock(spec=State, name="mock_child1_state1")
    mock_child1_state2 = mock.Mock(spec=State, name="mock_child1_state2")

    child1 = VisibleInformationSetNode(
        role=mock_role,
        parent=node,
        possible_states={mock_child1_state1, mock_child1_state2},
        depth=node.depth + 1,
        fully_enumerated=True,
    )

    mock_child2_state = mock.Mock(spec=State, name="mock_child2_state")

    child2 = HiddenInformationSetNode(
        role=mock_role,
        parent=node,
        possible_states={mock_child2_state},
        depth=node.depth + 1,
        fully_enumerated=True,
    )

    node.children = {
        (mock_node_state1, mock_node_turn1): child1,
        (mock_node_state2, mock_node_turn1): child2,
    }
    node.visible_child = child1
    node.hidden_child = child2

    mock_child1_view = mock.MagicMock(spec=View, name="mock_child1_view")
    mock_child1_view.__le__.side_effect = lambda other: other in (
        mock_child1_view,
        mock_child1_state1,
        mock_child1_state2,
    )

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

    mock_interpreter.get_developments.side_effect = lambda *args, **kwargs: iter(developments_seq)

    with mock.patch.object(Interpreter, "get_roles_in_control") as mock_get_roles_in_control:
        mock_get_roles_in_control.side_effect = lambda *args, **kwargs: {mock_role}
        current = node.develop(interpreter=mock_interpreter, ply=1, view=mock_child1_view)

    assert current is child1


def test_prune_removes_states_that_cannot_lead_to_view() -> None:
    pass


@pytest.fixture
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

    init_state = interpreter.get_init_state()
    init_view = interpreter.get_sees_by_role(init_state, role=x)

    root = VisibleInformationSetNode(view=init_view, possible_states={init_state}, role=x, fully_enumerated=True)

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
    tree.fill(interpreter)

    assert tree.view == view
    assert tree.possible_states == {state}


@pytest.fixture
def minipoker_ruleset() -> gdl.Ruleset:
    minipoker = """
    role(bluffer). role(caller). role(random).

    init(control(random)).

    colour(red). colour(black).

    next(dealt) :- does(random, deal(_C)).
    next(dealt) :- true(dealt).
    next(dealt(C)) :- colour(C), does(random, deal(C)).
    next(dealt(C)) :- colour(C), true(dealt(C)).
    next(control(bluffer)) :- does(random, deal(_C)).
    next(resigned(bluffer)) :- does(bluffer, resign).
    next(resigned(bluffer)) :- true(resigned(bluffer)).
    next(held(bluffer)) :- does(bluffer, hold).
    next(held(bluffer)) :- true(held(bluffer)).
    next(control(caller)) :- does(bluffer, hold).
    next(resigned(caller)) :- does(caller, resign).
    next(resigned(caller)) :- true(resigned(caller)).
    next(called(caller)) :- does(caller, call).
    next(called(caller)) :- true(called(caller)).

    sees(random, X) :- true(X).
    sees(Everyone, control(R)) :- role(Everyone), role(R), true(control(R)).
    sees(Everyone, dealt) :- role(Everyone), true(dealt).
    sees(Everyone, resigned(R)) :- role(Everyone), role(R), true(resigned(R)).
    sees(Everyone, held(R)) :- role(Everyone), role(R), true(held(R)).
    sees(Everyone, called(R)) :- role(Everyone), role(R), true(called(R)).
    sees(Everyone, dealt(C)) :- role(Everyone), colour(C), true(dealt(C)), true(called(caller)).
    sees(bluffer, dealt(C)) :- colour(C), true(dealt(C)).

    legal(random, deal(C)) :- colour(C).
    legal(bluffer, resign) :- true(dealt(red)).
    legal(bluffer, hold).
    legal(caller, resign).
    legal(caller, call).

    goal(bluffer, -10) :- true(resigned(bluffer)).
    goal(caller, 10) :- true(resigned(bluffer)).
    goal(bluffer, 4) :- true(resigned(caller)).
    goal(caller, -4) :- true(resigned(caller)).
    goal(bluffer, 16) :- true(dealt(black)), true(held(bluffer)), true(called(caller)).
    goal(caller, -16) :- true(dealt(black)), true(held(bluffer)), true(called(caller)).
    goal(bluffer, -20) :- true(dealt(red)), true(held(bluffer)), true(called(caller)).
    goal(caller, 20) :- true(dealt(red)), true(held(bluffer)), true(called(caller)).

    terminal :- true(resigned(bluffer)).
    terminal :- true(resigned(caller)).
    terminal :- true(held(bluffer)), true(called(caller)).

    """

    return gdl.transformer.transform(gdl.parser.parse(minipoker))


def test_minipoker(minipoker_ruleset) -> None:
    interpreter = ClingoInterpreter.from_ruleset(minipoker_ruleset)

    caller = Role(gdl.Subrelation(gdl.Relation("caller")))

    init_state = interpreter.get_init_state()

    root = HiddenInformationSetNode(possible_states={init_state}, role=caller, fully_enumerated=True)

    control_caller = gdl.Subrelation(gdl.Relation("control", (gdl.Subrelation(gdl.Relation("caller")),)))
    dealt = gdl.Subrelation(gdl.Relation("dealt"))
    held_bluffer = gdl.Subrelation(gdl.Relation("held", (gdl.Subrelation(gdl.Relation("bluffer")),)))
    target_state = State(frozenset({control_caller, dealt, held_bluffer}))
    view = View(target_state)

    actual = root.develop(interpreter=interpreter, ply=2, view=view)
    actual.fill(interpreter)

    dealt_red = gdl.Subrelation(gdl.Relation("dealt", (gdl.Subrelation(gdl.Relation("red")),)))
    dealt_black = gdl.Subrelation(gdl.Relation("dealt", (gdl.Subrelation(gdl.Relation("black")),)))

    possible_state1 = State(frozenset({control_caller, dealt_red, dealt, held_bluffer}))
    possible_state2 = State(frozenset({control_caller, dealt_black, dealt, held_bluffer}))

    assert actual.view == view
    assert actual.possible_states == {possible_state1, possible_state2}
