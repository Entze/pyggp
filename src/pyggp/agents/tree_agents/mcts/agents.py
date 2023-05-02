"""Agents that use Monte Carlo Tree Search to select moves."""
import logging
from dataclasses import dataclass, field
from typing import (
    Optional,
)

from pyggp import game_description_language as gdl
from pyggp._logging import format_amount, format_timedelta
from pyggp.agents import InterpreterAgent
from pyggp.agents.tree_agents.evaluators import NullEvaluator
from pyggp.agents.tree_agents.mcts.evaluators import LightPlayoutEvaluator
from pyggp.agents.tree_agents.mcts.nodes import DeterministicMCTSNode
from pyggp.agents.tree_agents.mcts.valuations import PlayoutValuation
from pyggp.agents.tree_agents.perspectives import DeterministicPerspective
from pyggp.exceptions.agent_exceptions import (
    InterpreterIsNoneInterpreterAgentError,
    PlayclockConfigurationIsNoneAgentError,
    PlayclockIsNoneMCTSAgentError,
    RoleIsNoneAgentError,
    RootIsNoneMCTSAgentError,
)
from pyggp.gameclocks import GameClock
from pyggp.interpreters import Move, Role, View

log: logging.Logger = logging.getLogger("pyggp")


@dataclass
class DeterministicMCTSAgent(InterpreterAgent):
    """An agent that can be used in Deterministic games that uses Monte Carlo Tree Search to select moves."""

    @dataclass
    class Node(DeterministicMCTSNode[DeterministicPerspective, PlayoutValuation]):
        """A DeterministicMCTSNode that uses DeterministicPerspectives and PlayoutValuations."""

        perspective_type = DeterministicPerspective
        valuation_type = PlayoutValuation
        default_evaluator = NullEvaluator(valuation_type)

    root: Optional[Node] = field(default=None)
    play_clock: Optional[GameClock] = field(default=None)

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        """Prepares the agent for a match.

        Args:
            role: Role of the agent
            ruleset: Ruleset of the match
            startclock_config: Configuration of startclock
            playclock_config: Configuration of playclock

        """
        super().prepare_match(role, ruleset, startclock_config, playclock_config)
        assert self.interpreter is not None, "Assumption: Calling super implies self._interpreter is not None"
        init_state = self.interpreter.get_init_state()
        self.root = DeterministicMCTSAgent.Node.from_state(state=init_state)
        self.play_clock = GameClock.from_configuration(playclock_config)

    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        """Calculates the next move.

        Args:
            ply: Current ply
            total_time_ns: Total time on the playclock in nanoseconds (without delay)
            view: Current view

        Returns:
            Move

        """
        if self.interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError
        if self.role is None:
            raise RoleIsNoneAgentError
        if self.root is None:
            raise RootIsNoneMCTSAgentError
        if self.playclock_config is None:
            raise PlayclockConfigurationIsNoneAgentError
        if self.play_clock is None:
            raise PlayclockIsNoneMCTSAgentError
        delay = self.playclock_config.delay
        self.play_clock.total_time_ns = total_time_ns
        deltas = 0.0
        with self.play_clock:
            self.root = self.root.develop(self.interpreter, ply, view)
        delta = self.play_clock.last_delta
        assert delta is not None, "Assumption: After with statement implies self.play_clock.last_delta is not None."
        develop_time = delta
        log.info("Developed node in [green]%s[/green].", format_timedelta(develop_time), extra={"highlighter": None})
        if self.root.valuation is not None:
            log.info("Valuation: %s", self.root.valuation.__rich__(), extra={"highlighter": None})
        deltas += delta
        before = self.root.valuation.total_playouts if self.root.valuation is not None else 0
        while deltas < (delay * 0.95):
            with self.play_clock:
                self.root.search(self.interpreter, evaluator=LightPlayoutEvaluator(self.role))
            delta = self.play_clock.last_delta
            assert delta is not None, "Assumption: After with statement implies self.play_clock.last_delta is not None."
            deltas += delta
        assert self.root.is_expanded, "Assumption: self.root.is_expanded after self.root.search."
        assert (
            self.root.children is not None
        ), "Assumption: self.root.is_expanded implies self.root.children is not None."
        assert self.root.valuation is not None, "Assumption: self.root.valuation is not None after self.root.search."
        after = self.root.valuation.total_playouts
        search_time = deltas - develop_time
        log.info(
            "Iterated [orange1]%s[/orange1] times in [green]%s[/green] ([red]%s[/red] it/s).",
            format_amount(after - before),
            format_timedelta(search_time),
            format_amount((after - before) / search_time),
            extra={"highlighter": None},
        )
        if self.root.valuation is not None:
            log.info("Root valuation:  %s", self.root.valuation.__rich__(), extra={"highlighter": None})
        key = self.root.choose()
        assert key in self.root.children, "Assumption: Key is in self.root.children."
        childs_valuation = self.root.children[key].valuation
        if childs_valuation is not None:
            log.info("Child valuation: %s", childs_valuation.__rich__(), extra={"highlighter": None})
        assert self.role in key, "Assumption: Role is in Turn."
        return key[self.role]
