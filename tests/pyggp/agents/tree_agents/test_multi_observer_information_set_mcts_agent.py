import random
from unittest import mock

import pyggp.game_description_language as gdl
import pytest
from pyggp.agents import MultiObserverInformationSetMCTSAgent
from pyggp.agents.tree_agents.mcts.selectors import Selector
from pyggp.agents.tree_agents.nodes import HiddenInformationSetNode, VisibleInformationSetNode
from pyggp.engine_primitives import DevelopmentStep, Move, Role, State, Turn, View
from pyggp.interpreters import Interpreter


@pytest.fixture()
def mock_interpreter() -> Interpreter:
    return mock.Mock(spec=Interpreter, name="mock_interpreter")


def test_select_stops_on_incidental_final_state(mock_interpreter) -> None:
    player_1_role = Role(gdl.Subrelation(gdl.Relation("player", (gdl.Subrelation(gdl.Number(1)),))))
    player_2_role = Role(gdl.Subrelation(gdl.Relation("player", (gdl.Subrelation(gdl.Number(2)),))))

    root_state_1 = mock.Mock(spec=State, name="root_state_1")
    root_state_2 = mock.Mock(spec=State, name="root_state_2")
    root_view = mock.Mock(spec=View, name="root_view")

    child_state_1 = mock.Mock(spec=State, name="child_state_1")
    child_view = mock.Mock(spec=View, name="child_view")

    move_1 = mock.Mock(spec=Move, name="move_1")
    turn_1 = Turn(((player_1_role, move_1),))

    p1_root = VisibleInformationSetNode(
        possible_states={root_state_1, root_state_2},
        role=player_1_role,
        view=root_view,
    )

    p1_child = HiddenInformationSetNode(
        possible_states={child_state_1},
        role=player_1_role,
    )

    p1_root.children = {(root_state_2, move_1): p1_child}

    p2_root = HiddenInformationSetNode(
        possible_states={root_state_1, root_state_2},
        role=player_2_role,
    )

    p2_child = VisibleInformationSetNode(
        possible_states={child_state_1},
        role=player_2_role,
        view=child_view,
    )

    p2_root.children = {(root_state_1, turn_1): p2_child}

    p1_selector = mock.Mock(spec=Selector, name="p1_selector")
    p2_selector = mock.Mock(spec=Selector, name="p2_selector")

    trees = {player_1_role: p1_root, player_2_role: p2_root}
    selectors = {player_1_role: p1_selector, player_2_role: p2_selector}

    agent = MultiObserverInformationSetMCTSAgent(
        role=player_1_role,
        trees=trees,
        interpreter=mock_interpreter,
        selectors=selectors,
    )

    with mock.patch.object(random, "choice") as mock_choice:
        mock_choice.side_effect = (root_state_2,)
        nodes, determinization = agent._select()

    assert determinization == root_state_2
    assert nodes == trees


def test_select_moves_nodes_to_compatible_branch(mock_interpreter) -> None:
    role_bluffer = Role(gdl.Subrelation(gdl.Relation("bluffer")))
    role_caller = Role(gdl.Subrelation(gdl.Relation("caller")))

    red = gdl.Subrelation(gdl.Relation("red"))
    black = gdl.Subrelation(gdl.Relation("black"))
    chosen = gdl.Subrelation(gdl.Relation("chosen"))

    root_state = State(frozenset())
    root_view = View(root_state)

    root_bluffer = VisibleInformationSetNode(
        possible_states={root_state},
        role=role_bluffer,
        view=root_view,
    )
    root_caller = HiddenInformationSetNode(
        possible_states={root_state},
        role=role_caller,
    )

    move1_red = mock.Mock(spec=Move, name="move1_red")
    turn1_red = Turn(((role_bluffer, move1_red),))
    child1_red_state = State(frozenset({chosen, red}))

    move1_black = mock.Mock(spec=Move, name="move1_black")
    turn1_black = Turn(((role_bluffer, move1_black),))
    child1_black_state = State(frozenset({chosen, black}))

    child1_bluffer_red = HiddenInformationSetNode(
        possible_states={child1_red_state},
        role=role_bluffer,
        parent=root_bluffer,
    )
    child1_bluffer_black = HiddenInformationSetNode(
        possible_states={child1_black_state},
        role=role_bluffer,
        parent=root_bluffer,
    )
    root_bluffer_children = {
        (root_state, move1_red): child1_bluffer_red,
        (root_state, move1_black): child1_bluffer_black,
    }
    root_bluffer.children = root_bluffer_children

    child1_view = View(State(frozenset({chosen})))

    child1_caller = VisibleInformationSetNode(
        possible_states={child1_red_state, child1_black_state},
        role=role_caller,
        view=child1_view,
        parent=root_caller,
    )

    root_caller_children = {
        (root_state, turn1_red): child1_caller,
        (root_state, turn1_black): child1_caller,
    }
    root_caller.children = root_caller_children

    fold = gdl.Subrelation(gdl.Relation("fold"))
    call = gdl.Subrelation(gdl.Relation("call"))

    child2_red_fold_state = State(frozenset({red, fold}))
    child2_red_call_state = State(frozenset({red, call}))

    child2_bluffer_red = HiddenInformationSetNode(
        possible_states={child2_red_fold_state, child2_red_call_state},
        role=role_bluffer,
        parent=child1_bluffer_red,
    )

    move_call = Move(call)
    move_fold = Move(fold)
    turn2_call = Turn(((role_caller, move_call),))
    turn2_fold = Turn(((role_caller, move_fold),))

    child1_bluffer_red_children = {
        (child1_red_state, turn2_call): child2_bluffer_red,
        (child1_red_state, turn2_fold): child2_bluffer_red,
    }
    child1_bluffer_red.children = child1_bluffer_red_children

    child2_black_fold_state = State(frozenset({black, fold}))
    child2_black_call_state = State(frozenset({black, call}))

    child2_bluffer_black = HiddenInformationSetNode(
        possible_states={child2_black_fold_state, child2_black_call_state},
        role=role_bluffer,
        parent=child1_bluffer_black,
    )

    child1_bluffer_black_children = {
        (child1_black_state, turn2_call): child2_bluffer_black,
        (child1_black_state, turn2_fold): child2_bluffer_black,
    }
    child1_bluffer_black.children = child1_bluffer_black_children

    child2_caller_fold = HiddenInformationSetNode(
        possible_states={child2_red_fold_state, child2_black_fold_state},
        role=role_caller,
        parent=child1_caller,
    )
    child2_caller_call = HiddenInformationSetNode(
        possible_states={child2_red_call_state, child2_black_call_state},
        role=role_caller,
        parent=child1_caller,
    )

    child1_caller_children = {
        (child1_red_state, move_fold): child2_caller_fold,
        (child1_red_state, move_call): child2_caller_call,
        (child1_black_state, move_fold): child2_caller_fold,
        (child1_black_state, move_call): child2_caller_call,
    }
    child1_caller.children = child1_caller_children

    agent = MultiObserverInformationSetMCTSAgent()
    agent.role = role_caller

    trees = {
        role_bluffer: child1_bluffer_black,
        role_caller: child1_caller,
    }
    agent.trees = trees
    agent.interpreter = mock_interpreter

    state_to_isterminal = {
        root_state: False,
        child1_red_state: False,
        child1_black_state: False,
        child2_red_fold_state: True,
        child2_red_call_state: True,
        child2_black_fold_state: True,
        child2_black_call_state: True,
    }

    mock_interpreter.is_terminal.side_effect = lambda current: state_to_isterminal.get(current, False)

    nodetype_to_action = {
        VisibleInformationSetNode: move_call,
        HiddenInformationSetNode: turn2_call,
    }

    mock_selector = mock.Mock(spec=Selector, name="mock_selector")
    mock_selector.side_effect = lambda node, state: (state, nodetype_to_action[type(node)])

    agent.selectors = {role_caller: mock_selector, role_bluffer: mock_selector}

    development_step0 = DevelopmentStep(root_state, turn1_red)
    development_step1 = DevelopmentStep(child1_red_state, None)

    development = (development_step0, development_step1)
    developments = (development,)

    mock_interpreter.get_developments.side_effect = lambda _: iter(developments)

    stateplays_to_state = {
        (child1_red_state, turn2_call): child2_red_call_state,
    }

    mock_interpreter.get_next_state.side_effect = lambda state, turn: stateplays_to_state[(state, turn)]

    view_to_legal_moves_by_role = {
        root_view: {
            role_bluffer: frozenset({move1_red, move1_black}),
        },
        child1_view: {
            role_caller: frozenset({move_fold, move_call}),
        },
    }

    mock_interpreter.get_legal_moves_by_role.side_effect = lambda view, role: view_to_legal_moves_by_role[view][role]

    with mock.patch.object(random, "choice") as mock_choice:
        mock_choice.side_effect = (child1_red_state,)
        actual_nodes, actual_determinization = agent._select()

    expected_nodes = {
        role_bluffer: child2_bluffer_red,
        role_caller: child2_caller_call,
    }

    expected_determinization = child2_red_call_state

    assert actual_nodes == expected_nodes
    assert actual_determinization == expected_determinization
