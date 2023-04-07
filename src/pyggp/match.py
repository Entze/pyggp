"""Abstract representation of a match."""
import abc
import concurrent.futures as concurrent_futures
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Generic,
    Iterable,
    Literal,
    Mapping,
    MutableMapping,
    MutableSequence,
    Sequence,
    TypedDict,
    TypeVar,
    Union,
)

import exceptiongroup
import rich.progress as rich_progress
from typing_extensions import TypeAlias

import pyggp.game_description_language as gdl
from pyggp._logging import format_timedelta, log
from pyggp.actors import Actor
from pyggp.exceptions.actor_exceptions import ActorError, PlayclockIsNoneActorError, TimeoutActorError
from pyggp.exceptions.match_exceptions import (
    DidNotFinishMatchError,
    DidNotStartMatchError,
    MatchError,
    TimeoutMatchError,
)
from pyggp.gameclocks import GameClock
from pyggp.interpreters import ClingoInterpreter, Interpreter, Move, Role, State, Turn, View

Disqualification: TypeAlias = Literal["DNS(Timeout)", "DNF(Timeout)", "DNF(Illegal Move)"]
"Disqualifications."

_DNS_TIMEOUT: Final[Literal["DNS(Timeout)"]] = "DNS(Timeout)"
_DNF_TIMEOUT: Final[Literal["DNF(Timeout)"]] = "DNF(Timeout)"
_DNF_ILLEGAL_MOVE: Final[Literal["DNF(Illegal Move)"]] = "DNF(Illegal Move)"

_DISQUALIFICATIONS: Final[Sequence[Disqualification]] = (_DNS_TIMEOUT, _DNF_TIMEOUT, _DNF_ILLEGAL_MOVE)

if TYPE_CHECKING:  # See https://github.com/python/typing/discussions/835#discussioncomment-1193041
    # To be fixed once 3.8 is no longer supported.
    Future_None = concurrent_futures.Future[None]
    Future_Any = concurrent_futures.Future[Any]
    Future_Move = concurrent_futures.Future[Move]
else:
    Future_None = concurrent_futures.Future
    Future_Any = concurrent_futures.Future
    Future_Move = concurrent_futures.Future

R = TypeVar("R")
A = TypeVar("A")
S = TypeVar("S", bound=Mapping[str, Any])


@dataclass
class _SignalProcessor(Generic[R, S, A], abc.ABC):
    executor: concurrent_futures.ThreadPoolExecutor
    progress: rich_progress.Progress
    role_actor_map: Mapping[Role, Actor]
    roles: Iterable[Role]
    role_future_map: MutableMapping[Role, concurrent_futures.Future[R]] = field(default_factory=dict)
    role_response_map: MutableMapping[Role, R] = field(default_factory=dict)
    role_interrupted_map: MutableMapping[Role, bool] = field(default_factory=dict)
    role_taskid_map: MutableMapping[Role, rich_progress.TaskID] = field(default_factory=dict)
    role_utility_map: MutableMapping[Role, Union[int, Disqualification, None]] = field(default_factory=dict)
    polling_interval: float = field(default=0.1)
    total_time: float = field(init=False, default=5.0)
    monitor_clock: GameClock = field(init=False)
    exceptions: MutableSequence[MatchError] = field(default_factory=list, init=False)
    signal_name: ClassVar[str] = "Signal"

    @property
    def all_done(self) -> bool:
        return all(self.is_done(role) for role in self.roles)

    def is_done(self, role: Role) -> bool:
        return role in self.role_response_map or self.role_interrupted_map.get(role, False)

    def is_still_running(self, role: Role) -> bool:
        return role not in self.role_response_map and not self.role_interrupted_map.get(role, False)

    def init(self) -> None:
        log.debug(
            "Will send [italic]%s[/italic] to %s",
            self.signal_name,
            ", ".join(f"[yellow italic]{role}[/yellow italic]" for role in self.roles),
        )
        role_timeout_map = {}
        for role in self.roles:
            args = self._get_signal_args(role)
            log.debug("Sending [italic]%s[/italic] to [yellow italic]%s[/yellow italic]", self.signal_name, role)
            future = self._signal(**args)
            self.role_future_map[role] = future
            role_timeout = self._get_timeout(role)
            role_timeout_map[role] = role_timeout
            log.debug(
                "Actor of [yellow italic]%s[/yellow italic] has [green]%s[/green] to respond",
                role,
                format_timedelta(role_timeout),
                extra={"highlighter": None},
            )
            display_total = role_timeout if role_timeout != float("inf") else 60.0 * 60.0 * 24.0
            task_id = self.progress.add_task(f"{role} ({self.signal_name})", total=display_total)
            self.role_taskid_map[role] = task_id

        self.total_time = max(5.0, max(role_timeout_map.values(), default=0.0) + self.polling_interval)
        log.debug(
            "Waiting for a response to [italic]%s[/italic] for a maximum of [green]%s[/green]",
            self.signal_name,
            format_timedelta(self.total_time),
            extra={"highlighter": None},
        )
        self.monitor_clock = GameClock.from_configuration(
            GameClock.Configuration(total_time=self.total_time, increment=0.0, delay=0.0),
        )

    @abc.abstractmethod
    def _get_signal_args(self, role: Role) -> S:
        raise NotImplementedError

    @abc.abstractmethod
    def _signal(self, *args: Any, **kwargs: Any) -> concurrent_futures.Future[R]:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_timeout(self, role: Role) -> float:
        raise NotImplementedError

    def monitor(self) -> None:
        done = False
        while not done and not self.monitor_clock.is_expired:
            done = True
            for role, future in self.role_future_map.items():
                if self.is_done(role):
                    continue

                for progress_role in filter(self.is_still_running, self.roles):
                    task_id = self.role_taskid_map[progress_role]
                    self.progress.advance(task_id=task_id, advance=self.polling_interval)
                self.progress.refresh()

                response = None
                responded = False
                try:
                    with self.monitor_clock:
                        response = future.result(self.polling_interval)
                    responded = True
                except TimeoutError:
                    pass
                except ActorError as inner_exception:
                    self.role_interrupted_map[role] = True
                    exception = self._get_exception(role, inner_exception)
                    self.exceptions.append(exception)

                if responded:
                    # Disable mypy. Because: Response may be None, but it is not Optional.
                    self.role_response_map[role] = response  # type: ignore[assignment]
                    task_id = self.role_taskid_map[role]
                    self.progress.stop_task(task_id)
                    log.debug(
                        "Received response ([italic]%s[/italic]) from [yellow italic]%s[/yellow italic]",
                        self.signal_name,
                        role,
                    )
                else:
                    done = False

    @abc.abstractmethod
    def _get_exception(self, role: Role, inner_exception: ActorError) -> MatchError:
        raise NotImplementedError

    def collect(self) -> None:
        for role in self.roles:
            if self.is_still_running(role):
                self.role_interrupted_map[role] = True
                role_timeout = self._get_timeout(role)
                inner_exception = TimeoutActorError(available_time=role_timeout, delta=self.total_time, role=role)
                exception = self._get_exception(role, inner_exception)
                self.exceptions.append(exception)
                self.role_utility_map[role] = self._get_disqualification_utility(role, exception)
            else:
                response = self.role_response_map[role]
                self.role_utility_map[role] = self._get_utility(role, response)

    @abc.abstractmethod
    def _get_disqualification_utility(self, role: Role, exception: MatchError) -> Union[int, Disqualification, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_utility(self, role: Role, response: R) -> Union[int, Disqualification, None]:
        raise NotImplementedError

    def process(self) -> A:
        if not self.all_done or self.exceptions:
            message = f"Errors while processing {self.signal_name}"
            raise exceptiongroup.ExceptionGroup(message, self.exceptions)
        return self._aggregate_responses()

    @abc.abstractmethod
    def _aggregate_responses(self) -> A:
        raise NotImplementedError


@dataclass
class _StartProcessor(_SignalProcessor[None, "_StartProcessor.StartArgs", None]):
    ruleset: gdl.Ruleset = field(default_factory=gdl.Ruleset)
    role_startclock_configuration_map: Mapping[Role, GameClock.Configuration] = field(default_factory=dict)
    role_playclock_configuration_map: Mapping[Role, GameClock.Configuration] = field(default_factory=dict)

    signal_name: ClassVar[str] = "start"

    class StartArgs(TypedDict):
        actor: Actor
        role: Role
        ruleset: gdl.Ruleset
        startclock_configuration: GameClock.Configuration
        playclock_configuration: GameClock.Configuration

    def _get_signal_args(self, role: Role) -> StartArgs:
        return _StartProcessor.StartArgs(
            actor=self.role_actor_map[role],
            role=role,
            ruleset=self.ruleset,
            startclock_configuration=self.role_startclock_configuration_map[role],
            playclock_configuration=self.role_playclock_configuration_map[role],
        )

    def _signal(
        self,
        *,
        actor: Actor,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_configuration: GameClock.Configuration,
        playclock_configuration: GameClock.Configuration,
    ) -> concurrent_futures.Future[None]:
        return self.executor.submit(
            actor.send_start,
            role=role,
            ruleset=ruleset,
            startclock_configuration=startclock_configuration,
            playclock_configuration=playclock_configuration,
        )

    def _get_timeout(self, role: Role) -> float:
        startclock_configuration = self.role_startclock_configuration_map[role]
        return startclock_configuration.total_time + startclock_configuration.delay

    def _get_exception(self, role: Role, inner_exception: ActorError) -> MatchError:
        actor = self.role_actor_map[role]
        exception = DidNotStartMatchError(actor=actor, role=role)
        exception.__cause__ = inner_exception
        return exception

    def _get_disqualification_utility(
        self,
        # Disables ARG002 (Unused method argument). Because method overrides abstract method.
        role: Role,  # noqa: ARG002
        exception: MatchError,  # noqa: ARG002
    ) -> Union[int, Disqualification, None]:
        return _DNS_TIMEOUT

    def _get_utility(
        self,
        # Disables ARG002 (Unused method argument). Because method overrides abstract method.
        role: Role,  # noqa: ARG002
        response: None,  # noqa: ARG002
    ) -> Union[int, Disqualification, None]:
        return None

    def _aggregate_responses(self) -> None:
        return None


@dataclass
class _PlayProcessor(_SignalProcessor[Move, "_PlayProcessor.PlayArgs", Turn]):
    ply: int = 0
    state: State = field(default_factory=lambda: State(frozenset()))
    interpreter: Interpreter = field(default_factory=ClingoInterpreter)
    signal_name: ClassVar[str] = "play"

    class PlayArgs(TypedDict):
        actor: Actor
        ply: int
        view: View

    def _get_signal_args(self, role: Role) -> PlayArgs:
        view = self.interpreter.get_sees_by_role(current=self.state, role=role)
        return _PlayProcessor.PlayArgs(actor=self.role_actor_map[role], ply=self.ply, view=view)

    def _signal(self, *, actor: Actor, ply: int, view: View) -> concurrent_futures.Future[Move]:
        return self.executor.submit(actor.send_play, ply=ply, view=view)

    def _get_timeout(self, role: Role) -> float:
        actor = self.role_actor_map[role]
        if actor.playclock is None:
            raise PlayclockIsNoneActorError
        return actor.playclock.get_timeout()

    def _get_exception(self, role: Role, inner_exception: ActorError) -> MatchError:
        actor = self.role_actor_map[role]
        exception: MatchError
        if isinstance(inner_exception, TimeoutActorError):
            exception = TimeoutMatchError(actor=actor, ply=self.ply, role=role)
        else:
            exception = DidNotFinishMatchError(actor=actor, ply=self.ply, role=role)
        exception.__cause__ = inner_exception
        return exception

    def _get_disqualification_utility(
        self,
        # Disables ARG002 (Unused method argument). Because method overrides abstract method.
        role: Role,  # noqa: ARG002
        exception: MatchError,  # noqa: ARG002
    ) -> Union[int, Disqualification, None]:
        return _DNF_TIMEOUT

    def _get_utility(self, role: Role, response: Move) -> Union[int, Disqualification, None]:
        is_legal = self.interpreter.is_legal(current=self.state, role=role, move=response)
        if not is_legal:
            return _DNF_ILLEGAL_MOVE
        return None

    def _aggregate_responses(self) -> Turn:
        return Turn.from_mapping(self.role_response_map)


@dataclass
class Match:
    """Representation of a match."""

    # region Inner Classes
    # endregion

    # region Attributes and Properties

    ruleset: gdl.Ruleset = field(repr=False)
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

    @property
    def is_finished(self) -> bool:
        """Whether the match is finished."""
        return bool(self.utilities) or self.interpreter.is_terminal(self.states[-1])

    # endregion

    # region Methods

    def start(self, polling_interval: float = 0.1) -> None:
        """Start the match.

        Args:
            polling_interval: Interval to poll for updates in seconds

        """
        with concurrent_futures.ThreadPoolExecutor() as executor, rich_progress.Progress(
            transient=True,
            auto_refresh=False,
        ) as progress:
            processor = _StartProcessor(
                executor=executor,
                progress=progress,
                role_actor_map=self.role_actor_map,
                roles=self.role_actor_map.keys(),
                ruleset=self.ruleset,
                role_startclock_configuration_map=self.role_startclock_configuration_map,
                role_playclock_configuration_map=self.role_playclock_configuration_map,
                polling_interval=polling_interval,
            )
            processor.init()
            processor.monitor()
            processor.collect()
            processor.process()
        initial_state = self.interpreter.get_init_state()
        self.states = [initial_state]

    def execute_ply(
        self,
        polling_interval: float = 0.1,
    ) -> None:
        """Execute the next ply."""
        current_state = self.states[-1]
        ply = len(self.states) - 1
        roles_in_control = self.interpreter.get_roles_in_control(current_state)
        humans_in_control = any(self.role_actor_map[role].is_human_actor for role in roles_in_control)
        with concurrent_futures.ThreadPoolExecutor() as executor, rich_progress.Progress(
            transient=True,
            auto_refresh=False,
            disable=humans_in_control,
        ) as progress:
            processor = _PlayProcessor(
                executor=executor,
                progress=progress,
                role_actor_map=self.role_actor_map,
                roles=roles_in_control,
                state=current_state,
                ply=ply,
                interpreter=self.interpreter,
                polling_interval=polling_interval,
            )
            processor.init()
            processor.monitor()
            processor.collect()
            turn = processor.process()
        next_state = self.interpreter.get_next_state(current_state, *turn.as_plays())
        self.states.append(next_state)

    def conclude(self) -> None:
        """Conclude the match."""

    def abort(self) -> None:
        """Abort the match."""

    # endregion
