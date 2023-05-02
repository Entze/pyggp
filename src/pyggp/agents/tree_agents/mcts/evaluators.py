"""Evaluators for the MCTS agents."""
import random
from dataclasses import dataclass

from pyggp.agents.tree_agents.evaluators import Evaluator
from pyggp.agents.tree_agents.mcts.valuations import PlayoutValuation
from pyggp.agents.tree_agents.perspectives import DeterministicPerspective
from pyggp.interpreters import Interpreter, Role, Turn


@dataclass
class LightPlayoutEvaluator(Evaluator[DeterministicPerspective, PlayoutValuation]):
    """Evaluator that rolls out the perspective by random moves."""

    role: Role
    "Role of the agent."

    def evaluate(self, interpreter: Interpreter, perspective: DeterministicPerspective) -> PlayoutValuation:
        """Evaluates the node.

        Does random moves until the game ends and returns a PlayoutValuation with 1 mapped to the rank of the role.

        Args:
            interpreter: Interpreter
            perspective: Current perspective

        Returns:
            Valuation of the node

        """
        state = perspective.state
        while not interpreter.is_terminal(state):
            roles_in_control = Interpreter.get_roles_in_control(state)
            role_move_pairing = []

            for role in roles_in_control:
                legal_moves = interpreter.get_legal_moves_by_role(state, role)
                move = random.choice(tuple(legal_moves))
                role_move_pairing.append((role, move))

            turn = Turn(frozenset(role_move_pairing))
            state = interpreter.get_next_state(state, *turn.as_plays())

        goals = interpreter.get_goals(state)
        ranks = Interpreter.get_ranks(goals)
        return PlayoutValuation(ranks={ranks[self.role]: 1})
