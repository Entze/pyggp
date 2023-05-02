"""Perspectives for tree agents."""
import abc
import itertools
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

from typing_extensions import Self

from pyggp.interpreters import Interpreter, State, Turn, View


@dataclass(frozen=True)
class Perspective(abc.ABC):
    """Base class for all perspectives."""

    @classmethod
    def from_state(cls, state: State) -> Self:
        """Creates a perspective from a state.

        Args:
            state: State to create the perspective from

        Returns:
            Perspective

        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_state_record(self) -> Optional[State]:
        """Gets the state record for this perspective.

        Returns:
            State record

        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_view_record(self) -> Optional[View]:
        """Gets the view record for this perspective.

        Returns:
            View record

        """
        raise NotImplementedError

    def get_next_perspectives(self, interpreter: Interpreter) -> Iterator[Tuple[Turn, Self]]:
        """Gets the next perspectives for this perspective.

        Args:
            interpreter: Interpreter to use for generating next perspectives

        Yields:
            turn, perspective pairs

        """
        raise NotImplementedError


@dataclass(frozen=True)
class DeterministicPerspective(Perspective):
    """Deterministic perspective.

    Usable if the game is deterministic. View is equivalent to state.

    """

    state: State
    "Current state."

    @classmethod
    def from_state(cls, state: State) -> Self:
        """Creates a perspective from a state.

        Args:
            state: State to create the perspective from

        Returns:
            Perspective

        """
        return cls(state)

    def get_state_record(self) -> Optional[State]:
        """Gets the state record for this perspective.

        Returns:
            State record

        """
        return self.state

    def get_view_record(self) -> Optional[View]:
        """Gets the view record for this perspective.

        Returns:
            View record

        """
        return None

    def get_next_perspectives(self, interpreter: Interpreter) -> Iterator[Tuple[Turn, Self]]:
        """Gets the next perspectives for this perspective.

        Args:
            interpreter: Interpreter to use for generating next perspectives

        Yields:
            turn, perspective pairs

        """
        if interpreter.is_terminal(self.state):
            return
        roles_in_control = Interpreter.get_roles_in_control(self.state)
        all_role_move_pairs = set()
        for role in roles_in_control:
            legal_moves = interpreter.get_legal_moves_by_role(self.state, role)
            role_move_pairs = set()
            for move in legal_moves:
                role_move_pairs.add((role, move))
            all_role_move_pairs.add(frozenset(role_move_pairs))
        for turn_role_move_pairs in itertools.product(*all_role_move_pairs):
            turn = Turn(frozenset(turn_role_move_pairs))
            next_state = interpreter.get_next_state(self.state, *turn.as_plays())
            yield turn, self.from_state(next_state)
