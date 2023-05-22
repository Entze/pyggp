import abc
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Final, Generic, Mapping, MutableMapping, Optional, Set, Tuple, TypeVar, Union

import pyggp.game_description_language as gdl
from pyggp._logging import format_amount, format_ns, format_rate_ns, log_time
from pyggp.agents import InterpreterAgent
from pyggp.agents.tree_agents.evaluators import Evaluator, final_goal_normalized_utility_evaluator
from pyggp.agents.tree_agents.mcts.evaluators import LightPlayoutEvaluator
from pyggp.agents.tree_agents.mcts.selectors import (
    Selector,
    most_selector,
    uct_selector,
)
from pyggp.agents.tree_agents.mcts.valuations import NormalizedUtilityValuation
from pyggp.agents.tree_agents.nodes import (
    HiddenInformationSetNode,
    ImperfectInformationNode,
    Node,
    PerfectInformationNode,
    VisibleInformationSetNode,
)
from pyggp.engine_primitives import Move, Role, State, Turn, View
from pyggp.gameclocks import GameClock
from pyggp.interpreters import Interpreter
from pyggp.repeaters import Repeater

log = logging.getLogger("pyggp")

_K = TypeVar("_K")

ONE_S_IN_NS: Final[int] = 1_000_000_000
MAX_LOGGED_OPTIONS: Final[int] = 5


@dataclass
class SingleObserverMonteCarloTreeSearchAgent(InterpreterAgent, Generic[_K], abc.ABC):
    tree: Optional[Node[float, _K]] = field(default=None, repr=False)
    selector: Optional[Selector[float, _K]] = field(default=None, repr=False)
    chooser: Optional[Selector[float, _K]] = field(default=None, repr=False)
    evaluator: Optional[Evaluator[float]] = field(default=None, repr=False)
    repeater: Optional[Repeater] = field(default=None, repr=False)

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        super().prepare_match(role, ruleset, startclock_config, playclock_config)
        assert self.interpreter is not None, "Assumption: interpreter is not None"
        assert self.role is not None, "Assumption: role is not None"

        self.tree = self._get_root()

        self.selector = uct_selector
        self.chooser = most_selector
        self.evaluator = LightPlayoutEvaluator(self.role, final_goal_normalized_utility_evaluator)
        self.repeater = Repeater(func=self.step, timeout_ns=playclock_config.delay_ns)

    @abc.abstractmethod
    def _get_root(self) -> Node[float, _K]:
        raise NotImplementedError

    def step(self) -> None:
        assert self.tree is not None, "Requirement: tree is not None"
        assert self.selector is not None, "Requirement: selector is not None"
        assert self.interpreter is not None, "Requirement: interpreter is not None"
        assert self.evaluator is not None, "Requirement: evaluator is not None"
        node = self.tree

        while node.children:
            key = self.selector(node)
            node = node.children[key]

        node.expand(self.interpreter)

        utility = node.evaluate(
            interpreter=self.interpreter,
            evaluator=self.evaluator,
            valuation_factory=NormalizedUtilityValuation.from_utility,
        )

        while node.parent is not None:
            assert node.parent is not None, "Condition: node.parent is not None"
            node = node.parent
            if node.valuation is not None:
                node.valuation = node.valuation.propagate(utility)
            else:
                node.valuation = NormalizedUtilityValuation.from_utility(utility)

    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        total_time_ns += time.monotonic_ns()
        assert self.interpreter is not None, "Requirement: interpreter is not None"
        assert self.tree is not None, "Requirement: tree is not None"
        assert self.selector is not None, "Requirement: selector is not None"
        assert self.chooser is not None, "Requirement: chooser is not None"
        assert self.evaluator is not None, "Requirement: evaluator is not None"
        assert self.repeater is not None, "Requirement: repeater is not None"

        with log_time(
            log,
            level=logging.DEBUG,
            begin_msg="Developing tree ("
            f"depth={self.tree.depth}, "
            f"valuation={self.tree.valuation}, "
            f"arity={self.tree.arity}, "
            f"descendant_count={format_amount(self.tree.descendant_count)}"
            ")",
            end_msg="Developed tree",
            abort_msg="Aborted developing tree",
        ):
            self.tree = self.tree.develop(interpreter=self.interpreter, ply=ply, view=view)

        assert self.tree.depth == ply, "Assumption: tree.depth == ply"

        total_time_ns -= time.monotonic_ns()

        search_time_ns: int = self._get_search_time_ns(total_time_ns)

        self.repeater.timeout_ns = search_time_ns
        with log_time(
            log,
            level=logging.DEBUG,
            begin_msg="Searching tree ("
            f"depth={self.tree.depth}, "
            f"valuation={self.tree.valuation}, "
            f"arity={self.tree.arity}, "
            f"descendant_count={format_amount(self.tree.descendant_count)}"
            f") for at most {format_ns(search_time_ns)}",
            end_msg="Searched tree",
            abort_msg="Aborted searching tree",
        ):
            it, elapsed_ns = self.repeater()

        log.info("%s it in %s (%s it/s)", format_amount(it), format_ns(elapsed_ns), format_rate_ns(it, elapsed_ns))

        self._log_options()

        key = self.chooser(self.tree)

        move = self._get_move_from_key(key)
        assert self.tree.children is not None, "Assumption: tree.children is not None (tree is expanded)"
        self.tree = self.tree.children[key]
        log.info("Chose %s (%s)", move, self.tree.valuation)

        return move

    def _get_search_time_ns(self, total_time_ns: int, slack: float = 0.99) -> int:
        assert self.playclock_config is not None, "Requirement: playclock_config is not None"
        effective_delay_ns: int = max(
            0,
            self.playclock_config.delay_ns - ONE_S_IN_NS,
            int(self.playclock_config.delay_ns * slack),
        )
        net_zero_time_ns: int = self.playclock_config.increment_ns + self.playclock_config.delay_ns
        effective_net_zero_time_ns: int = max(0, net_zero_time_ns - ONE_S_IN_NS, int(net_zero_time_ns * 0.99))

        search_time_ns: int = max(
            effective_delay_ns,
            min(
                effective_net_zero_time_ns,
                int(total_time_ns * slack),
            ),
        )
        return search_time_ns

    def _log_options(self) -> None:
        if log.level > logging.DEBUG:
            return
        options = self._get_options()

        def key(move: Move) -> Union[Tuple[float, int, int], Tuple[()]]:
            return options.get(move, ())

        sorted_moves = sorted(options, key=key, reverse=True)
        msg = [f"Options (out of {len(options)}):"]
        for option in sorted_moves[:MAX_LOGGED_OPTIONS]:
            utility, total_playouts, nr_of_target_states = options[option]
            msg.append(
                f"{option}{(' (%d)' % nr_of_target_states) if nr_of_target_states != 1 else ''}: "
                f"{(utility / total_playouts):.2f} @ {format_amount(total_playouts)}",
            )
        log.debug("\n".join(msg))

    @abc.abstractmethod
    def _get_options(self) -> Mapping[Move, Tuple[float, int, int]]:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_move_from_key(self, key: _K) -> Move:
        raise NotImplementedError


@dataclass
class MCTSAgent(SingleObserverMonteCarloTreeSearchAgent[Turn]):
    tree: Optional[PerfectInformationNode[float]] = field(default=None, repr=False)
    evaluator: Optional[LightPlayoutEvaluator[float]] = field(default=None, repr=False)

    def _get_root(self) -> PerfectInformationNode[float]:
        assert self.interpreter is not None, "Requirement: interpreter is not None"
        init_state = self.interpreter.get_init_state()

        return PerfectInformationNode(
            state=init_state,
        )

    def _get_options(self) -> Mapping[Move, Tuple[float, int, int]]:
        assert self.tree is not None, "Requirement: tree is not None"
        assert self.tree.children is not None, "Assumption: tree.children is not None"
        return {
            self._get_move_from_key(key): (
                child.valuation.utility if child.valuation is not None else 0.0,
                getattr(child.valuation, "total_playouts", 0) if child.valuation is not None else 0,
                1,
            )
            for key, child in self.tree.children.items()
        }

    def _get_move_from_key(self, key: Turn) -> Move:
        assert self.role is not None, "Requirement: role is not None"
        assert self.role in key, f"Assumption: role in key, (role={self.role}, key={key}"
        return key[self.role]


_A = TypeVar("_A", Turn, Move)


@dataclass
class SingleObserverInformationSetMCTSAgent(SingleObserverMonteCarloTreeSearchAgent[Tuple[State, _A]]):
    tree: Optional[ImperfectInformationNode[float]] = field(default=None, repr=False)  # type: ignore[assignment]
    evaluator: Optional[LightPlayoutEvaluator[float]] = field(default=None, repr=False)

    def _get_root(self) -> ImperfectInformationNode[float]:  # type: ignore[override]
        assert self.interpreter is not None, "Requirement: interpreter is not None"
        assert self.role is not None, "Requirement: role is not None"
        init_state = self.interpreter.get_init_state()
        roles_in_control = Interpreter.get_roles_in_control(init_state)
        node: ImperfectInformationNode[float]
        if self.role not in roles_in_control:
            node = HiddenInformationSetNode(
                role=self.role,
                possible_states={init_state},
            )
        else:
            view = self.interpreter.get_sees_by_role(init_state, self.role)
            node = VisibleInformationSetNode(
                role=self.role,
                view=view,
                possible_states={init_state},
            )
        return node

    def _get_options(self) -> Mapping[Move, Tuple[float, int, int]]:
        assert self.tree is not None, "Requirement: tree is not None"
        assert self.tree.children is not None, "Assumption: tree.children is not None (tree is expanded)"
        assert isinstance(self.tree, VisibleInformationSetNode), "Assumption: tree is VisibleInformationSetNode"
        move_to_utility: MutableMapping[Move, float] = defaultdict(float)
        move_to_tp: MutableMapping[Move, int] = defaultdict(int)
        move_to_ps: MutableMapping[Move, Set[State]] = defaultdict(set)
        for key, child in self.tree.children.items():
            _, move = key
            move_to_utility[move] += child.valuation.utility if child.valuation is not None else 0.0
            move_to_tp[move] += getattr(child.valuation, "total_playouts", 0) if child.valuation is not None else 0
            move_to_ps[move].update(child.possible_states)
        return {move: (move_to_utility[move], move_to_tp[move], len(move_to_ps[move])) for move in move_to_utility}

    def _get_move_from_key(self, key: Tuple[State, _A]) -> Move:
        state, edge = key
        if isinstance(edge, Turn):
            assert self.role is not None, "Requirement: role is not None"
            assert self.role in edge, "Assumption: role in edge"
            return edge[self.role]
        return edge
