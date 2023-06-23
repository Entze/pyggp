import abc
import collections
import logging
import random
import time
from dataclasses import dataclass, field
from typing import (
    FrozenSet,
    Generic,
    Mapping,
    MutableMapping,
    Optional,
    Tuple,
    TypeVar,
)

import pyggp.game_description_language as gdl
from pyggp._logging import format_amount, format_ns, format_rate_ns, log_time
from pyggp.agents.tree_agents.agents import ONE_S_IN_NS, AbstractTreeAgent, TreeAgent
from pyggp.agents.tree_agents.evaluators import Evaluator, final_goal_normalized_utility_evaluator
from pyggp.agents.tree_agents.mcts.evaluators import LightPlayoutEvaluator
from pyggp.agents.tree_agents.mcts.selectors import (
    Selector,
    UCTSelector,
)
from pyggp.agents.tree_agents.mcts.valuations import NormalizedUtilityValuation
from pyggp.agents.tree_agents.nodes import (
    HiddenInformationSetNode,
    ImperfectInformationNode,
    Node,
    PerfectInformationNode,
    VisibleInformationSetNode,
)
from pyggp.books import Book, BookBuilder
from pyggp.engine_primitives import Move, Role, State, Turn, View
from pyggp.gameclocks import GameClock
from pyggp.interpreters import Interpreter
from pyggp.repeaters import Repeater

log = logging.getLogger("pyggp")

_K = TypeVar("_K")

_BookValue = float
_Total_Playouts = int
_Utility = float
_MCTSEvaluation = Tuple[_BookValue, _Total_Playouts, _Utility]


class MonteCarloTreeSearchAgent(TreeAgent[_K, _MCTSEvaluation]):
    def step(self) -> None:
        ...


@dataclass
class AbstractMCTSAgent(AbstractTreeAgent[_K, _MCTSEvaluation], MonteCarloTreeSearchAgent[_K], Generic[_K], abc.ABC):
    def _move_evaluation_as_str(self, move: Move, evaluation: _MCTSEvaluation) -> str:
        book_value, total_playouts, utility = evaluation
        strs = [f"{move}: "]
        if self._can_lookup():
            strs.append(f"{book_value:.2f} | ")
        avg_utility = utility / total_playouts if total_playouts > 0 else 0.0
        strs.append(f"{avg_utility:.2f} @ ")
        strs.append(f"{format_amount(total_playouts)}")
        return "".join(strs)

    @abc.abstractmethod
    def _can_lookup(self) -> bool:
        raise NotImplementedError


class SingleObserverMonteCarloTreeSearchAgent(MonteCarloTreeSearchAgent[_K]):
    tree: Optional[Node[float, _K]]
    selector: Optional[Selector[float, _K]]
    evaluator: Optional[Evaluator[float]]
    repeater: Optional[Repeater[None]]
    book: Optional[Book[float]]


@dataclass
class AbstractSOMCTSAgent(AbstractMCTSAgent, SingleObserverMonteCarloTreeSearchAgent[_K], Generic[_K], abc.ABC):
    tree: Optional[Node[float, _K]] = field(default=None, repr=False)
    selector: Optional[Selector[float, _K]] = field(default=None, repr=False)
    evaluator: Optional[Evaluator[float]] = field(default=None, repr=False)
    repeater: Optional[Repeater[None]] = field(default=None, repr=False)
    book: Optional[Book[float]] = field(default=None, repr=False)

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        timeout_ns = startclock_config.total_time_ns + startclock_config.delay_ns + time.monotonic_ns()
        super().prepare_match(role, ruleset, startclock_config, playclock_config)
        assert self.interpreter is not None, "Assumption: interpreter is not None"
        assert self.role is not None, "Assumption: role is not None"

        self.tree = self._get_root()

        self.selector = UCTSelector(self.role)

        self.repeater = Repeater(func=self.step, timeout_ns=playclock_config.delay_ns, shortcircuit=self._can_lookup)

        timeout_ns -= time.monotonic_ns()
        self.book = self._build_book(timeout_ns=timeout_ns)
        self.evaluator = LightPlayoutEvaluator(
            role=self.role,
            final_state_evaluator=final_goal_normalized_utility_evaluator,
            book=self.book,
        )

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

    def _can_lookup(self) -> bool:
        return False

    def _build_book(self, timeout_ns: int) -> Book[float]:
        if timeout_ns < ONE_S_IN_NS:
            return {}
        build_time_ns = (timeout_ns * 9) // 10

        book_builder = BookBuilder(
            interpreter=self.interpreter,
            role=self.role,
            evaluator=final_goal_normalized_utility_evaluator,
            min_value=0.0,
            max_value=1.0,
        )

        def shortcircuit() -> bool:
            return book_builder.done

        book_building_repeater = Repeater(func=book_builder.step, timeout_ns=build_time_ns, shortcircuit=shortcircuit)

        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=f"Building book for at most {format_ns(build_time_ns)}",
            end_msg="Built book",
            abort_msg="Aborted building book",
        ):
            it, elapsed_time = book_building_repeater()
        log.info(
            "%s book with %s entries in %s (%s entries/s)",
            "Finished" if book_builder.done else "Built",
            format_amount(len(book_builder.book)),
            format_ns(elapsed_time),
            format_rate_ns(len(book_builder.book), elapsed_time),
        )
        return book_builder()

    def update(self, ply: int, view: View, total_time_ns: int) -> None:
        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=f"Developing {self._get_tree_log_representation(logging.DEBUG)}",
            end_msg="Developed tree",
            abort_msg="Aborted developing tree",
        ):
            self.tree = self.tree.develop(interpreter=self.interpreter, ply=ply, view=view)

    def search(self, search_time_ns: int) -> None:
        self.repeater.timeout_ns = search_time_ns
        with log_time(
            log,
            level=logging.DEBUG,
            begin_msg=f"Searching {self._get_tree_log_representation(logging.DEBUG)} "
            f"for at most {format_ns(search_time_ns)}",
            end_msg="Searched tree",
            abort_msg="Aborted searching tree",
        ):
            it, elapsed_ns = self.repeater()

        log.info("%s it in %s (%s it/s)", format_amount(it), format_ns(elapsed_ns), format_rate_ns(it, elapsed_ns))
        log.info("Current %s", self._get_tree_log_representation(logging.INFO))

    def _guess_remaining_moves(self) -> int:
        return self.tree.max_height

    def _get_tree_log_representation(self, log_level: int) -> str:
        if log_level < log.level:
            return "tree"
        return (
            "tree ("
            f"valuation={self.tree.valuation}, "
            f"depth={self.tree.depth}, "
            f"max_height={self.tree.max_height}, "
            f"avg_height={self.tree.avg_height:.2f}, "
            f"arity={self.tree.arity}, "
            f"fully_expanded={getattr(self.tree, 'fully_expanded', self.tree.children is not None)}, "
            f"transitions={len(self.tree.children or ())}, "
            f"fully_enumerated={getattr(self.tree, 'fully_enumerated', True)}, "
            f"possible_states={len(getattr(self.tree, 'possible_states', ((),)))}"
            ")"
        )


@dataclass
class MCTSAgent(AbstractSOMCTSAgent[Turn]):
    tree: Optional[PerfectInformationNode[float]] = field(default=None, repr=False)

    def _get_root(self) -> Node[float, Turn]:
        init_state = self.interpreter.get_init_state()
        return PerfectInformationNode(
            state=init_state,
        )

    def _can_lookup(self) -> bool:
        return self.book is not None and self.tree.state in self.book

    def descend(self, key: Turn) -> None:
        self.tree.expand(interpreter=self.interpreter)
        self.tree.turn = key
        self.tree.trim()
        self.tree = self.tree.children[key]

    def get_key_to_evaluation(self) -> Mapping[Turn, _MCTSEvaluation]:
        self.tree.expand(interpreter=self.interpreter)
        return {
            turn: (
                float("-inf") if not self._can_lookup() else self.book.get(child.state, float("-inf")),
                child.valuation.total_playouts
                if child.valuation is not None and hasattr(child.valuation, "total_playouts")
                else 0,
                child.valuation.utility if child.valuation is not None else 0.0,
            )
            for turn, child in self.tree.children.items()
        }

    def _get_move_to_aggregation(
        self,
        key_to_evaluation: Mapping[Turn, _MCTSEvaluation],
    ) -> Mapping[Move, _MCTSEvaluation]:
        return {self._key_to_move(turn): evaluation for turn, evaluation in key_to_evaluation.items()}

    def _key_to_move(self, key: Turn) -> Move:
        return key[self.role]


_Action = TypeVar("_Action", Turn, Move)


@dataclass
class SingleObserverInformationSetMCTSAgent(AbstractSOMCTSAgent[Tuple[State, _Action]]):
    tree: Optional[ImperfectInformationNode[float]] = field(default=None, repr=False)  # type: ignore[assignment]

    def update(self, ply: int, view: View, total_time_ns: int) -> None:
        used_time = time.monotonic_ns()
        super().update(ply=ply, view=view, total_time_ns=total_time_ns)
        used_time = time.monotonic_ns() - used_time
        fill_time_ns = self._get_timeout_ns(total_time_ns=total_time_ns, used_time=used_time, scale=0.5)
        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=f"Filling {self._get_tree_log_representation(logging.DEBUG)}",
            end_msg="Filled tree",
            abort_msg="Aborted filling tree",
        ):
            self._fill(ply=ply, view=view, fill_time_ns=fill_time_ns)

    def _fill(self, ply: int, view: View, fill_time_ns: int) -> None:
        __start = time.monotonic_ns()
        deltas = collections.deque(maxlen=5)
        deltas.extend((0, 0, 0, 0, 0))
        record = self.tree.gather_record(has_incomplete_information=self.interpreter.has_incomplete_information)
        possible_states = self.interpreter.get_possible_states(record=record, ply=ply)
        possible_state = next(possible_states, None)

        while possible_state is not None and time.monotonic_ns() - __start < fill_time_ns:
            self.tree.possible_states.add(possible_state)
            possible_state = next(possible_states, None)
        if possible_state is None:
            self.tree.fully_enumerated = True

    def step(self) -> None:
        node = self.tree
        determinization: State = random.choice(tuple(node.possible_states))

        while (
            node.children is not None
            and node.children
            and any(state == determinization for (state, _) in node.children)
            and not self.interpreter.is_terminal(determinization)
        ):
            key = self.selector(node=node, state=determinization)
            node = node.children[key]
            determinization = random.choice(tuple(node.possible_states))

        node.branch(interpreter=self.interpreter, state=determinization)

        utility = node.evaluate(
            interpreter=self.interpreter,
            evaluator=self.evaluator,
            valuation_factory=NormalizedUtilityValuation.from_utility,
            state=determinization,
        )

        while node.parent is not None:
            assert node.parent is not None, "Condition: node.parent is not None"
            node = node.parent
            if node.valuation is not None:
                node.valuation = node.valuation.propagate(utility)
            else:
                node.valuation = NormalizedUtilityValuation.from_utility(utility)

    def _get_root(self) -> Node[float, _K]:
        init_state = self.interpreter.get_init_state()
        roles_in_control = Interpreter.get_roles_in_control(init_state)
        if self.role not in roles_in_control:
            return HiddenInformationSetNode(possible_states={init_state}, role=self.role, fully_enumerated=True)
        else:
            view = self.interpreter.get_sees_by_role(init_state, self.role)
            return VisibleInformationSetNode(
                possible_states={init_state}, view=view, role=self.role, fully_enumerated=True
            )

    def _can_lookup(self) -> bool:
        return self.book is not None and all(state in self.book for state in self.tree.possible_states)

    def descend(self, key: Tuple[State, _Action]) -> None:
        state, move = key
        assert isinstance(move, gdl.Subrelation), "Assumption: action is a move"
        self.tree.branch(interpreter=self.interpreter, state=state)
        self.tree.move = move
        self.tree.trim()

    def get_key_to_evaluation(self) -> Mapping[Tuple[State, _Action], _MCTSEvaluation]:
        while not self.tree.children:
            determinization = random.choice(tuple(self.tree.possible_states))
            if self.interpreter.is_terminal(determinization):
                continue
            self.tree.branch(interpreter=self.interpreter, state=determinization)
        return {
            key: (
                float("-inf") if not self._can_lookup() else self._lookup(child),
                child.valuation.total_playouts
                if child.valuation is not None and hasattr(child.valuation, "total_playouts")
                else 0,
                child.valuation.utility if child.valuation is not None else 0.0,
            )
            for key, child in self.tree.children.items()
        }

    def _lookup(self, node: ImperfectInformationNode[float]) -> float:
        return sum(self.book.get(state, float("-inf")) for state in node.possible_states) / len(node.possible_states)

    def _get_move_to_aggregation(
        self,
        key_to_evaluation: Mapping[Tuple[State, _Action], _MCTSEvaluation],
    ) -> Mapping[Move, _MCTSEvaluation]:
        move_to_aggregated_book_value: MutableMapping[Move, float] = collections.defaultdict(float)
        move_to_total_playouts: MutableMapping[Move, int] = collections.defaultdict(int)
        move_to_utility: MutableMapping[Move, float] = collections.defaultdict(float)
        move_to_links: MutableMapping[Move, int] = collections.defaultdict(int)
        for (state, action), (book_value, total_playouts, utility) in key_to_evaluation.items():
            move_to_links[action] += 1
            move_to_aggregated_book_value[action] += book_value
            move_to_total_playouts[action] += total_playouts
            move_to_utility[action] += utility
        return {
            self._key_to_move(key): (
                move_to_aggregated_book_value[self._key_to_move(key)] / move_to_links[self._key_to_move(key)],
                move_to_total_playouts[self._key_to_move(key)],
                move_to_utility[self._key_to_move(key)],
            )
            for key in key_to_evaluation
        }

    def _key_to_move(self, key: Tuple[State, _Action]) -> Move:
        assert isinstance(key[1], gdl.Subrelation), "Assumption: key is (state, move)"
        return key[1]


class MultiObserverMonteCarloTreeSearchAgent(MonteCarloTreeSearchAgent[_K]):
    trees: Optional[MutableMapping[Role, Node[float, _K]]]
    roles: Optional[FrozenSet[Role]]
    selectors: Optional[Mapping[Role, Selector[float, _K]]]
    evaluators: Optional[Mapping[Role, Evaluator[float]]]
    repeater: Optional[Repeater]
    books: Optional[Mapping[Role, Book[float]]]


@dataclass
class MultiObserverInformationSetMCTSAgent(MultiObserverMonteCarloTreeSearchAgent[Tuple[State, Turn]]):
    pass
