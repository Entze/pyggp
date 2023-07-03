import abc
import logging
import time
from dataclasses import dataclass, field
from typing import Final, Generic, Mapping, Optional, Protocol, TypeVar

from pyggp._logging import format_ns, inflect_without_count, log_time
from pyggp.agents import Agent, InterpreterAgent
from pyggp.engine_primitives import Move, View

log: logging.Logger = logging.getLogger("pyggp")

_K = TypeVar("_K")
_E = TypeVar("_E")


class TreeAgent(Agent, Protocol[_K, _E]):
    def update(self, ply: int, view: View, total_time_ns: int) -> None:
        ...

    def search(self, search_time_ns: int) -> None:
        ...

    def descend(self, key: _K) -> None:
        ...

    def get_key_to_evaluation(self) -> Mapping[_K, _E]:
        ...


ONE_S_IN_NS: Final[int] = 1_000_000_000


@dataclass
class AbstractTreeAgent(InterpreterAgent, TreeAgent[_K, _E], Generic[_K, _E], abc.ABC):
    max_logged_options: int = field(default=10)
    update_time_quota: float = field(default=1.0)
    search_time_quota: float = field(default=1.0)

    @abc.abstractmethod
    def update(self, ply: int, view: View, total_time_ns: int) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def search(self, search_time_ns: int) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def descend(self, key: _K) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_key_to_evaluation(self) -> Mapping[_K, _E]:
        raise NotImplementedError

    def calculate_move(self, ply: int, total_time_ns: int, view: View) -> Move:
        used_time = time.monotonic_ns()
        with log_time(
            log,
            logging.DEBUG,
            inflect_without_count("tree", count=int(hasattr(self, "tree"))),
            begin_msg=f"Updating %s",
            end_msg=f"Updated %s",
            abort_msg=f"Aborted updating %s",
        ):
            self.update(ply, view, total_time_ns)

        used_time = time.monotonic_ns() - used_time

        search_time_ns = self._get_timeout_ns(total_time_ns, used_time)

        with log_time(
            log=log,
            level=logging.DEBUG,
            begin_msg=f"Searching for at most {format_ns(search_time_ns)}",
            end_msg="Searched",
            abort_msg="Aborted searching",
        ):
            self.search(search_time_ns)

        key_to_evaluation = self.get_key_to_evaluation()

        assert key_to_evaluation, "Assumption: Non-final node implies at least one option."

        move_to_aggregation = self._get_move_to_aggregation(key_to_evaluation)
        best_move = max(move_to_aggregation, key=move_to_aggregation.get)
        self._log_options(move_to_aggregation)

        filtered_keys = {
            key: evaluation for key, evaluation in key_to_evaluation.items() if self._key_to_move(key) == best_move
        }
        key = max(filtered_keys, key=filtered_keys.get)

        self._log_choice(best_move, move_to_aggregation, filtered_keys)

        self.descend(key)
        return best_move

    @property
    def _net_zero_time_ns(self) -> int:
        return self.playclock_config.increment_ns + self.playclock_config.delay_ns

    def _get_timeout_ns(
        self,
        total_time_ns: int,
        used_time_ns: int,
        *,
        net_zero_time_ns: Optional[int] = None,
        zero_time_ns: Optional[int] = None,
        scale: float = 0.975,
        min_buffer: int = ONE_S_IN_NS,
        max_buffer: int = 5 * ONE_S_IN_NS,
    ) -> int:
        if net_zero_time_ns is None:
            net_zero_time_ns = self._net_zero_time_ns
        net_zero_time_ns -= used_time_ns
        if zero_time_ns is None:
            zero_time_ns = total_time_ns + self.playclock_config.delay_ns
        zero_time_ns -= used_time_ns

        remaining_moves = max(1, self._guess_remaining_moves()) if total_time_ns > 0 else 1
        using_time = max(0, total_time_ns // remaining_moves)

        LOG_BUFFER = ONE_S_IN_NS if log.level == logging.DEBUG else 0
        MIN_BUFFER = min_buffer + LOG_BUFFER
        MAX_BUFFER = max_buffer + LOG_BUFFER

        max_time = int(zero_time_ns * scale) - MIN_BUFFER
        min_time = int(net_zero_time_ns * scale) - MAX_BUFFER

        timeout_ns = int((net_zero_time_ns + using_time) * scale)
        timeout_ns = max(0, timeout_ns, min_time)
        timeout_ns = min(timeout_ns, max_time)
        return timeout_ns

    def _guess_remaining_moves(self) -> int:
        return 128

    def _log_options(self, move_to_aggregation: Mapping[Move, _E], log_level: int = logging.DEBUG) -> None:
        if log.level > log_level:
            return

        msg_parts = []

        nr_of_options = len(move_to_aggregation)
        if nr_of_options < self.max_logged_options:
            msg_parts.append("Options:")
        else:
            msg_parts.append(f"Options (out of {nr_of_options}):")

        sorted_moves = sorted(move_to_aggregation, key=move_to_aggregation.get, reverse=True)
        for move in sorted_moves[: self.max_logged_options]:
            evaluation = move_to_aggregation[move]
            msg_parts.append(self._move_evaluation_as_str(move, evaluation))

        log.debug("\n".join(msg_parts))

    @abc.abstractmethod
    def _get_move_to_aggregation(self, key_to_evaluation: Mapping[_K, _E]) -> Mapping[Move, _E]:
        raise NotImplementedError

    def _move_evaluation_as_str(
        self,
        move: Move,
        evaluation: _E,
        *,
        sep: str = ":",
        pre_move: str = "",
        post_move: str = "",
        pre_evaluation: str = " ",
        post_evaluation: str = "",
    ) -> str:
        return f"{pre_move}{move}{post_move}{sep}{pre_evaluation}{self._evaluation_as_str(evaluation)}{post_evaluation}"

    def _evaluation_as_str(self, evaluation: _E) -> str:
        return str(evaluation)

    @abc.abstractmethod
    def _key_to_move(self, key: _K) -> Move:
        raise NotImplementedError

    def _log_choice(
        self,
        move: Move,
        move_to_aggregation: Mapping[Move, _E],
        filtered_keys: Mapping[_K, _E],
        log_level: int = logging.INFO,
    ) -> None:
        if log.level > log_level:
            return

        evaluation = move_to_aggregation[move]

        best_key = max(filtered_keys, key=filtered_keys.get)
        best_key_evaluation = filtered_keys[best_key]
        worst_key = min(filtered_keys, key=filtered_keys.get)
        worst_key_evaluation = filtered_keys[worst_key]

        log.info(
            "Chose %s (%s, \\[%s, %s])",
            move,
            self._evaluation_as_str(evaluation),
            self._evaluation_as_str(worst_key_evaluation),
            self._evaluation_as_str(best_key_evaluation),
        )
