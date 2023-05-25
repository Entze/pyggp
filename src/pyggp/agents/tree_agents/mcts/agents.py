import abc
import collections
import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import (
    FrozenSet,
    Generic,
    Iterator,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Set,
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
from pyggp.books import Book, BookBuilder
from pyggp.engine_primitives import Development, DevelopmentStep, Move, Role, State, Turn, View
from pyggp.gameclocks import GameClock
from pyggp.interpreters import Interpreter
from pyggp.records import ImperfectInformationRecord
from pyggp.repeaters import Repeater

log = logging.getLogger("pyggp")

_K = TypeVar("_K")

_BookValue = float
_Total_Playouts = int
_Utility = float
_NegatedTargetStates = int
_MCTSEvaluation = Tuple[_BookValue, _Total_Playouts, _Utility, _NegatedTargetStates]


class MonteCarloTreeSearchAgent(TreeAgent[_K, _MCTSEvaluation]):
    def step(self) -> None:
        ...


@dataclass
class AbstractMCTSAgent(AbstractTreeAgent[_K, _MCTSEvaluation], MonteCarloTreeSearchAgent[_K], Generic[_K], abc.ABC):
    @abc.abstractmethod
    def _can_lookup(self) -> bool:
        raise NotImplementedError

    def _move_evaluation_as_str(self, move: Move, evaluation: _MCTSEvaluation) -> str:
        book_value, total_playouts, utility, negated_target_states = evaluation
        strs = []
        if negated_target_states != -1:
            strs.append(f"{move} ({-negated_target_states}): ")
        else:
            strs.append(f"{move}: ")
        if self._can_lookup():
            strs.append(f"{book_value:.2f} | ")
        avg_utility = utility / total_playouts if total_playouts > 0 else 0.0
        strs.append(f"{avg_utility:.2f} @ ")
        strs.append(f"{format_amount(total_playouts)}")
        return "".join(strs)


class SingleObserverMonteCarloTreeSearchAgent(MonteCarloTreeSearchAgent[_K]):
    tree: Optional[Node[float, _K]]
    selector: Optional[Selector[float, _K]]
    evaluator: Optional[Evaluator[float]]
    repeater: Optional[Repeater]
    book: Optional[Book[float]]


@dataclass
class AbstractSOMCTSAgent(AbstractMCTSAgent, SingleObserverMonteCarloTreeSearchAgent[_K], Generic[_K], abc.ABC):
    tree: Optional[Node[float, _K]] = field(default=None, repr=False)
    selector: Optional[Selector[float, _K]] = field(default=None, repr=False)
    evaluator: Optional[Evaluator[float]] = field(default=None, repr=False)
    repeater: Optional[Repeater] = field(default=None, repr=False)
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

        self.selector = uct_selector(self.role)

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

    def update(self, ply: int, view: View) -> None:
        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=(
                "Developing tree "
                f"(depth={self.tree.depth}, "
                f"avg_height={self.tree.avg_height:.2f}, "
                f"valuation={self.tree.valuation}, "
                f"arity={self.tree.arity})"
            ),
            end_msg="Developed tree",
            abort_msg="Aborted developing tree",
        ):
            self.tree = self.tree.develop(interpreter=self.interpreter, ply=ply, view=view)

    def search(self, search_time_ns: int) -> None:
        self.repeater.timeout_ns = search_time_ns
        with log_time(
            log,
            level=logging.DEBUG,
            begin_msg=(
                "Searching tree ("
                f"depth={self.tree.depth}, "
                f"avg_height={self.tree.avg_height:.2f}, "
                f"valuation={self.tree.valuation}, "
                f"arity={self.tree.arity}"
                f") for at most {format_ns(search_time_ns)}"
            ),
            end_msg="Searched tree",
            abort_msg="Aborted searching tree",
        ):
            it, elapsed_ns = self.repeater()

        log.info("%s it in %s (%s it/s)", format_amount(it), format_ns(elapsed_ns), format_rate_ns(it, elapsed_ns))

    def _guess_remaining_moves(self) -> int:
        return math.ceil(self.tree.avg_height)


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
                -1,  # negated_target_states
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

    def _get_root(self) -> Node[float, _K]:
        init_state = self.interpreter.get_init_state()
        roles_in_control = Interpreter.get_roles_in_control(init_state)
        if self.role not in roles_in_control:
            return HiddenInformationSetNode(possible_states={init_state}, role=self.role)
        else:
            view = self.interpreter.get_sees_by_role(init_state, self.role)
            return VisibleInformationSetNode(possible_states={init_state}, view=view, role=self.role)

    def _can_lookup(self) -> bool:
        return self.book is not None and all(state in self.book for state in self.tree.possible_states)

    def descend(self, key: Tuple[State, _Action]) -> None:
        state, move = key
        assert isinstance(move, gdl.Subrelation), "Assumption: action is a move"
        self.tree.expand(interpreter=self.interpreter)
        self.tree.move = move
        self.tree.trim()

    def get_key_to_evaluation(self) -> Mapping[Tuple[State, _Action], _MCTSEvaluation]:
        self.tree.expand(interpreter=self.interpreter)
        return {
            key: (
                float("-inf") if not self._can_lookup() else self._lookup(child),
                child.valuation.total_playouts
                if child.valuation is not None and hasattr(child.valuation, "total_playouts")
                else 0,
                child.valuation.utility if child.valuation is not None else 0.0,
                -len(child.possible_states),
            )
            for key, child in self.tree.children.items()
        }

    def _lookup(self, node: ImperfectInformationNode[float]) -> float:
        return sum(self.book.get(state, float("-inf")) for state in node.possible_states) / len(node.possible_states)

    def _get_move_to_aggregation(
        self,
        key_to_evaluation: Mapping[Tuple[State, _Action], _MCTSEvaluation],
    ) -> Mapping[Move, _MCTSEvaluation]:
        self.tree.expand(interpreter=self.interpreter)
        move_to_aggregated_book_value: MutableMapping[Move, float] = collections.defaultdict(float)
        move_to_total_playouts: MutableMapping[Move, int] = collections.defaultdict(int)
        move_to_utility: MutableMapping[Move, float] = collections.defaultdict(float)
        move_to_possible_states: MutableMapping[Move, Set[State]] = collections.defaultdict(set)
        move_to_links: MutableMapping[Move, int] = collections.defaultdict(int)
        for (state, action), (book_value, total_playouts, utility, negated_target_states) in key_to_evaluation.items():
            move_to_links[action] += 1
            move_to_aggregated_book_value[action] += book_value
            move_to_total_playouts[action] += total_playouts
            move_to_utility[action] += utility
            move_to_possible_states[action].update(self.tree.children[(state, action)].possible_states)
        return {
            self._key_to_move(key): (
                move_to_aggregated_book_value[self._key_to_move(key)] / move_to_links[self._key_to_move(key)],
                move_to_total_playouts[self._key_to_move(key)],
                move_to_utility[self._key_to_move(key)],
                -len(move_to_possible_states[self._key_to_move(key)]),
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
class MultiObserverInformationSetMCTSAgent(
    AbstractMCTSAgent[_Action],
    MultiObserverMonteCarloTreeSearchAgent[_Action],
    abc.ABC,
):
    trees: Optional[MutableMapping[Role, ImperfectInformationNode[float]]] = field(default=None, repr=False)
    roles: Optional[FrozenSet[Role]] = field(default=None, repr=False)
    selectors: Optional[Mapping[Role, Selector[float, _K]]] = field(default=None, repr=False)
    evaluators: Optional[Mapping[Role, Evaluator[float]]] = field(default=None, repr=False)
    repeater: Optional[Repeater] = field(default=None, repr=False)
    books: Optional[Mapping[Role, Book[float]]] = field(default=None, repr=False)

    def prepare_match(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        timeout_ns = startclock_config.total_time_ns + startclock_config.delay_ns + time.monotonic_ns()
        super().prepare_match(role, ruleset, startclock_config, playclock_config)
        self.roles = self.interpreter.get_roles()
        self.trees = self._get_roots()
        self.selectors = {role: uct_selector(role) for role in self.roles}
        self.repeater = Repeater(
            func=self.step,
            timeout_ns=playclock_config.delay_ns + playclock_config.total_time_ns,
            shortcircuit=self._can_lookup,
        )
        timeout_ns -= time.monotonic_ns()
        self.books = self._build_books(timeout_ns=timeout_ns)
        self.evaluators = {
            role: LightPlayoutEvaluator(
                role=role,
                final_state_evaluator=final_goal_normalized_utility_evaluator,
                book=self.books[role],
            )
            for role in self.roles
        }

    def _get_roots(self) -> MutableMapping[Role, ImperfectInformationNode[float]]:
        init_state = self.interpreter.get_init_state()
        roles_in_control = Interpreter.get_roles_in_control(init_state)
        return {role: self._get_root(role, roles_in_control, init_state) for role in self.roles}

    def _get_root(self, role: Role, roles_in_control: FrozenSet[Role], state: State) -> ImperfectInformationNode[float]:
        if role not in roles_in_control:
            return HiddenInformationSetNode(
                possible_states={state},
                role=role,
            )
        else:
            view = self.interpreter.get_sees_by_role(state, role)
            return VisibleInformationSetNode(possible_states={state}, role=role, view=view)

    def step(self) -> None:
        nodes, determinization = self._select()

        nodes[self.role].expand(interpreter=self.interpreter)

        utilities = {
            role: node.evaluate(
                interpreter=self.interpreter,
                evaluator=self.evaluators[role],
                valuation_factory=NormalizedUtilityValuation.from_utility,
                state=determinization,
            )
            for role, node in nodes.items()
        }

        self._backpropagate(nodes, utilities)

    def _select(self) -> Tuple[Mapping[Role, ImperfectInformationNode[float]], State]:
        determinization = random.choice(tuple(self.trees[self.role].possible_states))
        nodes: MutableMapping[Role, ImperfectInformationNode[float]] = self._recenter_trees(determinization)

        while (
            nodes[self.role].children is not None
            and nodes[self.role].children
            and not self.interpreter.is_terminal(determinization)
        ):
            mutable_turn: MutableMapping[Role, Move] = {}
            next_nodes: MutableMapping[Role, ImperfectInformationNode[float]] = {}
            for role, node in nodes.items():
                if role != self.role:
                    node.expand(interpreter=self.interpreter)
                if isinstance(node, VisibleInformationSetNode):
                    key: Tuple[State, Move] = self.selectors[role](node, state=determinization)
                    state, move = key
                    mutable_turn[role] = move
                    next_nodes[role] = node.children[key]
            turn = Turn(mutable_turn)
            for role, node in nodes.items():
                if isinstance(node, HiddenInformationSetNode):
                    key: Tuple[State, Turn] = (determinization, turn)
                    next_nodes[role] = node.children[key]
            nodes = next_nodes
            determinization = self.interpreter.get_next_state(determinization, *turn.as_plays())
        return nodes, determinization

    def _recenter_trees(self, determinization: State) -> MutableMapping[Role, ImperfectInformationNode[float]]:
        trees = {role: node for role, node in self.trees.items()}
        if all(determinization in node.possible_states for node in self.trees.values()):
            return trees
        view_trail: MutableSequence[Optional[View]] = []
        possible_states_trail: MutableSequence[FrozenSet[State]] = []
        move_trail: MutableSequence[Optional[Move]] = []
        possible_turns_trail: MutableSequence[Optional[FrozenSet[Turn]]] = []
        node = self.trees[self.role]
        while node is not None:
            view_trail.append(getattr(node, "view", None))
            move_trail.append(getattr(node, "move", None))
            possible_turns_trail.append(getattr(node, "possible_turns", None))
            possible_states_trail.append(frozenset(node.possible_states))
            node = node.parent

        possible_states_record = {}
        view_record = {}
        possible_turns_record = {}
        role_move_map = {}
        for ply, (view, possible_states, move, possible_turns) in enumerate(
            zip(
                reversed(view_trail),
                reversed(possible_states_trail),
                reversed(move_trail),
                reversed(possible_turns_trail),
            ),
        ):
            if view is not None:
                view_record[ply] = {self.role: view}
            if move is not None:
                role_move_map[ply] = {self.role: move}
            possible_states_record[ply] = possible_states

        possible_states_record[self.trees[self.role].depth] = frozenset((determinization,))
        record = ImperfectInformationRecord(
            possible_states=possible_states_record,
            views=view_record,
            role_move_map=role_move_map,
        )
        developments: Iterator[Development] = self.interpreter.get_developments(record)
        development: Development
        development, *_ = developments
        roots = {}
        for role, node in trees.items():
            if role == self.role:
                continue
            while node.parent is not None:
                node = node.parent
            roots[role] = node
        nodes = roots
        step: DevelopmentStep
        for step in development:
            state = step.state
            turn = step.turn
            if turn is None:
                continue
            for role, node in nodes.items():
                if role == self.role:
                    continue
                if isinstance(node, HiddenInformationSetNode):
                    key = (state, turn)
                else:
                    assert isinstance(node, VisibleInformationSetNode), "Assumption: node is VisibleInformationSetNode"
                    key = (state, turn[role])
                node.expand(interpreter=self.interpreter)
                assert key in node.children, "Assumption: key in node.children"
                trees[role] = node.children[key]
            nodes = trees
        assert all(
            determinization in node.possible_states for node in trees.values()
        ), "Guarantee: all nodes have determinization in possible_states"
        return trees

    def _backpropagate(
        self,
        nodes: Mapping[Role, ImperfectInformationNode[float]],
        utilities: Mapping[Role, float],
    ) -> None:
        while any(node.parent is not None for node in nodes.values()):
            assert all(node.parent is not None for node in nodes.values()), "Assumption: all have parent"
            parents = {}
            for role, node in nodes.items():
                utility = utilities[role]
                parents[role] = node.parent
                if node.parent.valuation is not None:
                    node.parent.valuation = node.parent.valuation.propagate(utility=utility)
                else:
                    node.parent.valuation = NormalizedUtilityValuation.from_utility(utility)
                nodes = parents

    def _can_lookup(self) -> bool:
        return (
            self.books is not None
            and self.role in self.books
            and all(state in self.books[self.role] for state in self.trees[self.role].possible_states)
        )

    def _build_books(self, timeout_ns: int) -> Mapping[Role, Book[float]]:
        if timeout_ns < ONE_S_IN_NS:
            return {role: {} for role in self.roles}
        build_books_ns = (timeout_ns * 9) // 10
        main_ns = 9 * build_books_ns // 10
        other_ns = (build_books_ns - main_ns) // max(1, len(self.roles) - 1)
        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=f"Building books for at most {format_ns(build_books_ns)}",
            end_msg=f"Built books",
            abort_msg=f"Aborting building books",
        ):
            return {role: self._build_book(role, other_ns if role != self.role else main_ns) for role in self.roles}

    def _build_book(self, role: Role, timeout_ns: int) -> Book[float]:
        book_builder = BookBuilder(
            interpreter=self.interpreter,
            role=role,
            evaluator=final_goal_normalized_utility_evaluator,
            min_value=0.0,
            max_value=1.0,
        )

        def shortcircuit() -> bool:
            return book_builder.done

        book_building_repeater = Repeater(func=book_builder.step, timeout_ns=timeout_ns, shortcircuit=shortcircuit)

        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=f"Building book for role {role} for at most {format_ns(timeout_ns)}",
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

    def update(self, ply: int, view: View) -> None:
        with log_time(
            log,
            level=logging.DEBUG,
            begin_msg="Developing trees",
            end_msg="Developed trees",
            abort_msg="Aborted developing trees",
        ):
            for role in self.roles:
                with log_time(
                    log,
                    level=logging.DEBUG,
                    begin_msg=f"Developing tree for {role}",
                    end_msg=f"Developed tree for {role}",
                    abort_msg=f"Aborted developing tree for {role}",
                ):
                    tree = self.trees[role]
                    tree = tree.develop(
                        interpreter=self.interpreter,
                        view=view,
                        ply=ply,
                    )
                    assert tree.depth == ply, "Assumption: tree.depth == ply"
                    self.trees[role] = tree

    def search(self, search_time_ns: int) -> None:
        self.repeater.timeout_ns = search_time_ns
        with log_time(
            log,
            level=logging.DEBUG,
            begin_msg=(
                "Searching trees ("
                f"depth={self.trees[self.role].depth}, "
                f"valuation={self.trees[self.role].valuation}, "
                f"arity={self.trees[self.role].arity}"
                f") for at most {format_ns(search_time_ns)}"
            ),
            end_msg="Searched trees",
            abort_msg="Aborted searching trees",
        ):
            it, elapsed_ns = self.repeater()

        log.info("%s it in %s (%s it/s)", format_amount(it), format_ns(elapsed_ns), format_rate_ns(it, elapsed_ns))

    def descend(self, key: Tuple[State, _Action]) -> None:
        self.trees[self.role].expand(interpreter=self.interpreter)
        state, action = key
        nr_of_action_compatible_states = sum(state == s for s, _ in self.trees[self.role].children)
        if nr_of_action_compatible_states > 1:
            return
        nr_of_state_compatible_actions = sum(action == a for _, a in self.trees[self.role].children)
        if nr_of_state_compatible_actions > 1:
            self.trees[self.role] = self.trees[self.role].children[key]

    def get_key_to_evaluation(self) -> Mapping[Tuple[State, _Action], _MCTSEvaluation]:
        self.trees[self.role].expand(interpreter=self.interpreter)
        return {
            key: (
                float("-inf") if not self._can_lookup() else self._lookup(),
                child.valuation.total_playouts
                if child.valuation is not None and hasattr(child.valuation, "total_playouts")
                else 0,
                child.valuation.utility if child.valuation is not None else 0.0,
                -len(child.possible_states),
            )
            for key, child in self.trees[self.role].children.items()
        }

    def _lookup(self) -> float:
        return sum(
            self.books[self.role].get(state, float("-inf")) for state in self.trees[self.role].possible_states
        ) / len(self.trees[self.role].possible_states)

    def _get_move_to_aggregation(
        self,
        key_to_evaluation: Mapping[Tuple[State, _Action], _MCTSEvaluation],
    ) -> Mapping[Move, _MCTSEvaluation]:
        self.trees[self.role].expand(interpreter=self.interpreter)
        move_to_aggregated_book_value: MutableMapping[Move, float] = collections.defaultdict(float)
        move_to_total_playouts: MutableMapping[Move, int] = collections.defaultdict(int)
        move_to_utility: MutableMapping[Move, float] = collections.defaultdict(float)
        move_to_possible_states: MutableMapping[Move, Set[State]] = collections.defaultdict(set)
        move_to_links: MutableMapping[Move, int] = collections.defaultdict(int)
        for (state, action), (book_value, total_playouts, utility, negated_target_states) in key_to_evaluation.items():
            move_to_links[action] += 1
            move_to_aggregated_book_value[action] += book_value
            move_to_total_playouts[action] += total_playouts
            move_to_utility[action] += utility
            move_to_possible_states[action].update(self.trees[self.role].children[(state, action)].possible_states)
        return {
            self._key_to_move(key): (
                move_to_aggregated_book_value[self._key_to_move(key)] / move_to_links[self._key_to_move(key)],
                move_to_total_playouts[self._key_to_move(key)],
                move_to_utility[self._key_to_move(key)],
                -len(move_to_possible_states[self._key_to_move(key)]),
            )
            for key in key_to_evaluation
        }

    def _key_to_move(self, key: Tuple[State, _Action]) -> Move:
        assert isinstance(key[1], gdl.Subrelation), "Assumption: key is (state, move)"
        return key[1]
