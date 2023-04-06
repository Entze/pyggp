"""Abstract representation of a match."""
import concurrent.futures as concurrent_futures
from dataclasses import dataclass, field
from typing import Any, Final, Literal, Mapping, MutableMapping, MutableSequence, Sequence, Union

import exceptiongroup
import rich.progress as rich_progress
from typing_extensions import TypeAlias

import pyggp.game_description_language as gdl
from pyggp.actors import Actor
from pyggp.exceptions.actor_exceptions import TimeoutActorError
from pyggp.exceptions.match_exceptions import DidNotStartMatchError, MatchError
from pyggp.gameclocks import GameClock
from pyggp.interpreters import Interpreter, Role, State

Disqualification: TypeAlias = Literal["DNS(Timeout)", "DNF(Timeout)", "DNF(Illegal Move)"]
"Disqualifications."

_DNS_TIMEOUT: Final[Literal["DNS(Timeout)"]] = "DNS(Timeout)"
_DNF_TIMEOUT: Final[Literal["DNF(Timeout)"]] = "DNF(Timeout)"
_DNF_ILLEGAL_MOVE: Final[Literal["DNF(Illegal Move)"]] = "DNF(Illegal Move)"

_DISQUALIFICATIONS: Final[Sequence[Disqualification]] = (_DNS_TIMEOUT, _DNF_TIMEOUT, _DNF_ILLEGAL_MOVE)


@dataclass
class Match:
    """Representation of a match."""

    # region Inner Classes
    # endregion

    # region Attributes and Properties

    ruleset: gdl.Ruleset
    "Ruleset of the match."
    interpreter: Interpreter
    "Interpreter of the match."
    role_actor_map: Mapping[Role, Actor]
    "Mapping of roles to actors."
    role_startclock_configuration_map: Mapping[Role, GameClock.Configuration]
    "Mapping of roles to startclock configurations."
    role_playclock_configuration_map: Mapping[Role, GameClock.Configuration]
    "Mapping of roles to playclock configurations."
    states: MutableSequence[State] = field(default_factory=list)
    "Sequence of states."
    utilities: MutableMapping[Role, Union[int, None, Disqualification]] = field(default_factory=dict)
    "Mapping of roles to utilities."

    # endregion

    # region Methods

    def start(self, polling_interval: float = 0.1) -> None:
        """Start the match.

        Args:
            polling_interval: Interval to poll for updates in seconds

        """
        role_future_map: MutableMapping[Role, concurrent_futures.Future[None]] = {}
        role_taskid_map: MutableMapping[Role, rich_progress.TaskID] = {}
        monitor_startclock = GameClock(total_time_ns=0, increment_ns=0, delay_ns=0)
        exceptions: MutableSequence[MatchError] = []
        with concurrent_futures.ThreadPoolExecutor() as executor, rich_progress.Progress(
            transient=True,
            auto_refresh=False,
        ) as progress:
            self._start_init(
                role_future_map=role_future_map,
                executor=executor,
                role_taskid_map=role_taskid_map,
                progress=progress,
                monitor_startclock=monitor_startclock,
            )
            self._start_monitor(
                role_future_map=role_future_map,
                role_taskid_map=role_taskid_map,
                progress=progress,
                monitor_startclock=monitor_startclock,
                exceptions=exceptions,
                polling_interval=polling_interval,
            )
            self._start_collect(role_future_map=role_future_map, exceptions=exceptions)
        if exceptions:
            message = "Errors during start of match"
            raise exceptiongroup.ExceptionGroup(message, exceptions)

    def _start_init(
        self,
        *,
        role_future_map: MutableMapping[Role, concurrent_futures.Future[None]],
        executor: concurrent_futures.ThreadPoolExecutor,
        role_taskid_map: MutableMapping[Role, rich_progress.TaskID],
        progress: rich_progress.Progress,
        monitor_startclock: GameClock,
    ) -> None:
        total_time: int = 10_000_000_000
        for role in self.role_actor_map:
            role_future_map[role] = self._kick_off_start(role=role, executor=executor)
            startclock_configuration = self.role_startclock_configuration_map[role]
            total = startclock_configuration.total_time + startclock_configuration.delay
            if total == float("inf"):
                total = 60.0 * 60.0  # 1 hour in seconds
            total_time = max(total_time, int(total * 1e9))
            role_taskid_map[role] = progress.add_task(f"{Role} (Start)", total=total)
        monitor_startclock.total_time_ns = total_time

    def _start_monitor(
        self,
        *,
        monitor_startclock: GameClock,
        role_taskid_map: Mapping[Role, rich_progress.TaskID],
        role_future_map: Mapping[Role, concurrent_futures.Future[None]],
        progress: rich_progress.Progress,
        exceptions: MutableSequence[MatchError],
        polling_interval: float = 0.1,
    ) -> None:
        all_started = False
        while not monitor_startclock.is_expired and not all_started:
            all_started = True
            for role, actor in self.role_actor_map.items():
                task_id = role_taskid_map[role]
                future = role_future_map[role]
                started = False
                try:
                    started = Match._monitor(
                        task_id=task_id,
                        future=future,
                        progress=progress,
                        monitor_clock=monitor_startclock,
                        polling_interval=polling_interval,
                        skip=self.utilities.get(role) in _DISQUALIFICATIONS,
                    )
                except TimeoutActorError as timeout_exception:
                    self.utilities[role] = _DNS_TIMEOUT
                    dns_exception = DidNotStartMatchError(actor=actor, role=role)
                    dns_exception.__cause__ = timeout_exception
                    exceptions.append(dns_exception)
                all_started = all_started and started
                for task in progress.tasks:
                    if task.stop_time is None:
                        advance = monitor_startclock.last_delta or 0.0
                        progress.advance(task.id, advance)

                progress.refresh()

    def _start_collect(
        self,
        *,
        role_future_map: Mapping[Role, concurrent_futures.Future[None]],
        exceptions: MutableSequence[MatchError],
    ) -> None:
        for role, actor in self.role_actor_map.items():
            startclock_configuration = self.role_startclock_configuration_map[role]
            future = role_future_map[role]
            if future.running() and self.utilities.get(role) is None:
                self.utilities[role] = _DNS_TIMEOUT
                available_time = startclock_configuration.total_time + startclock_configuration.delay
                timeout_exception = TimeoutActorError(role=role, available_time=available_time)
                dns_exception = DidNotStartMatchError(actor=actor, role=role)
                dns_exception.__cause__ = timeout_exception
                exceptions.append(dns_exception)

    def _kick_off_start(
        self,
        role: Role,
        executor: concurrent_futures.ThreadPoolExecutor,
    ) -> concurrent_futures.Future[None]:
        actor = self.role_actor_map[role]
        startclock_configuration = self.role_startclock_configuration_map[role]
        playclock_configuration = self.role_playclock_configuration_map[role]
        return executor.submit(
            actor.send_start,
            role=role,
            ruleset=self.ruleset,
            startclock_configuration=startclock_configuration,
            playclock_configuration=playclock_configuration,
        )

    @staticmethod
    # Disables PLR0913 (too many arguments to function call) and FBT001 (Boolean positional arg in function definition)
    # Because: This is a private method.
    def _monitor(  # noqa: PLR0913
        task_id: rich_progress.TaskID,
        future: concurrent_futures.Future[Any],
        progress: rich_progress.Progress,
        monitor_clock: GameClock,
        polling_interval: float = 0.1,
        skip: bool = False,  # noqa: FBT001
    ) -> bool:
        if skip or future.done():
            for task in progress.tasks:
                if task.id == task_id and task.stop_time is None:
                    progress.stop_task(task_id)
            return True
        timeout = min(polling_interval, monitor_clock.get_timeout(slack=polling_interval / 2))
        done = True
        try:
            with monitor_clock:
                future.result(timeout=timeout)
        except TimeoutError:
            done = False
        if done:
            for task in progress.tasks:
                if task.id == task_id and task.stop_time is None:
                    progress.stop_task(task_id)
        return done

    def execute_ply(self) -> None:
        """Execute a ply."""

    def conclude(self) -> None:
        """Conclude the match."""

    def abort(self) -> None:
        """Abort the match."""

    # endregion
