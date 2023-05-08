import collections
import logging
import time
from dataclasses import dataclass, field
from typing import Final, MutableMapping, Optional, Set, Tuple, TypeVar

import pyggp.game_description_language as gdl
from pyggp._logging import compact_inflect, format_amount, format_timedelta
from pyggp.agents import InterpreterAgent
from pyggp.agents.tree_agents.evaluators import final_goal_normalized_utility_evaluator
from pyggp.agents.tree_agents.mcts.evaluators import LightPlayoutEvaluator
from pyggp.agents.tree_agents.mcts.selectors import (
    MonteCarloTreeSearchSelector,
    best_selector,
    most_selector,
    uct_selector,
)
from pyggp.agents.tree_agents.mcts.valuations import NormalizedUtilityValuation
from pyggp.agents.tree_agents.nodes import (
    HiddenInformationSetNode,
    ImperfectInformationNode,
    PerfectInformationNode,
    VisibleInformationSetNode,
)
from pyggp.agents.tree_agents.valuations import Valuation
from pyggp.engine_primitives import Move, Role, State, Turn, View
from pyggp.exceptions.agent_exceptions import (
    InterpreterIsNoneInterpreterAgentError,
    TreeIsNoneTreeAgentError,
)
from pyggp.gameclocks import GameClock
from pyggp.interpreters import Interpreter
from pyggp.repeaters import Repeater

log = logging.getLogger("pyggp")

_K = TypeVar("_K")
_U_co = TypeVar("_U_co", covariant=True)

ONE_S_IN_NS: Final[int] = 1_000_000_000


@dataclass
class MCTSAgent(InterpreterAgent):
    tree: Optional[PerfectInformationNode[float]] = field(default=None, repr=False)
    selector: Optional[MonteCarloTreeSearchSelector[float, Turn]] = field(default=None, repr=False)
    chooser: Optional[MonteCarloTreeSearchSelector[float, Turn]] = field(default=None, repr=False)
    evaluator: Optional[LightPlayoutEvaluator[float]] = field(default=None, repr=False)
    repeater: Optional[Repeater] = field(default=None, repr=False)

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        super().prepare_match(role, ruleset, startclock_config, playclock_config)
        assert (
            self.interpreter is not None
        ), "Assumption: interpreter is not None (super().prepare_match() should have set it)"

        init_state = self.interpreter.get_init_state()

        self.tree = PerfectInformationNode(
            state=init_state,
        )
        self.selector = uct_selector
        self.chooser = best_selector
        self.evaluator = LightPlayoutEvaluator(self.role, final_goal_normalized_utility_evaluator)
        self.repeater = Repeater(func=self.step, timeout_ns=playclock_config.delay_ns)

    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        if self.tree is None:
            raise TreeIsNoneTreeAgentError
        if self.interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError

        develop_start_ns = time.monotonic_ns()
        self.tree = self.tree.develop(interpreter=self.interpreter, ply=ply, view=view)
        develop_time_ns = time.monotonic_ns() - develop_start_ns
        log.debug("Developed tree in %s", format_timedelta(develop_time_ns * 1e-9))

        assert self.tree.depth == ply, "Assumption: tree.depth == ply"

        search_time_ns: int = max(
            int(self.playclock_config.delay_ns * 0.95),
            min(
                total_time_ns // 2,
                (self.playclock_config.delay_ns + self.playclock_config.increment_ns) - ONE_S_IN_NS,
            ),
        )

        self.repeater.timeout_ns = search_time_ns

        log.debug("Searching for %s", format_timedelta(search_time_ns / 1e9))
        nr_of_iterations, elapsed_ns = self.repeater()
        elapsed_s = elapsed_ns / 1e9
        log.info(
            "%s it in %s (%s it/s)",
            format_amount(nr_of_iterations),
            format_timedelta(elapsed_s),
            format_amount(nr_of_iterations / elapsed_s),
        )

        self._log_choices()

        key = self.chooser(self.tree)
        self.tree = self.tree.children[key]

        move = key[self.role]
        log.info("Selected %s: %s", move, self.tree.valuation)
        assert self.interpreter.is_legal(view, self.role, move), "Assumption: move is legal"

        return move

    def _log_choices(self) -> None:
        if log.level > logging.DEBUG:
            return
        move_to_valuation: MutableMapping[Move, Tuple[Valuation[float], ...]] = {}
        for key, child in self.tree.children.items():
            move = key[self.role]
            valuation = child.valuation
            if valuation is not None:
                move_to_valuation[move] = (valuation,)
            else:
                move_to_valuation[move] = ()

        sorted_moves = sorted(move_to_valuation, key=move_to_valuation.get, reverse=True)

        choice_dbg_log = []
        choice_dbg_log.append(f"Best options (out of {format_amount(len(move_to_valuation))}):")
        for move in sorted_moves[:5]:
            valuation = move_to_valuation[move]
            if valuation:
                choice_dbg_log.append(f"{move}: {valuation[0]}")

        log.debug("\n".join(choice_dbg_log))

    def step(self) -> None:
        node = self.tree
        while node.children:
            key = self.selector(node)
            node = node.children[key]

        # Expansion
        node.expand(self.interpreter)

        # Simulation
        utility = node.evaluate(
            interpreter=self.interpreter,
            evaluator=self.evaluator,
            valuation_factory=NormalizedUtilityValuation.from_utility,
        )

        assert 0 <= utility <= 1, f"Assumption: 0 <= utility <= 1 (utility is normalized)"

        # Backpropagation
        while node.parent is not None:
            node = node.parent
            if node.valuation is not None:
                node.valuation = node.valuation.propagate(utility)
            else:
                node.valuation = NormalizedUtilityValuation.from_utility(utility)


_A = TypeVar("_A", Turn, Move)


@dataclass
class SOISMCTSAgent(InterpreterAgent):
    tree: Optional[ImperfectInformationNode[float]] = field(default=None, repr=False)
    selector: Optional[MonteCarloTreeSearchSelector[float, Tuple[State, _A]]] = field(default=None, repr=False)
    chooser: Optional[MonteCarloTreeSearchSelector[float, Tuple[State, Move]]] = field(default=None, repr=False)
    evaluator: Optional[LightPlayoutEvaluator[float]] = field(default=None, repr=False)
    repeater: Optional[Repeater] = field(default=None, repr=False)

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        super().prepare_match(role, ruleset, startclock_config, playclock_config)
        assert (
            self.interpreter is not None
        ), "Assumption: interpreter is not None (super().prepare_match() should have set it)"

        init_state = self.interpreter.get_init_state()
        roles_in_control = Interpreter.get_roles_in_control(init_state)
        if self.role not in roles_in_control:
            self.tree = HiddenInformationSetNode(
                role=self.role,
                possible_states={init_state},
            )
        else:
            view = self.interpreter.get_sees_by_role(init_state, self.role)
            self.tree = VisibleInformationSetNode(
                view=view,
                role=self.role,
                possible_states={init_state},
            )

        self.selector = uct_selector
        self.chooser = most_selector
        self.evaluator = LightPlayoutEvaluator(self.role, final_goal_normalized_utility_evaluator)
        self.repeater = Repeater(func=self.step, timeout_ns=playclock_config.delay_ns)

    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        if self.tree is None:
            raise TreeIsNoneTreeAgentError
        if self.interpreter is None:
            raise InterpreterIsNoneInterpreterAgentError

        log.debug(
            "Developing tree (depth=%s, arity=%s, descendant_count=%s)",
            self.tree.depth,
            self.tree.arity,
            self.tree.descendant_count,
        )
        develop_start_ns = time.monotonic_ns()
        self.tree = self.tree.develop(interpreter=self.interpreter, ply=ply, view=view)
        develop_time_ns = time.monotonic_ns() - develop_start_ns
        log.debug(
            "Developed tree (depth=%s, arity=%s, descendant_count=%s) in %s",
            self.tree.depth,
            self.tree.arity,
            self.tree.descendant_count,
            format_timedelta(develop_time_ns / 1e9),
        )

        assert self.tree.depth == ply, "Assumption: tree.depth == ply"
        assert isinstance(self.tree, VisibleInformationSetNode), "Assumption: view implies VisibleInformationSetNode"
        assert self.tree.view == view, "Assumption: tree.view == view"
        assert self.tree.possible_states is None or all(
            self.role in Interpreter.get_roles_in_control(state) for state in self.tree.possible_states
        ), "Assumption: role is in control in possible_states"
        assert self.tree.children is None or all(
            self.role in Interpreter.get_roles_in_control(state) for state, _ in self.tree.children
        ), "Assumption: role is in control in states in children"
        assert self.tree.possible_states is None or all(
            self.interpreter.get_sees_by_role(state, self.role) == view for state in self.tree.possible_states
        ), "Assumption: view is consistent with possible_states"
        assert self.tree.children is None or all(
            self.interpreter.get_sees_by_role(state, self.role) == view for state, _ in self.tree.children
        ), "Assumption: view is consistent with states in children"

        search_time_ns: int = max(
            0,
            int(self.playclock_config.delay_ns * 0.95) - develop_time_ns,
            min(
                total_time_ns // 2,
                (self.playclock_config.delay_ns + self.playclock_config.increment_ns) - (ONE_S_IN_NS + develop_time_ns),
            ),
        )

        self.repeater.timeout_ns = search_time_ns

        log.debug("Searching for %s", format_timedelta(search_time_ns / 1e9))
        nr_of_iterations, elapsed_ns = self.repeater()
        elapsed_s = elapsed_ns / 1e9
        log.info(
            "%s it in %s (%s it/s)",
            format_amount(nr_of_iterations),
            format_timedelta(elapsed_s),
            format_amount(nr_of_iterations / elapsed_s),
        )

        self._log_choices()

        key = self.chooser(self.tree)
        state, move = key

        deterministic_child = sum(1 for _, m in self.tree.children if m == move) == 1
        log.info("Selected %s%s: %s", move, "*" if not deterministic_child else "", self.tree.children[key].valuation)
        self.tree.move = move
        if deterministic_child:
            self.tree = self.tree.children[key]
        log.debug(
            "Current tree depth=%s, arity=%s, descendant_count=%s",
            self.tree.depth,
            self.tree.arity,
            self.tree.descendant_count,
        )
        assert self.interpreter.get_sees_by_role(state, self.role) == view, (
            "Assumption: assumed state has given view "
            f"(state={'{'}{', '.join(str(elem) for elem in state)}{'}'}, "
            f"view={'{'}{', '.join(str(elem) for elem in view)}{'}'})"
        )
        assert self.interpreter.is_legal(view, self.role, move), (
            "Assumption: move is legal "
            f"(move: {move}, legal moves: {'{'}"
            f"{', '.join(str(move) for move in self.interpreter.get_legal_moves_by_role(view, self.role))})"
            f"{'}'}"
        )
        return move

    def _log_choices(self) -> None:
        if log.level > logging.DEBUG:
            return
        move_tp_map: MutableMapping[Move, int] = collections.defaultdict(int)
        move_utility_map: MutableMapping[Move, float] = collections.defaultdict(float)
        move_aps_map: MutableMapping[Move, Set[State]] = collections.defaultdict(set)
        for key, node in self.tree.children.items():
            _, move = key
            move_tp_map[move] += getattr(node.valuation, "total_playouts", 0)
            move_utility_map[move] += getattr(node.valuation, "utility", 0.0)
            move_aps_map[move].update(node.possible_states)
        sorted_moves = sorted(move_tp_map, key=move_tp_map.get, reverse=True)
        choice_dbg_log = []
        choice_dbg_log.append(
            f"Best options (out of {format_amount(len(move_tp_map.keys()))}, "
            f"{compact_inflect('possible state', len(self.tree.possible_states))}):",
        )
        for move in sorted_moves[:5]:
            total_playouts = move_tp_map[move]
            utility = move_utility_map[move]
            possible_states = move_aps_map[move]
            choice_dbg_log.append(
                f"{move} ({format_amount(len(possible_states))}): "
                f"{utility / total_playouts:.2f} @ {format_amount(total_playouts)}",
            )

        log.debug("\n".join(choice_dbg_log))

    def step(self) -> None:
        node = self.tree
        while node.children:
            key = self.selector(node)
            node = node.children[key]

        # Expansion
        node.expand(self.interpreter)

        # Simulation
        utility = node.evaluate(
            interpreter=self.interpreter,
            evaluator=self.evaluator,
            valuation_factory=NormalizedUtilityValuation.from_utility,
        )

        # Backpropagation
        while node.parent is not None:
            node = node.parent
            if node.valuation is not None:
                node.valuation = node.valuation.propagate(utility)
            else:
                node.valuation = NormalizedUtilityValuation.from_utility(utility)
