from typing import Self

from common import MockRetentionAgent, MockTimeoutAgent, SLEEP_TIME, mock_ruleset_1
from pyggp.commands import orchestrate_match
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import State, Relation
from pyggp.interpreters import ClingoInterpreter
from pyggp.match import MatchResult
from pyggp.visualizers import Visualizer


class _MockVisualizer(Visualizer):
    def __init__(self):
        super().__init__()
        self.update_state_count = 0
        self.update_result_count = 0
        self.update_abort_count = 0
        self.draw_count = 0

    def update_state(self, state: State, move_nr: int | None = None) -> None:
        super().update_state(state, move_nr)
        self.update_state_count += 1

    def update_result(self, result: MatchResult) -> None:
        self.update_result_count += 1

    def update_abort(self) -> None:
        self.update_abort_count += 1

    def draw(self) -> None:
        self.draw_count += 1


class _MockAgent(MockRetentionAgent):
    last_init: Self | None = None

    def __init__(self):
        super().__init__()
        self.next_move = 1
        _MockAgent.last_init = self


class _MockAgentIllegalMove(MockRetentionAgent):
    last_init: Self | None = None

    def __init__(self):
        super().__init__()
        self.next_move = 0
        _MockAgentIllegalMove.last_init = self


class _MockAgentTimeoutStart(MockRetentionAgent, MockTimeoutAgent):
    last_init: Self | None = None

    def __init__(self):
        super().__init__()
        self.timeout_prepare_match = True
        self.timeout_calculate_move = False
        self.timeout_abort_match = False
        self.timeout_conclude_match = False
        self.sleep_time = SLEEP_TIME * 1.1
        self.next_move = 1
        _MockAgentTimeoutStart.last_init = self


class _MockAgentTimeoutMove(MockRetentionAgent, MockTimeoutAgent):
    last_init: Self | None = None

    def __init__(self):
        super().__init__()
        self.timeout_prepare_match = False
        self.timeout_calculate_move = True
        self.timeout_abort_match = False
        self.timeout_conclude_match = False
        self.sleep_time = SLEEP_TIME * 1.1
        self.next_move = 1
        _MockAgentTimeoutMove.last_init = self


def test_as_expected() -> None:
    ruleset = mock_ruleset_1
    interpreter = ClingoInterpreter(ruleset)
    visualizer = _MockVisualizer()
    name_agenttype_map = {
        "mock_agent": _MockAgent,
    }
    role_agentname_map = {
        Relation("p1"): "mock_agent",
    }
    startclock_configs = {
        Relation("p1"): GameClockConfiguration(),
    }
    playclock_configs = {
        Relation("p1"): GameClockConfiguration(),
    }

    assert visualizer.update_state_count == 0
    assert visualizer.update_result_count == 0
    assert visualizer.update_abort_count == 0
    assert visualizer.draw_count == 0

    orchestrate_match(
        ruleset=ruleset,
        interpreter=interpreter,
        name_agenttypes_map=name_agenttype_map,
        role_agentname_map=role_agentname_map,
        startclock_configs=startclock_configs,
        playclock_configs=playclock_configs,
        visualizer=visualizer,
    )
    agent = _MockAgent.last_init
    assert agent.called_prepare_match
    assert agent.called_calc_move
    assert agent.called_conclude_match
    assert not agent.called_abort_match
    assert agent.move_nrs == [0]
    assert agent.views == [frozenset({Relation.control(Relation("p1"))})]
    assert agent.conclusion_view == frozenset({Relation("won")})

    assert visualizer.update_state_count == 4
    assert visualizer.update_result_count == 1
    assert visualizer.update_abort_count == 0
    assert visualizer.draw_count == 3


def test_as_expected_illegal_move() -> None:
    ruleset = mock_ruleset_1
    interpreter = ClingoInterpreter(ruleset)
    visualizer = _MockVisualizer()
    name_agenttype_map = {
        "mock_agent": _MockAgentIllegalMove,
    }
    role_agentname_map = {
        Relation("p1"): "mock_agent",
    }
    startclock_configs = {
        Relation("p1"): GameClockConfiguration(),
    }
    playclock_configs = {
        Relation("p1"): GameClockConfiguration(),
    }

    assert visualizer.update_state_count == 0
    assert visualizer.update_result_count == 0
    assert visualizer.update_abort_count == 0
    assert visualizer.draw_count == 0

    orchestrate_match(
        ruleset=ruleset,
        interpreter=interpreter,
        name_agenttypes_map=name_agenttype_map,
        role_agentname_map=role_agentname_map,
        startclock_configs=startclock_configs,
        playclock_configs=playclock_configs,
        visualizer=visualizer,
    )
    agent = _MockAgentIllegalMove.last_init
    assert agent.called_prepare_match
    assert agent.called_calc_move
    assert not agent.called_conclude_match
    assert agent.called_abort_match
    assert agent.move_nrs == [0]
    assert agent.views == [frozenset({Relation.control(Relation("p1"))})]
    assert agent.conclusion_view is None

    assert visualizer.update_state_count == 3
    assert visualizer.update_result_count == 1
    assert visualizer.update_abort_count == 1
    assert visualizer.draw_count == 3


def test_as_expected_timeout_start() -> None:
    ruleset = mock_ruleset_1
    interpreter = ClingoInterpreter(ruleset)
    visualizer = _MockVisualizer()
    name_agenttype_map = {
        "mock_agent": _MockAgentTimeoutStart,
    }
    role_agentname_map = {
        Relation("p1"): "mock_agent",
    }
    startclock_configs = {
        Relation("p1"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=SLEEP_TIME * 0.9),
    }
    playclock_configs = {
        Relation("p1"): GameClockConfiguration(),
    }

    assert visualizer.update_state_count == 0
    assert visualizer.update_result_count == 0
    assert visualizer.update_abort_count == 0
    assert visualizer.draw_count == 0

    orchestrate_match(
        ruleset=ruleset,
        interpreter=interpreter,
        name_agenttypes_map=name_agenttype_map,
        role_agentname_map=role_agentname_map,
        startclock_configs=startclock_configs,
        playclock_configs=playclock_configs,
        visualizer=visualizer,
    )
    agent = _MockAgentTimeoutStart.last_init
    assert agent.called_prepare_match
    assert not agent.called_calc_move
    assert not agent.called_conclude_match
    assert agent.called_abort_match
    assert agent.move_nrs == []
    assert agent.views == []

    assert visualizer.update_state_count == 0
    assert visualizer.update_result_count == 1
    assert visualizer.update_abort_count == 1
    assert visualizer.draw_count == 1


def test_as_expected_timeout_move() -> None:
    ruleset = mock_ruleset_1
    interpreter = ClingoInterpreter(ruleset)
    visualizer = _MockVisualizer()
    name_agenttype_map = {
        "mock_agent": _MockAgentTimeoutMove,
    }
    role_agentname_map = {
        Relation("p1"): "mock_agent",
    }
    startclock_configs = {
        Relation("p1"): GameClockConfiguration(),
    }
    playclock_configs = {
        Relation("p1"): GameClockConfiguration(total_time=0.0, increment=0.0, delay=SLEEP_TIME * 0.9),
    }

    assert visualizer.update_state_count == 0
    assert visualizer.update_result_count == 0
    assert visualizer.update_abort_count == 0
    assert visualizer.draw_count == 0

    orchestrate_match(
        ruleset=ruleset,
        interpreter=interpreter,
        name_agenttypes_map=name_agenttype_map,
        role_agentname_map=role_agentname_map,
        startclock_configs=startclock_configs,
        playclock_configs=playclock_configs,
        visualizer=visualizer,
    )
    agent = _MockAgentTimeoutMove.last_init
    assert agent.called_prepare_match
    assert agent.called_calc_move
    assert not agent.called_conclude_match
    assert agent.called_abort_match
    assert agent.move_nrs == [0]
    assert agent.views == [frozenset({Relation.control(Relation("p1"))})]

    assert visualizer.update_state_count == 3
    assert visualizer.update_result_count == 1
    assert visualizer.update_abort_count == 1
    assert visualizer.draw_count == 3
