import random
from collections import deque
from dataclasses import dataclass, field
from typing import (
    Deque,
    FrozenSet,
    Generic,
    Iterable,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from pyggp.agents.tree_agents.evaluators import Evaluator
from pyggp.engine_primitives import RANDOM, Role, State, Turn
from pyggp.interpreters import Interpreter

_U_co = TypeVar("_U_co", covariant=True)

Book = Mapping[State, _U_co]
MutableBook = MutableMapping[State, _U_co]


@dataclass
class BookBuilder(Generic[_U_co]):
    @dataclass(frozen=True)
    class Seed:
        state: State

    @dataclass(frozen=True)
    class Search(Generic[_U_co]):
        state: State
        alpha: _U_co
        beta: _U_co

    interpreter: Interpreter
    role: Role
    evaluator: Evaluator[_U_co]
    min_value: _U_co
    max_value: _U_co
    allies: Optional[FrozenSet[Role]] = field(default=None)
    init_seed_state: Optional[State] = field(default=None)
    book: MutableBook[_U_co] = field(default_factory=dict)
    _queue: Optional[Deque["_QueueItem"]] = field(default=None)
    done: bool = field(default=False)

    def __call__(self) -> Book[_U_co]:
        return self.book

    def step(self) -> None:
        if self._queue is None or not self._queue:
            self._initialize()
        if self.done:
            return
        item = self._queue.popleft()
        if isinstance(item, BookBuilder.Seed):
            self._handle_seed(*item)
        else:
            assert isinstance(item, BookBuilder.Search), "Assumption: item has type Search"
            self._handle_search(*item)

    def is_done(self) -> bool:
        return self.done

    def _initialize(self) -> None:
        if self.init_seed_state is None:
            self.init_seed_state = self.interpreter.get_init_state()
        if self.init_seed_state in self.book:
            self.done = True
            return
        self._queue = deque((BookBuilder.Seed(self.init_seed_state),))
        if self.allies is None:
            self.allies = frozenset((self.role,))
        else:
            if self.role not in self.allies:
                self.allies = frozenset((*self.allies, self.role))

    def _handle_seed(self, state: State) -> None:
        if state in self.book:
            return
        penultimate_state: Optional[State] = None
        final_state = state
        while final_state not in self.book and not self.interpreter.is_terminal(final_state):
            roles_in_control = Interpreter.get_roles_in_control(final_state)
            role_move_pairing = []

            for role in roles_in_control:
                legal_moves = self.interpreter.get_legal_moves_by_role(final_state, role)
                move = random.choice(tuple(legal_moves))
                role_move_pairing.append((role, move))

            turn = Turn(role_move_pairing)
            penultimate_state = final_state
            final_state = self.interpreter.get_next_state(final_state, turn)
        assert final_state in self.book or self.interpreter.is_terminal(final_state), "Condition: final_state is final"
        if penultimate_state is not None:
            self._queue.append(BookBuilder.Seed(penultimate_state))
            self._queue.append(BookBuilder.Search(penultimate_state, self.min_value, self.max_value))
        if final_state not in self.book:
            self.book[final_state] = self.evaluator(state=final_state, role=self.role, interpreter=self.interpreter)

        turn_state_pairs = self.interpreter.get_all_next_states(state)
        for _, next_state in turn_state_pairs:
            self._queue.append(BookBuilder.Seed(next_state))

    def _handle_search(self, state: State, alpha: _U_co, beta: _U_co) -> None:
        if state in self.book:
            return
        roles_in_control = Interpreter.get_roles_in_control(state)
        turn_state_pairs = self.interpreter.get_all_next_states(state)
        next_states = (state for _, state in turn_state_pairs)
        if len(roles_in_control) == 1 and RANDOM in roles_in_control:
            self._handle_search_random(state, next_states, alpha, beta)
            return
        maximizing_player = roles_in_control <= self.allies
        if maximizing_player:
            self._handle_search_maximizing_player(state, next_states, alpha, beta)
        else:
            self._handle_search_minimizing_player(state, next_states, alpha, beta)

    def _handle_search_random(self, state: State, next_states: Iterable[State], alpha: _U_co, beta: _U_co) -> None:
        to_be_evaluated: MutableSequence[State] = []
        values: MutableSequence[_U_co] = []
        for next_state in next_states:
            if next_state not in self.book:
                to_be_evaluated.append(next_state)
            else:
                values.append(self.book[next_state])

        if to_be_evaluated:
            self._queue.appendleft(BookBuilder.Search(state, alpha, beta))
            self._queue.extendleft(BookBuilder.Search(next_state, alpha, beta) for next_state in to_be_evaluated)
            return
        self.book[state] = sum(values) / len(values)

    def _handle_search_maximizing_player(
        self,
        state: State,
        next_states: Iterable[State],
        alpha: _U_co,
        beta: _U_co,
    ) -> None:
        value = self.min_value
        to_be_evaluated: MutableSequence[State] = []
        evaluated = False
        for next_state in next_states:
            if next_state not in self.book:
                to_be_evaluated.append(next_state)
                continue
            value = max(value, self.book[next_state])
            alpha = max(alpha, value)
            if value >= beta:
                evaluated = True
                break
        if not evaluated and to_be_evaluated:
            self._queue.appendleft(BookBuilder.Search(state, alpha, beta))
            self._queue.extendleft(BookBuilder.Search(next_state, alpha, beta) for next_state in to_be_evaluated)
            return
        self.book[state] = value

    def _handle_search_minimizing_player(
        self,
        state: State,
        next_states: Iterable[State],
        alpha: _U_co,
        beta: _U_co,
    ) -> None:
        value = self.max_value
        to_be_evaluated: MutableSequence[State] = []
        evaluated = False
        for next_state in next_states:
            if next_state not in self.book:
                to_be_evaluated.append(next_state)
                continue
            value = min(value, self.book[next_state])
            beta = min(beta, value)
            if value <= alpha:
                evaluated = True
                break
        if not evaluated and to_be_evaluated:
            self._queue.appendleft(BookBuilder.Search(state, alpha, beta))
            self._queue.extendleft(BookBuilder.Search(next_state, alpha, beta) for next_state in to_be_evaluated)
            return
        self.book[state] = value

    def _handle_search_max_sort_key(self, state: State) -> Tuple[bool, Optional[_U_co]]:
        return state in self.book, self.book.get(state)

    def _handle_search_min_sort_key(self, state: State) -> Tuple[bool, Optional[_U_co]]:
        return state in self.book, -self.book[state] if state in self.book else None


_QueueItem = Union[BookBuilder.Seed, BookBuilder.Search]
