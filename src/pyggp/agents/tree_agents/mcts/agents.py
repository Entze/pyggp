import abc
import collections
import logging
import time
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    FrozenSet,
    Generic,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    ParamSpec,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from typing_extensions import Self

import pyggp.game_description_language as gdl
from pyggp._logging import format_amount, format_id, format_ns, format_rate_ns, log_time, rich
from pyggp.agents import InterpreterAgent
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
from pyggp.cli.argument_specification import ArgumentSpecification
from pyggp.engine_primitives import Move, Role, State, Turn, View
from pyggp.gameclocks import GameClock
from pyggp.interpreters import ClingoInterpreter, Interpreter
from pyggp.records import ImperfectInformationRecord, PerfectInformationRecord, Record
from pyggp.repeaters import Repeater

log = logging.getLogger("pyggp")

_K = TypeVar("_K")

_BookValue = float
_Total_Playouts = int
_Utility = float
_MCTSEvaluation = Tuple[_BookValue, _Total_Playouts, _Utility]


class MonteCarloTreeSearchAgent(TreeAgent[_K, _MCTSEvaluation]):
    step_repeater: Optional[Repeater[None]]
    max_mcts_iterations: Optional[int]
    max_expansion_depth: Optional[int]

    def step(self) -> None:
        ...


_P = ParamSpec("_P")


@dataclass
class AbstractMCTSAgent(AbstractTreeAgent[_K, _MCTSEvaluation], MonteCarloTreeSearchAgent[_K], Generic[_K], abc.ABC):
    max_mcts_iterations: Optional[int] = field(default=None, repr=False)
    max_expansion_depth: Optional[int] = field(default=None, repr=False)
    selector_factory: Callable[_P, Selector[float, _K]] = field(default=UCTSelector, repr=False)
    skip_book: bool = field(default=False, repr=False)

    @classmethod
    def from_cli(
        cls,
        max_mcts_iterations: Union[str, int, None] = None,
        max_expansion_depth: Union[str, int, None] = None,
        interpreter: Optional[str] = None,
        selector: Optional[str] = None,
        skip_book: Union[str, bool] = False,
        *args: str,
        **kwargs: str,
    ) -> Self:
        interpreter_factory = (
            InterpreterAgent.interpreter_factory_from_spec_str(interpreter)
            if interpreter is not None
            else ClingoInterpreter.from_ruleset
        )
        selector_factory = ArgumentSpecification.get_factory_from_str(selector) if selector is not None else UCTSelector
        if isinstance(max_mcts_iterations, str):
            max_mcts_iterations = int(max_mcts_iterations)
        if isinstance(max_expansion_depth, str):
            max_expansion_depth = int(max_expansion_depth)
        if isinstance(skip_book, str):
            skip_book = skip_book.casefold() in ("true", "1")
        return cls(
            *args,
            interpreter_factory=interpreter_factory,
            selector_factory=selector_factory,
            max_mcts_iterations=max_mcts_iterations,
            max_expansion_depth=max_expansion_depth,
            skip_book=skip_book,
            **kwargs,
        )

    def __rich__(self) -> str:
        id_str = f"id={format_id(self)}"
        interpreter_str = f"interpreter={rich(self.interpreter)}"
        interpreter_factory_str = f"interpreter_factory={rich(self.interpreter_factory)}"
        selector_factory_str = f"selector_factory={rich(self.selector_factory)}"
        max_mcts_iterations_str = f"max_mcts_iterations={rich(self.max_mcts_iterations)}"
        max_expansion_depth_str = f"max_expansion_depth={rich(self.max_expansion_depth)}"
        attributes_str = ", ".join(
            (
                id_str,
                interpreter_str,
                interpreter_factory_str,
                selector_factory_str,
                max_mcts_iterations_str,
                max_expansion_depth_str,
            )
        )
        return f"{self.__class__.__name__}({attributes_str})"

    def search(self, search_time_ns: int) -> None:
        self.step_repeater.timeout_ns = search_time_ns
        with log_time(
            log,
            logging.DEBUG,
            begin_msg=f"Starting MCTS at {rich(self.get_main_tree(logging.DEBUG))} for at most "
            f"{format_ns(search_time_ns)}",
            end_msg="Ended MCTS",
            abort_msg="Aborted MCTS",
        ):
            it, elapsed_ns = self.step_repeater()

        log.info(
            "Concluded MCTS after %s it in %s (%s it/s)",
            format_amount(it),
            format_ns(elapsed_ns),
            format_rate_ns(it, elapsed_ns),
        )
        log.info("Choosing move at %s", rich(self.get_main_tree(logging.INFO)))

    def _evaluation_as_str(self, evaluation: _MCTSEvaluation) -> str:
        book_value, total_playouts, utility = evaluation
        strs = []
        if self._can_lookup():
            strs.append(f"{book_value:.2f} | ")
        avg_utility = utility / total_playouts if total_playouts > 0 else 0.0
        strs.append(f"{avg_utility:.2f} @ ")
        strs.append(f"{format_amount(total_playouts)}")
        return "".join(strs)

    def _can_lookup(self) -> bool:
        return False

    @abc.abstractmethod
    def _lookup(self, key: Optional[_K] = None) -> float:
        raise NotImplementedError

    @abc.abstractmethod
    def get_main_tree(self, target_log_level: int) -> Optional[Node[float, _K]]:
        raise NotImplementedError


class SingleObserverMonteCarloTreeSearchAgent(MonteCarloTreeSearchAgent[_K]):
    tree: Optional[Node[float, _K]]
    selector: Optional[Selector[float, _K]]
    evaluator: Optional[Evaluator[float]]
    book: Optional[Book[float]]


@dataclass
class AbstractSOMCTSAgent(AbstractMCTSAgent, SingleObserverMonteCarloTreeSearchAgent[_K], Generic[_K], abc.ABC):
    tree: Optional[Node[float, _K]] = field(default=None, repr=False)
    selector: Optional[Selector[float, _K]] = field(default=None, repr=False)
    evaluator: Optional[Evaluator[float]] = field(default=None, repr=False)
    step_repeater: Optional[Repeater[None]] = field(default=None, repr=False)
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

        self.selector = self.selector_factory(role=self.role)

        self.step_repeater = Repeater(
            func=self.step,
            timeout_ns=playclock_config.delay_ns,
            max_repeats=self.max_mcts_iterations,
            shortcircuit=self._can_lookup,
            slack=1.5,
        )

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
        ply = node.depth

        while node.children and (
            self.max_expansion_depth is None or (node.depth - ply) < (self.max_expansion_depth - 1)
        ):
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
        if timeout_ns < 10 * ONE_S_IN_NS or self.skip_book:
            return {}
        build_time_ns = (timeout_ns * 9) // 10

        book_builder = BookBuilder(
            interpreter=self.interpreter,
            role=self.role,
            evaluator=final_goal_normalized_utility_evaluator,
            min_value=0.0,
            max_value=1.0,
        )

        book_building_repeater = Repeater(
            func=book_builder.step,
            timeout_ns=build_time_ns,
            shortcircuit=book_builder.is_done,
        )

        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=f"Building book from perspective {rich(self.role)} for at most {format_ns(build_time_ns)}",
            end_msg=f"Built book from perspective {rich(self.role)}",
            abort_msg="Aborted building book",
        ):
            it, elapsed_time = book_building_repeater()
        log.info(
            "%s book from perspecitve %s with %s entries in %s (%s entries/s)",
            "Finished" if book_builder.done else "Built",
            rich(self.role),
            format_amount(len(book_builder.book)),
            format_ns(elapsed_time),
            format_rate_ns(len(book_builder.book), elapsed_time),
        )
        return book_builder()

    def update(self, ply: int, view: View, total_time_ns: int) -> None:
        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=f"Developing at {rich(self.get_main_tree(logging.DEBUG))}",
            end_msg="Developed to current ply and view",
            abort_msg="Aborted developing",
        ):
            self.tree = self.tree.develop(interpreter=self.interpreter, ply=ply, view=view)

    def _guess_remaining_moves(self) -> int:
        return self.tree.max_height


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

    def _lookup(self, key: Optional[Turn] = None) -> float:
        node = self.tree.children[key] if key is not None else self.tree
        return self.book.get(node.state, float("-inf"))

    def descend(self, key: Turn) -> None:
        self.tree.expand(interpreter=self.interpreter)
        self.tree.turn = key
        self.tree.trim()
        self.tree = self.tree.children[key]

    def get_key_to_evaluation(self) -> Mapping[Turn, _MCTSEvaluation]:
        self.tree.expand(interpreter=self.interpreter)
        return {
            turn: (
                float("-inf") if not self._can_lookup() else self._lookup(turn),
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

    def get_main_tree(self, target_log_level: int) -> Optional[Node[float, _K]]:
        if log.level > target_log_level:
            return None
        return self.tree


_Action = TypeVar("_Action", Turn, Move)


@dataclass
class SingleObserverInformationSetMCTSAgent(AbstractSOMCTSAgent[Tuple[State, _Action]]):
    tree: Optional[ImperfectInformationNode[float]] = field(default=None, repr=False)  # type: ignore[assignment]
    fill_repeater: Optional[Repeater[None]] = field(default=None, repr=False)

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        super().prepare_match(role, ruleset, startclock_config, playclock_config)
        self.fill_repeater = Repeater(
            timeout_ns=0,
            func=self.fill,
            shortcircuit=self._is_fully_enumerated,
            slack=2.0,
        )

    def fill(self, possible_states: Iterator[State]) -> None:
        possible_state = next(possible_states, None)
        if possible_state is None:
            self.tree.fully_enumerated = True
            self.tree.parent = None
            return
        self.tree.possible_states.add(possible_state)

    def _is_fully_enumerated(self, *args: Any, **kwargs: Any) -> bool:
        return self.tree.fully_enumerated

    def update(self, ply: int, view: View, total_time_ns: int) -> None:
        used_time = time.monotonic_ns()
        super().update(ply=ply, view=view, total_time_ns=total_time_ns)
        used_time = time.monotonic_ns() - used_time
        if self.tree.fully_enumerated:
            return
        total_quota = self.update_time_quota + self.search_time_quota
        fill_time_scale = self.update_time_quota / total_quota
        fill_time_ns = self._get_timeout_ns(total_time_ns=total_time_ns, used_time_ns=used_time, scale=fill_time_scale)
        self.fill_repeater.timeout_ns = fill_time_ns
        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg="Filling tree at "
            f"{rich(self.get_main_tree(logging.DEBUG))} for at most {format_ns(fill_time_ns)}",
            end_msg="Filled tree",
            abort_msg="Aborted filling tree",
        ):
            record = self.tree.gather_record(
                has_incomplete_information=self.interpreter.has_incomplete_information,
                views={ply: view},
            )
            possible_states = self.interpreter.get_possible_states(record=record, ply=ply, is_final=False)
            self.tree.possible_states.clear()
            self.fill_repeater(possible_states)

    def step(self) -> None:
        node = self.tree
        ply = node.depth
        determinization: State = node.get_determinization()

        while (
            node.children is not None
            and node.children
            and any(state == determinization for (state, _) in node.children)
            and not self.interpreter.is_terminal(determinization)
            and (self.max_expansion_depth is None or (node.depth - ply) < (self.max_expansion_depth - 1))
        ):
            key = self.selector(node=node, state=determinization)
            node = node.children[key]
            determinization = node.get_determinization()

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
                possible_states={init_state},
                view=view,
                role=self.role,
                fully_enumerated=True,
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
            determinization = self.tree.get_determinization()
            if self.interpreter.is_terminal(determinization):
                continue
            self.tree.branch(interpreter=self.interpreter, state=determinization)
        return {
            key: (
                float("-inf") if not self._can_lookup() else self._lookup(key),
                child.valuation.total_playouts
                if child.valuation is not None and hasattr(child.valuation, "total_playouts")
                else 0,
                child.valuation.utility if child.valuation is not None else 0.0,
            )
            for key, child in self.tree.children.items()
        }

    def _lookup(self, key: Optional[Tuple[State, _Action]] = None) -> float:
        node = self.tree.children[key] if key is not None else self.tree
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

    def get_main_tree(self, target_log_level: int) -> Optional[Node[float, _K]]:
        if log.level > target_log_level:
            return
        return self.tree


class MultiObserverMonteCarloTreeSearchAgent(MonteCarloTreeSearchAgent[_K]):
    trees: Optional[MutableMapping[Role, ImperfectInformationNode[float]]]
    roles: Optional[FrozenSet[Role]]
    selectors: Optional[Mapping[Role, Selector[float, _K]]]
    evaluators: Optional[Mapping[Role, Evaluator[float]]]
    step_repeater: Optional[Repeater[None]]
    fill_repeater: Optional[Repeater[None]]
    books: Optional[Mapping[Role, Book[float]]]


@dataclass
class MultiObserverInformationSetMCTSAgent(
    AbstractMCTSAgent[Tuple[State, _Action]],
    MultiObserverMonteCarloTreeSearchAgent[Tuple[State, _Action]],
):
    trees: Optional[MutableMapping[Role, ImperfectInformationNode[float]]] = field(default=None)
    roles: Optional[FrozenSet[Role]] = field(default=None)
    views: Optional[MutableMapping[int, View]] = field(default=None)
    moves: Optional[MutableMapping[int, Move]] = field(default=None)
    selectors: Optional[Mapping[Role, Selector[float, _K]]] = field(default=None)
    evaluators: Optional[Mapping[Role, Evaluator[float]]] = field(default=None)
    step_repeater: Optional[Repeater[None]] = field(default=None)
    fill_repeater: Optional[Repeater[None]] = field(default=None)
    books: Optional[Mapping[Role, Book[float]]] = field(default=None)

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        used_time_ns = time.monotonic_ns()
        super().prepare_match(role, ruleset, startclock_config, playclock_config)

        self.roles = self.interpreter.get_roles()
        self.trees = self._get_roots()

        self.selectors = {role: self.selector_factory(role=role) for role in self.roles}

        self.step_repeater = Repeater(
            func=self.step,
            timeout_ns=playclock_config.delay_ns,
            max_repeats=self.max_mcts_iterations,
            shortcircuit=self._can_lookup,
            slack=1.5,
        )
        self.fill_repeater = Repeater(
            func=self.fill,
            timeout_ns=playclock_config.delay_ns,
            shortcircuit=self._fully_enumerated,
            slack=2.0,
        )

        used_time_ns = time.monotonic_ns() - used_time_ns
        total_time_ns = startclock_config.total_time_ns + startclock_config.delay_ns
        timeout_ns = self._get_timeout_ns(
            total_time_ns=total_time_ns,
            used_time_ns=used_time_ns,
            net_zero_time_ns=total_time_ns,
            zero_time_ns=total_time_ns,
            scale=0.9,
        )
        self.books = self._build_books(timeout_ns=timeout_ns)
        self.evaluators = {
            role: LightPlayoutEvaluator(
                role=role,
                final_state_evaluator=final_goal_normalized_utility_evaluator,
                book=self.books.get(role) if self.books is not None else None,
            )
            for role in self.roles
        }
        self.views = {}
        self.moves = {}

    def _get_roots(self) -> MutableMapping[Role, ImperfectInformationNode[float]]:
        init_state = self.interpreter.get_init_state()
        roles_in_control = Interpreter.get_roles_in_control(init_state)
        views = self.interpreter.get_sees(init_state)
        roots = {}
        for role in self.roles:
            if role not in roles_in_control:
                root = HiddenInformationSetNode(
                    role=role,
                    possible_states={init_state},
                    fully_enumerated=True,
                )
            else:
                root = VisibleInformationSetNode(
                    role=role,
                    possible_states={init_state},
                    fully_enumerated=True,
                    view=views[role],
                )
            roots[role] = root
        return roots

    def _fully_enumerated(self, tree: ImperfectInformationNode[float], *args: Any, **kwargs: Any) -> bool:
        return tree.fully_enumerated

    def _build_books(self, timeout_ns: int) -> Optional[Mapping[Role, Book[float]]]:
        if timeout_ns <= 10 * ONE_S_IN_NS or self.skip_book:
            return
        start = time.monotonic_ns()
        books = {}
        other_quota = 1.0
        main_quota = other_quota * (len(self.roles) - 1)
        total_quota = main_quota + other_quota
        main_scale = main_quota / total_quota
        other_scale = other_quota / total_quota
        for role in self.roles:
            used_time = time.monotonic_ns() - start
            zero_time_ns = timeout_ns + used_time
            build_book_timeout_ns = self._get_timeout_ns(
                total_time_ns=timeout_ns,
                used_time_ns=used_time,
                scale=main_scale if role == self.role else other_scale,
                net_zero_time_ns=zero_time_ns,
                zero_time_ns=zero_time_ns,
            )
            books[role] = self._build_book(role, build_book_timeout_ns)
        return books

    def _build_book(self, role: Role, timeout_ns: int) -> Book[float]:
        book_builder = BookBuilder(
            interpreter=self.interpreter,
            role=role,
            evaluator=final_goal_normalized_utility_evaluator,
            min_value=0.0,
            max_value=1.0,
        )

        book_building_repeater = Repeater(
            func=book_builder.step,
            timeout_ns=timeout_ns,
            shortcircuit=book_builder.is_done,
        )

        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=f"Building book from perspective "
            f"{rich(role)} for role {rich(self.role)} for at most {format_ns(timeout_ns)}",
            end_msg=f"Built book from perspective {rich(role)} for role {rich(self.role)}",
            abort_msg="Aborted building book",
        ):
            it, elapsed_time = book_building_repeater()
        log.info(
            "%s book from perspective %s for %s with %s entries in %s (%s entries/s)",
            "Finished" if book_builder.done else "Built",
            rich(role),
            rich(self.role),
            format_amount(len(book_builder.book)),
            format_ns(elapsed_time),
            format_rate_ns(len(book_builder.book), elapsed_time),
        )
        return book_builder()

    def update(self, ply: int, view: View, total_time_ns: int) -> None:
        self.views[ply] = view
        used_time = time.monotonic_ns()
        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=f"Developing at {rich(self.get_main_tree(logging.DEBUG))}",
            end_msg="Developed to current ply and view",
            abort_msg="Aborted developing",
        ):
            self.trees[self.role] = self.trees[self.role].develop(
                interpreter=self.interpreter,
                ply=ply,
                view=view,
            )
        if self.trees[self.role].fully_enumerated:
            return
        used_time = time.monotonic_ns() - used_time
        total_quota = self.update_time_quota + self.search_time_quota
        fill_time_scale = self.update_time_quota / total_quota
        fill_time_ns = self._get_timeout_ns(total_time_ns=total_time_ns, used_time_ns=used_time, scale=fill_time_scale)
        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg="Filling tree at "
            f"{rich(self.get_main_tree(logging.DEBUG))} for at most {format_ns(fill_time_ns)}",
            end_msg="Filled tree",
            abort_msg="Aborted filling tree",
        ):
            record = self.trees[self.role].gather_record(
                has_incomplete_information=self.interpreter.has_incomplete_information,
                views={ply: view},
            )
            possible_states = self.interpreter.get_possible_states(record=record, ply=ply, is_final=False)
            self.fill_repeater.timeout_ns = fill_time_ns
            tree = self.trees[self.role]
            tree.possible_states.clear()
            tree.fully_enumerated = False
            self.fill_repeater(tree, possible_states)

    def fill(self, tree: ImperfectInformationNode[float], possible_states: Iterator[State]) -> None:
        possible_state = next(possible_states, None)
        if possible_state is None:
            tree.fully_enumerated = True
            tree.parent = None
            return
        tree.possible_states.add(possible_state)

    def step(self) -> None:
        tree = self.trees[self.role]
        ply = tree.depth
        determinization = tree.get_determinization()
        trees = self._recenter_trees(ply=ply, determinization=determinization)
        assert all(node.depth == tree.depth for node in trees.values()), "Assumption: all trees are at the same depth"
        while (
            tree.children is not None
            and tree.children
            and not self.interpreter.is_terminal(determinization)
            and any(determinization == state for state, _ in tree.children)
            and (self.max_expansion_depth is None or (tree.depth - ply) < (self.max_expansion_depth - 1))
        ):
            assert (
                trees is not None
            ), "Assumption: not self.interpreter.is_terminal(determinization) implies trees is not None"
            turn = self._select(determinization=determinization, tree=tree, trees=trees)
            assert determinization in tree.possible_states, "Assumption: determinization in tree.possible_states"
            assert any(
                determinization == state for state, _ in tree.children
            ), "Assumption: determinization in (state,_) for all (state,_) in tree.children"
            assert all(any(determinization == state for state, _ in node.children) for node in trees.values()), (
                "Assumption: determinization in (state,_) for all (state,_) in node.children "
                "for all nodes in trees.values()"
            )
            tree = tree.descend(state=determinization, turn=turn)
            assert tree is not None, "Assumption: tree is not None"
            assert all(
                determinization in node.possible_states for node in trees.values()
            ), "Assumption: determinization in node.possible_states for all nodes in trees.values()"
            trees = {role: node.descend(state=determinization, turn=turn) for role, node in trees.items()}
            assert all(
                node is not None for node in trees.values()
            ), "Assumption: not self.interpreter.is_terminal(determinization) implies all nodes are not None"

            determinization = self.interpreter.get_next_state(determinization, turn)

        tree.branch(interpreter=self.interpreter, state=determinization)

        utilities = self._evaluate(determinization=determinization, tree=tree, trees=trees)

        self._backpropagate(tree=tree, trees=trees, utilities=utilities)

    def _recenter_trees(self, ply: int, determinization: State) -> Mapping[Role, ImperfectInformationNode[float]]:
        if ply == 0:
            return {role: tree for role, tree in self.trees.items() if role != self.role}
        states = {0: self.interpreter.get_init_state(), ply: determinization}

        record = self._gather_record(states=states)
        developments = self.interpreter.get_developments(record=record)
        roots: Mapping[Role, ImperfectInformationNode[float]] = {
            role: tree.root for role, tree in self.trees.items() if role != self.role
        }
        trees: Mapping[Role, ImperfectInformationNode[float]] = {}
        for development in developments:
            trees = {role: root for role, root in roots.items()}
            for ply_, step in enumerate(development):
                state = step.state
                turn = step.turn
                if turn is not None:
                    next_state = development[ply_ + 1].state
                    for role, tree in trees.items():
                        tree._initialize_children()
                        tree._branch_by(
                            interpreter=self.interpreter,
                            state=state,
                            turn=turn,
                            next_state=next_state,
                            fully_enumerated=False,
                            fully_expanded=False,
                        )
                    trees = {role: tree.descend(state, turn) for role, tree in trees.items()}
                    if any(tree is None for tree in trees.values()):
                        break
            if all(tree is not None for tree in trees.values()):
                break

        return trees

    def _gather_record(self, states: Mapping[int, State]) -> Record:
        if self.interpreter.has_incomplete_information:
            return self._gather_imperfect_information_record(states=states)
        return self._gather_perfect_information_record(states=states)

    def _gather_imperfect_information_record(self, states: Mapping[int, State]) -> ImperfectInformationRecord:
        return ImperfectInformationRecord(
            views={ply_: {self.role: view} for ply_, view in self.views.items()},
            role_move_map={ply_: {self.role: move} for ply_, move in self.moves.items()},
            possible_states={ply_: frozenset((state,)) for ply_, state in states.items()},
        )

    def _gather_perfect_information_record(self, states: Mapping[int, State]) -> PerfectInformationRecord:
        states_ = {ply: cast(State, view) for ply, view in self.views.items()}
        states_.update(states)
        return PerfectInformationRecord(states=states_)

    def _select(
        self,
        determinization: State,
        tree: ImperfectInformationNode[float],
        trees: Mapping[Role, ImperfectInformationNode[float]],
    ) -> Turn:
        roles_in_control = Interpreter.get_roles_in_control(determinization)
        assert all(
            determinization in node.possible_states for node in trees.values()
        ), "Assumption: determinization in node.possible_states for all nodes in trees.values()"
        for role, node in trees.items():
            node.branch(interpreter=self.interpreter, state=determinization)
        assert all(
            any(determinization == state for state, _ in node.children) for node in trees.values()
        ), "Assumption: branch implies state in children if non-terminal"
        role_move_map = {
            role: self.selectors[role](node=node, state=determinization)[1]
            for role, node in trees.items()
            if role in roles_in_control
        }
        if self.role in roles_in_control:
            role_move_map[self.role] = self.selectors[self.role](node=tree, state=determinization)[1]
        return Turn(role_move_map)

    def _evaluate(
        self,
        determinization: State,
        tree: ImperfectInformationNode[float],
        trees: Mapping[Role, ImperfectInformationNode[float]],
    ) -> Mapping[Role, float]:
        utilities = {
            role: node.evaluate(
                interpreter=self.interpreter,
                state=determinization,
                valuation_factory=NormalizedUtilityValuation.from_utility,
                evaluator=self.evaluators[role],
            )
            for role, node in trees.items()
        }
        utilities[self.role] = tree.evaluate(
            interpreter=self.interpreter,
            state=determinization,
            valuation_factory=NormalizedUtilityValuation.from_utility,
            evaluator=self.evaluators[self.role],
        )
        return utilities

    def _backpropagate(
        self,
        tree: ImperfectInformationNode[float],
        trees: Mapping[Role, ImperfectInformationNode[float]],
        utilities: Mapping[Role, float],
    ) -> None:
        while tree.parent is not None:
            tree = tree.parent
            if tree.valuation is None:
                tree.valuation = NormalizedUtilityValuation.from_utility(utilities[self.role])
            else:
                tree.valuation = tree.valuation.propagate(utilities[self.role])
        for role, tree in trees.items():
            node = tree
            while node.parent is not None:
                node = node.parent
                if node.valuation is None:
                    node.valuation = NormalizedUtilityValuation.from_utility(utilities[role])
                else:
                    node.valuation = node.valuation.propagate(utilities[role])

    def descend(self, key: Tuple[State, _Action]) -> None:
        state: State = key[0]
        move: Move = key[1]
        assert isinstance(move, gdl.Subrelation), "Assumption: action is a move"
        self.trees[self.role].branch(interpreter=self.interpreter, state=state)
        self.trees[self.role].move = move
        self.moves[self.trees[self.role].depth] = move
        self.trees[self.role].trim()

    def get_key_to_evaluation(self) -> Mapping[Tuple[State, _Action], _MCTSEvaluation]:
        while not self.trees[self.role].children:
            determinization = self.trees[self.role].get_determinization()
            if self.interpreter.is_terminal(determinization):
                continue
            self.trees[self.role].branch(interpreter=self.interpreter, state=determinization)
        return {
            key: (
                float("-inf") if not self._can_lookup() else self._lookup(key),
                child.valuation.total_playouts
                if child.valuation is not None and hasattr(child.valuation, "total_playouts")
                else 0,
                child.valuation.utility if child.valuation is not None else 0.0,
            )
            for key, child in self.trees[self.role].children.items()
        }

    def _can_lookup(self) -> bool:
        return (
            self.books is not None
            and self.books.get(self.role) is not None
            and all(state in self.books[self.role] for state in self.trees[self.role].possible_states)
        )

    def _lookup(self, key: Optional[Tuple[State, _Action]] = None) -> float:
        node = self.trees[self.role].children[key] if key is not None else self.trees[self.role]
        utilities = tuple(self.books[self.role][state] for state in node.possible_states)
        total = sum(utilities)
        return total / len(utilities)

    def _get_move_to_aggregation(
        self,
        key_to_evaluation: Mapping[_K, _MCTSEvaluation],
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
        state, action = key
        move: Move
        if isinstance(action, Turn):
            move = action[self.role]
        else:
            assert isinstance(action, gdl.Subrelation), "Assumption: action is a move"
            move = cast(Move, action)
        return move

    def get_main_tree(self, target_log_level: int) -> Optional[Node[float, _K]]:
        if log.level > target_log_level:
            return
        return self.trees[self.role]
