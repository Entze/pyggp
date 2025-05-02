from unittest import mock

import pytest

from pyggp import game_description_language as gdl
from pyggp.agents import MultiObserverInformationSetMCTSAgent
from pyggp.agents.tree_agents.mcts.valuations import NormalizedUtilityValuation
from pyggp.agents.tree_agents.nodes import HiddenInformationSetNode, ImperfectInformationNode, VisibleInformationSetNode
from pyggp.engine_primitives import Move, Role, State


@pytest.fixture
def role() -> Role:
    return Role(gdl.Subrelation(gdl.Relation("role")))


@pytest.fixture
def state() -> State:
    return mock.Mock(spec=frozenset)


@pytest.fixture
def state_win() -> State:
    return mock.Mock(spec=frozenset)


@pytest.fixture
def state_loss() -> State:
    return mock.Mock(spec=frozenset)


@pytest.fixture
def move_loss() -> Move:
    return mock.Mock(spec=gdl.Subrelation)


@pytest.fixture
def move_win() -> Move:
    return mock.Mock(spec=gdl.Subrelation)


@pytest.fixture
def move_even() -> Move:
    return mock.Mock(spec=gdl.Subrelation)


@pytest.fixture
def valuation_loss() -> NormalizedUtilityValuation:
    return NormalizedUtilityValuation(utility=0.0, total_playouts=500)


@pytest.fixture
def valuation_win() -> NormalizedUtilityValuation:
    return NormalizedUtilityValuation(utility=500.0, total_playouts=500)


@pytest.fixture
def valuation_even() -> NormalizedUtilityValuation:
    return NormalizedUtilityValuation(utility=500.0, total_playouts=1000)


@pytest.fixture
def parent_single_loss_child(
    role: Role,
    state: State,
    move_loss: Move,
    child_loss: ImperfectInformationNode[float],
) -> VisibleInformationSetNode[float]:
    parent: VisibleInformationSetNode[float] = VisibleInformationSetNode(role)
    parent.children = {(state, move_loss): child_loss}
    return parent


@pytest.fixture
def parent_with_win_child_and_loss_child(
    role: Role,
    state: State,
    move_loss: Move,
    move_win: Move,
    child_loss: ImperfectInformationNode[float],
    child_win: ImperfectInformationNode[float],
) -> VisibleInformationSetNode[float]:
    parent: VisibleInformationSetNode[float] = VisibleInformationSetNode(role)
    parent.children = {(state, move_loss): child_loss, (state, move_win): child_win}
    return parent


@pytest.fixture
def parent_with_even_child(
    role: Role,
    state_loss: State,
    state_win: State,
    move_even: Move,
    child_even: ImperfectInformationNode[float],
) -> VisibleInformationSetNode[float]:
    parent: VisibleInformationSetNode[float] = VisibleInformationSetNode(role)
    parent.children = {(state_loss, move_even): child_even, (state_win, move_even): child_even}
    return parent


@pytest.fixture
def child_loss(role: Role, valuation_loss: NormalizedUtilityValuation) -> HiddenInformationSetNode[float]:
    child = HiddenInformationSetNode(role)
    child.valuation = valuation_loss
    return child


@pytest.fixture
def child_win(role: Role, valuation_win: NormalizedUtilityValuation) -> HiddenInformationSetNode[float]:
    child = HiddenInformationSetNode(role)
    child.valuation = valuation_win
    return child


@pytest.fixture
def child_even(role: Role, valuation_even: NormalizedUtilityValuation) -> HiddenInformationSetNode[float]:
    child = HiddenInformationSetNode(role)
    child.valuation = valuation_even
    return child


@pytest.fixture
def agent_single_state_single_move(
    role: Role,
    parent_single_loss_child: ImperfectInformationNode[float],
) -> MultiObserverInformationSetMCTSAgent[float]:
    agent = MultiObserverInformationSetMCTSAgent()
    agent.role = role
    agent.trees = {role: parent_single_loss_child}
    return agent


@pytest.fixture
def agent_single_state_duo_move(
    role: Role,
    parent_with_win_child_and_loss_child: ImperfectInformationNode[float],
) -> MultiObserverInformationSetMCTSAgent[float]:
    agent = MultiObserverInformationSetMCTSAgent()
    agent.role = role
    agent.trees = {role: parent_with_win_child_and_loss_child}
    return agent


@pytest.fixture
def agent_duo_state_single_move(
    role: Role,
    parent_with_even_child: ImperfectInformationNode[float],
) -> MultiObserverInformationSetMCTSAgent[float]:
    agent = MultiObserverInformationSetMCTSAgent()
    agent.role = role
    agent.trees = {role: parent_with_even_child}
    return agent


def test_get_key_to_evaluation_single_state_single_move_child(
    state: State,
    move_loss: Move,
    agent_single_state_single_move: MultiObserverInformationSetMCTSAgent[float],
):
    agent = agent_single_state_single_move
    expected = {(state, move_loss): (float("-inf"), 500, 0.0)}

    actual = agent.get_key_to_evaluation()

    assert actual == expected


def test_get_key_to_evaluation_single_state_duo_move_child(
    state: State,
    move_loss: Move,
    move_win: Move,
    agent_single_state_duo_move: MultiObserverInformationSetMCTSAgent[float],
):
    agent = agent_single_state_duo_move
    expected = {(state, move_loss): (float("-inf"), 500, 0.0), (state, move_win): (float("-inf"), 500, 500.0)}

    actual = agent.get_key_to_evaluation()

    assert actual == expected


def test_get_key_to_evaluation_duo_state_single_move_child(
    state_loss: State,
    state_win: State,
    move_even: Move,
    agent_duo_state_single_move: MultiObserverInformationSetMCTSAgent[float],
):
    agent = agent_duo_state_single_move
    expected = {
        (state_win, move_even): (float("-inf"), 1000, 500.0),
        (state_loss, move_even): (float("-inf"), 1000, 500.0),
    }

    actual = agent.get_key_to_evaluation()

    assert actual == expected


def test_get_move_to_aggregation_single_state_single_move(state: State, move_loss: Move):
    agent = MultiObserverInformationSetMCTSAgent()
    expected = {move_loss: (float("-inf"), 500, 0.0)}

    actual = agent.get_move_to_evaluation({(state, move_loss): (float("-inf"), 500, 0.0)})

    assert actual == expected


def test_get_move_to_evaluation_multi_state_multi_move():
    agent = MultiObserverInformationSetMCTSAgent()

    state_unique = mock.Mock(spec=frozenset)
    state_ambiguous = mock.Mock(spec=frozenset)

    move_win = mock.Mock(spec=gdl.Subrelation)
    move_loss = mock.Mock(spec=gdl.Subrelation)

    expected = {
        move_loss: (float("-inf"), 500, 0.25),
        move_win: (float("-inf"), 500, 0.75),
    }

    actual = agent.get_move_to_evaluation(
        {
            (state_unique, move_loss): (float("-inf"), 500, 0.0),
            (state_unique, move_win): (float("-inf"), 500, 500.0),
            (state_ambiguous, move_win): (float("-inf"), 500, 250.0),
            (state_ambiguous, move_loss): (float("-inf"), 500, 250.0),
        },
    )

    assert actual == expected
