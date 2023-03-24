# pylint: disable=missing-docstring,invalid-name,unused-argument

import pytest
from common import (
    MockAgent,
    MockRetentionAgent,
    MockRuleset1Interpreter,
    MockRuleset2Interpreter,
    MockRuleset3Interpreter,
    MockTimeoutAgent,
    mock_match,
    mock_ruleset_1,
    mock_ruleset_2,
    mock_ruleset_3,
)
from pyggp.exceptions.match_exceptions import IllegalMoveMatchError, TimeoutMatchError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Relation, State


@pytest.mark.skip
@pytest.mark.parametrize(
    "move,expected_state",
    [
        (1, frozenset({Relation("won")})),
        (2, frozenset({Relation("lost")})),
        (3, frozenset({Relation.control(Relation("p1"))})),
    ],
)
def test_as_expected_legal_move(move: int, expected_state: State) -> None:
    agent = MockAgent()
    match = mock_match(ruleset=mock_ruleset_1, interpreter=MockRuleset1Interpreter(), agents=(agent,))

    agent.next_move = move

    assert len(match.states) == 1
    assert match.states[0] == {Relation.control(Relation("p1"))}
    match.execute_ply()
    assert len(match.states) == 2
    assert match.states[0] == {Relation.control(Relation("p1"))}
    assert match.states[1] == expected_state


@pytest.mark.skip
def test_as_expected_passes_state() -> None:
    agent_p1 = MockRetentionAgent()
    agent_p2 = MockRetentionAgent()
    match = mock_match(ruleset=mock_ruleset_2, interpreter=MockRuleset2Interpreter(), agents=(agent_p1, agent_p2))

    assert len(match.states) == 1
    assert match.states[-1] == {Relation.control(Relation("p1"))}

    agent_p1.next_move = 3

    match.execute_ply()

    assert len(match.states) == 2
    assert match.states[-1] == {Relation.control(Relation("p1"))}

    assert agent_p1.move_nrs == [0]
    assert agent_p1.views == [match.states[-2]]

    assert agent_p2.move_nrs == []
    assert agent_p2.views == []

    agent_p1.next_move = 4

    match.execute_ply()

    assert len(match.states) == 3
    assert match.states[-1] == {Relation.control(Relation("p2"))}

    assert agent_p1.move_nrs == [0, 1]
    assert agent_p1.views == [match.states[-3], match.states[-2]]

    assert agent_p2.move_nrs == []
    assert agent_p2.views == []

    agent_p2.next_move = 1

    match.execute_ply()

    assert len(match.states) == 4
    assert match.states[-1] == {Relation("won", (Relation("p2"),))}

    assert agent_p1.move_nrs == [0, 1]
    assert agent_p1.views == [match.states[-4], match.states[-3]]

    assert agent_p2.move_nrs == [2]
    assert agent_p2.views == [match.states[-2]]


@pytest.mark.skip
def test_raises_on_illegal_move() -> None:
    agent = MockAgent()
    match = mock_match(ruleset=mock_ruleset_1, interpreter=MockRuleset1Interpreter(), agents=(agent,))

    agent.next_move = 4

    assert len(match.states) == 1
    assert match.states[0] == {Relation.control(Relation("p1"))}
    with pytest.raises(ExceptionGroup) as excinfo:
        match.execute_ply()
    assert len(excinfo.value.exceptions) == 1
    assert isinstance(excinfo.value.exceptions[0], IllegalMoveMatchError)
    assert len(match.states) == 1
    assert match.states[0] == {Relation.control(Relation("p1"))}
    assert match.utilities == {Relation("p1"): "DNF(Illegal Move)"}


@pytest.mark.skip
@pytest.mark.parametrize(
    "slack,sleep_time,delay",
    [
        (0.0, 0.2, 0.0),
        (0.0, 0.2, 0.1),
        (0.1, 0.2, 0.0),
        (0.1, 0.2, 0.1),
        (0.2, 0.2, 0.0),
        (0.2, 0.2, 0.1),
    ],
)
def test_raises_on_timeout(slack: float, sleep_time: float, delay: float) -> None:
    agent = MockTimeoutAgent(
        timeout_prepare_match=False,
        timeout_calculate_move=True,
        timeout_abort_match=False,
        timeout_conclude_match=False,
        sleep_time=sleep_time,
    )
    playclock_configs = {
        Relation("p1"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=delay),
    }
    match = mock_match(
        ruleset=mock_ruleset_1,
        interpreter=MockRuleset1Interpreter(),
        agents=(agent,),
        playclock_configs=playclock_configs,
        slack=slack,
    )

    assert len(match.states) == 1
    assert match.states[0] == {Relation.control(Relation("p1"))}
    with pytest.raises(ExceptionGroup) as excinfo:
        match.execute_ply()
    assert len(excinfo.value.exceptions) == 1
    assert isinstance(excinfo.value.exceptions[0], TimeoutMatchError)
    assert len(match.states) == 1
    assert match.states[0] == {Relation.control(Relation("p1"))}
    assert match.utilities == {Relation("p1"): "DNF(Timeout)"}


@pytest.mark.skip
def test_raises_on_multi_timeout() -> None:
    agent_p1 = MockTimeoutAgent(
        timeout_prepare_match=False,
        timeout_calculate_move=True,
        timeout_abort_match=False,
        timeout_conclude_match=False,
        sleep_time=0.1,
    )
    agent_p2 = MockTimeoutAgent(
        timeout_prepare_match=False,
        timeout_calculate_move=True,
        timeout_abort_match=False,
        timeout_conclude_match=False,
        sleep_time=0.2,
    )
    agent_p3 = MockTimeoutAgent(
        timeout_prepare_match=False,
        timeout_calculate_move=True,
        timeout_abort_match=False,
        timeout_conclude_match=False,
        sleep_time=0.1,
    )
    playclock_configs = {
        Relation("p1"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=0.1),
        Relation("p2"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=0.1),
        Relation("p3"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=0.1),
    }

    agent_p1.next_move = Relation("dibs")
    agent_p2.next_move = Relation("dibs")
    agent_p3.next_move = Relation("dibs")

    match = mock_match(
        ruleset=mock_ruleset_3,
        interpreter=MockRuleset3Interpreter(),
        agents=(agent_p1, agent_p2, agent_p3),
        playclock_configs=playclock_configs,
        slack=0.0,
    )

    with pytest.raises(ExceptionGroup) as excinfo:
        match.execute_ply()

    assert len(excinfo.value.exceptions) == 3
    assert isinstance(excinfo.value.exceptions[0], TimeoutMatchError)
    assert isinstance(excinfo.value.exceptions[1], TimeoutMatchError)
    assert isinstance(excinfo.value.exceptions[2], TimeoutMatchError)
