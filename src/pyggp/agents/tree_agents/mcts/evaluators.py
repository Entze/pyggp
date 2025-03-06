"""Evaluators for the MCTS agents."""

import random
from dataclasses import dataclass, field
from typing import Any, Optional, TypeVar

from pyggp.agents.tree_agents.evaluators import Evaluator
from pyggp.books import Book
from pyggp.engine_primitives import Role, State, Turn
from pyggp.interpreters import Interpreter

_U_co = TypeVar("_U_co", covariant=True)


@dataclass
class LightPlayoutEvaluator(Evaluator[_U_co]):
    """Evaluator that rolls out the perspective by random moves."""

    role: Role
    "Role."
    final_state_evaluator: Evaluator[_U_co]
    "Evaluator for the final state."
    book: Optional[Book[_U_co]] = field(default=None, repr=False)
    accesses: int = field(default=0, repr=False)
    hits: int = field(default=0, repr=False)

    # Disables override checks. Because: Typecheckers cannot infer that *args includes any arguments.
    # noinspection PyMethodOverriding
    def __call__(  # type: ignore[override]
        self,
        state: State,
        interpreter: Interpreter,
        role: Optional[Role] = None,
        *args: Any,
        **kwargs: Any,
    ) -> _U_co:
        self.accesses += 1
        while not interpreter.is_terminal(state) and (self.book is None or state not in self.book):
            roles_in_control = Interpreter.get_roles_in_control(state)
            role_move_pairing = []

            for role in roles_in_control:
                legal_moves = interpreter.get_legal_moves_by_role(state, role)
                move = random.choice(tuple(legal_moves))
                role_move_pairing.append((role, move))

            turn = Turn(role_move_pairing)
            state = interpreter.get_next_state(state, turn)

        if self.book is not None and state in self.book:
            self.hits += 1
            return self.book[state]

        return self.final_state_evaluator(state, *args, role=self.role, interpreter=interpreter, **kwargs)
