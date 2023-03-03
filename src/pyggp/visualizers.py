from typing import MutableSequence

from pyggp.gdl import State
from pyggp.match import MatchResult


class Visualizer:
    def __init__(self):
        self._states: MutableSequence[State | None] = []

    def update_state(self, state: State, move_nr: int | None = None) -> None:
        if move_nr is None:
            self._states.append(state)
            return
        if move_nr >= len(self._states):
            self._states.extend([None] * ((move_nr + 1) - len(self._states)))

        self._states[move_nr] = state

    def update_result(self, result: MatchResult) -> None:
        raise NotImplementedError

    def update_abort(self) -> None:
        raise NotImplementedError

    def draw(self) -> None:
        raise NotImplementedError


class NullVisualizer:  # pragma: no cover
    def update_state(self, state: State, move_nr: int | None = None) -> None:
        pass

    def update_result(self, result: MatchResult) -> None:
        pass

    def update_abort(self) -> None:
        pass

    def draw(self) -> None:
        pass
