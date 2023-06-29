"""Abstract representation of a match."""
import abc
import concurrent.futures as concurrent_futures
import contextlib
import logging
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
    Tuple,
    TypedDict,
    TypeVar,
    Union,
)

import exceptiongroup
import rich.progress as rich_progress
from typing_extensions import TypeAlias

import pyggp.game_description_language as gdl
from pyggp._logging import format_id, format_timedelta, rich
from pyggp.actors import Actor
from pyggp.engine_primitives import Move, Role, State, Turn, View
from pyggp.exceptions.actor_exceptions import ActorError, TimeoutActorError
from pyggp.exceptions.match_exceptions import (
    DidNotFinishMatchError,
    DidNotStartMatchError,
    IllegalMoveMatchError,
    MatchError,
    TimeoutMatchError,
)
from pyggp.gameclocks import GameClock
from pyggp.interpreters import ClingoInterpreter, Interpreter

log: logging.Logger = logging.getLogger("pyggp")

Disqualification: TypeAlias = Literal["DNS(Timeout)", "DNF(Timeout)", "DNF(Illegal Move)"]
"Disqualifications."

_DNS_TIMEOUT: Final[Literal["DNS(Timeout)"]] = "DNS(Timeout)"
_DNF_TIMEOUT: Final[Literal["DNF(Timeout)"]] = "DNF(Timeout)"
_DNF_ILLEGAL_MOVE: Final[Literal["DNF(Illegal Move)"]] = "DNF(Illegal Move)"

_DISQUALIFICATIONS: Final[Sequence[Disqualification]] = (_DNS_TIMEOUT, _DNF_TIMEOUT, _DNF_ILLEGAL_MOVE)

R = TypeVar("R")
A = TypeVar("A")
S = TypeVar("S", bound=Mapping[str, Any])

if TYPE_CHECKING:  # See https://github.com/python/typing/discussions/835#discussioncomment-1193041
    # To be fixed once 3.8 is no longer supported.
    Future_None = concurrent_futures.Future[None]
    Future_Any = concurrent_futures.Future[Any]
    Future_Move = concurrent_futures.Future[Move]
    Future_R = concurrent_futures.Future[R]


else:
    Future_None = concurrent_futures.Future
    Future_Any = concurrent_futures.Future
    Future_Move = concurrent_futures.Future
    Future_R = concurrent_futures.Future


@dataclass
class _SignalProcessor(Generic[R, S, A], abc.ABC):
    executor: concurrent_futures.ThreadPoolExecutor
    progress: rich_progress.Progress
    role_actor_map: Mapping[Role, Actor]
    roles: Iterable[Role]
    # Disables mypy. Because: Hack around Python 3.8's type system limitations. Future_R is a Future[R] in Python 3.9+.
    role_future_map: MutableMapping[Role, Future_R] = field(default_factory=dict)  # type: ignore[type-arg]
    role_response_map: MutableMapping[Role, R] = field(default_factory=dict)
    role_interrupted_map: MutableMapping[Role, bool] = field(default_factory=dict)
    role_exception_map: MutableMapping[Role, ActorError] = field(default_factory=dict)
    role_taskid_map: MutableMapping[Role, rich_progress.TaskID] = field(default_factory=dict)
    role_utility_map: MutableMapping[Role, Union[int, Disqualification, None]] = field(default_factory=dict)
    polling_interval: float = field(default=0.1)
    total_time: float = field(init=False, default=1.0)
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
            ", ".join(f"[yellow italic]{rich(role)}[/yellow italic]" for role in self.roles),
        )
        role_timeout_map = {}
        for role in self.roles:
            args = self._get_signal_args(role)
            log.debug("Sending [italic]%s[/italic] to [yellow italic]%s[/yellow italic]", self.signal_name, rich(role))
            future = self._signal(**args)
            self.role_future_map[role] = future
            role_timeout = self._get_timeout(role)
            role_timeout_map[role] = role_timeout
            log.debug(
                "Actor of [yellow italic]%s[/yellow italic] has [green]%s[/green] to respond",
                rich(role),
                format_timedelta(role_timeout),
                extra={"highlighter": None},
            )
            display_total = role_timeout if role_timeout != float("inf") else 60.0 * 60.0 * 24.0
            task_id = self.progress.add_task(f"{rich(role)} ({self.signal_name})", total=display_total)
            self.role_taskid_map[role] = task_id

        self.total_time = max(self.total_time, max(role_timeout_map.values(), default=0.0) + self.polling_interval)
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
    # Disables mypy. Because: Hack around Python 3.8's type system limitations. Future_R is a Future[R] in Python 3.9+.
    def _signal(self, *args: Any, **kwargs: Any) -> Future_R:  # type: ignore[type-arg]
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
                except (TimeoutError, concurrent_futures.TimeoutError):
                    pass
                except ActorError as inner_exception:
                    self.role_interrupted_map[role] = True
                    self.role_exception_map[role] = inner_exception

                if responded:
                    # Disable mypy. Because: Response may be None, but it is not Optional.
                    self.role_response_map[role] = response  # type: ignore[assignment]
                    task_id = self.role_taskid_map[role]
                    self.progress.stop_task(task_id)
                    log.debug(
                        "Received response ([italic]%s[/italic]) from [yellow italic]%s[/yellow italic]",
                        self.signal_name,
                        rich(role),
                    )
                else:
                    done = False

    @abc.abstractmethod
    def _get_exception(self, role: Role, inner_exception: ActorError) -> MatchError:
        raise NotImplementedError

    def collect(self) -> None:
        for role in self.roles:
            if role not in self.role_response_map:
                inner_exception: ActorError
                if not self.role_interrupted_map.get(role, False):
                    future = self.role_future_map[role]
                    future.cancel()
                    self.role_interrupted_map[role] = True
                    role_timeout = self._get_timeout(role)
                    inner_exception = TimeoutActorError(available_time=role_timeout, delta=self.total_time, role=role)
                else:
                    inner_exception = self.role_exception_map[role]

                exception = self._get_exception(role, inner_exception)
                self.exceptions.append(exception)
                self.role_utility_map[role] = self._get_disqualification_utility(role, exception)
            else:
                response = self.role_response_map[role]
                overwrite, utility = self._get_utility(role, response)
                if overwrite:
                    self.role_utility_map[role] = utility

    @abc.abstractmethod
    def _get_disqualification_utility(self, role: Role, exception: MatchError) -> Union[int, Disqualification, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_utility(self, role: Role, response: R) -> Tuple[bool, Union[int, Disqualification, None]]:
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
    ) -> Future_None:
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
    ) -> Tuple[bool, Union[int, Disqualification, None]]:
        return False, None

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

    def _signal(self, *, actor: Actor, ply: int, view: View) -> Future_Move:
        return self.executor.submit(actor.send_play, ply=ply, view=view)

    def _get_timeout(self, role: Role) -> float:
        actor = self.role_actor_map[role]
        assert actor.playclock is not None, "Assumption: playclock is not None (should have been set in send_start)"
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

    def _get_utility(self, role: Role, response: Move) -> Tuple[bool, Union[int, Disqualification, None]]:
        is_legal = self.interpreter.is_legal(current=self.state, role=role, move=response)
        if not is_legal:
            actor = self.role_actor_map[role]
            ply = self.ply
            view = self.interpreter.get_sees_by_role(current=self.state, role=role)
            legal_moves = self.interpreter.get_legal_moves_by_role(current=self.state, role=role)
            exception = IllegalMoveMatchError(
                actor=actor,
                move=response,
                legal_moves=legal_moves,
                view=view,
                ply=ply,
                role=role,
            )
            self.exceptions.append(exception)
            return True, _DNF_ILLEGAL_MOVE
        return False, None

    def _aggregate_responses(self) -> Turn:
        return Turn(self.role_response_map)


@dataclass
class _StopProcessor(_SignalProcessor[None, S, None], Generic[S], abc.ABC):
    # Disables ARG002 (Unused method argument). Because method overrides abstract method.
    def _get_timeout(self, role: Role) -> float:  # noqa: ARG002
        return float("inf")

    # Disables coverage. Because this method cannot be called.
    # Disables ARG002 (Unused method argument). Because method overrides abstract method.
    def _get_exception(self, role: Role, inner_exception: ActorError) -> MatchError:  # pragma: no cover # noqa: ARG002
        message = "Should not be called."
        raise AssertionError(message)

    # Disables coverage. Because this method cannot be called.
    def _get_disqualification_utility(
        self,
        # Disables ARG002 (Unused method argument). Because method overrides abstract method.
        role: Role,  # noqa: ARG002
        exception: MatchError,  # noqa: ARG002
    ) -> None:  # pragma: no cover
        message = "Should not be called."
        raise AssertionError(message)

    # Disables coverage. Because this method cannot be called.
    def _get_utility(
        self,
        # Disables ARG002 (Unused method argument). Because method overrides abstract method.
        role: Role,  # noqa: ARG002
        response: None,  # noqa: ARG002
    ) -> Tuple[bool, Union[int, Disqualification, None]]:  # pragma: no cover
        message = "Should not be called."
        raise AssertionError(message)

    def _aggregate_responses(self) -> None:  # pragma: no cover
        message = "Should not be called."
        raise AssertionError(message)


@dataclass
class _ConcludeProcessor(_StopProcessor["_ConcludeProcessor.ConcludeArgs"]):
    state: State = field(default_factory=lambda: State(frozenset()))
    interpreter: Interpreter = field(default_factory=ClingoInterpreter)

    signal_name: ClassVar[str] = "conclude"

    class ConcludeArgs(TypedDict):
        actor: Actor
        view: View

    def _get_signal_args(self, role: Role) -> ConcludeArgs:
        actor = self.role_actor_map[role]
        view = self.interpreter.get_sees_by_role(current=self.state, role=role)
        return _ConcludeProcessor.ConcludeArgs(actor=actor, view=view)

    def _signal(self, *, actor: Actor, view: View) -> Future_None:
        return self.executor.submit(actor.send_stop, view=view)

    def collect(self) -> None:
        self.role_utility_map.update(self.interpreter.get_goals(current=self.state))


@dataclass
class _AbortProcessor(_StopProcessor[Mapping[str, Actor]]):
    signal_name: ClassVar[str] = "abort"

    def _get_signal_args(self, role: Role) -> Mapping[str, Actor]:
        actor = self.role_actor_map[role]
        return {"actor": actor}

    def _signal(self, *, actor: Actor) -> Future_None:
        return self.executor.submit(actor.send_abort)


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
    role_to_actor: Mapping[Role, Actor]
    "Mapping of roles to actors."
    role_to_startclockconfiguration: Mapping[Role, GameClock.Configuration]
    "Mapping of roles to startclock configurations."
    role_to_playclockconfiguration: Mapping[Role, GameClock.Configuration]
    "Mapping of roles to playclock configurations."
    states: MutableSequence[State] = field(default_factory=list)
    "Sequence of states."
    utilities: MutableMapping[Role, Union[int, None, Disqualification]] = field(default_factory=dict)
    "Mapping of roles to utilities."

    @property
    def is_finished(self) -> bool:
        """Whether the match is finished."""
        return bool(self.utilities) or (bool(self.states) and self.interpreter.is_terminal(self.states[-1]))

    # endregion

    def __rich__(self) -> str:
        id_str = f"id={format_id(self)}"
        ruleset_str = f"ruleset={rich(self.ruleset)}"
        interpreter_str = f"interpreter={rich(self.interpreter)}"
        role_to_actor_str = f"role_to_actor={rich(self.role_to_actor)}"
        role_to_startclockconfiguration_str = (
            f"role_to_startclockconfiguration={rich(self.role_to_startclockconfiguration)}"
        )
        role_to_playclockconfiguration_str = (
            f"role_to_playclockconfiguration={rich(self.role_to_playclockconfiguration)}"
        )
        attributes_str = (
            f"{id_str}, "
            f"{ruleset_str}, "
            f"{interpreter_str}, "
            f"{role_to_actor_str}, "
            f"{role_to_startclockconfiguration_str}, "
            f"{role_to_playclockconfiguration_str}"
        )

        information_str = f"\\[#states={len(self.states)}{'' if not self.is_finished else ', is_finished'}]"
        return f"{self.__class__.__name__}{information_str}({attributes_str})"

    # region Methods

    def start(self, polling_interval: float = 0.1) -> None:
        """Start the match.

        Args:
            polling_interval: Interval to poll for updates in seconds

        """
        with contextlib.ExitStack() as exit_stack:
            executor = concurrent_futures.ThreadPoolExecutor()
            exit_stack.callback(executor.shutdown, wait=False)
            progress = exit_stack.enter_context(rich_progress.Progress(transient=True, auto_refresh=False))
            processor = _StartProcessor(
                executor=executor,
                progress=progress,
                role_actor_map=self.role_to_actor,
                roles=self.role_to_actor.keys(),
                ruleset=self.ruleset,
                role_startclock_configuration_map=self.role_to_startclockconfiguration,
                role_playclock_configuration_map=self.role_to_playclockconfiguration,
                polling_interval=polling_interval,
            )
            processor.init()
            processor.monitor()
            processor.collect()
            self.utilities = processor.role_utility_map
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
        log.info(
            "Executing ply ply=%s, playclocks=%s",
            ply,
            rich({role: actor.playclock for role, actor in self.role_to_actor.items()}),
        )
        roles_in_control = Interpreter.get_roles_in_control(current_state)
        humans_in_control = any(self.role_to_actor[role].is_human_actor for role in roles_in_control)
        with contextlib.ExitStack() as exit_stack:
            executor = concurrent_futures.ThreadPoolExecutor()
            exit_stack.callback(executor.shutdown, wait=False)
            progress = exit_stack.enter_context(
                rich_progress.Progress(
                    transient=True,
                    auto_refresh=False,
                    disable=humans_in_control,
                ),
            )
            processor = _PlayProcessor(
                executor=executor,
                progress=progress,
                role_actor_map=self.role_to_actor,
                roles=roles_in_control,
                state=current_state,
                ply=ply,
                interpreter=self.interpreter,
                polling_interval=polling_interval,
            )
            processor.init()
            processor.monitor()
            processor.collect()
            self.utilities = processor.role_utility_map
            turn = processor.process()
            executor.shutdown(wait=False)
        next_state = self.interpreter.get_next_state(current_state, turn)
        self.states.append(next_state)

    def conclude(self) -> None:
        """Conclude the match."""
        current_state = self.states[-1]
        with concurrent_futures.ThreadPoolExecutor() as executor, rich_progress.Progress(
            transient=True,
            auto_refresh=False,
            disable=True,
        ) as progress:
            processor = _ConcludeProcessor(
                executor=executor,
                progress=progress,
                role_actor_map=self.role_to_actor,
                roles=self.role_to_actor.keys(),
                state=current_state,
                interpreter=self.interpreter,
            )
            processor.init()
            processor.collect()
            self.utilities = processor.role_utility_map

    def abort(self) -> None:
        """Abort the match."""
        with concurrent_futures.ThreadPoolExecutor() as executor, rich_progress.Progress(
            transient=True,
            auto_refresh=False,
            disable=True,
        ) as progress:
            processor = _AbortProcessor(
                executor=executor,
                progress=progress,
                role_actor_map=self.role_to_actor,
                roles=self.role_to_actor.keys(),
            )
            processor.init()

    # endregion

    @staticmethod
    def get_rank(utilities: Mapping[Role, Union[int, None, Disqualification]]) -> Mapping[Role, int]:
        """Get the rank of the utilities.

        Args:
            utilities: Mapping of roles to goals (utility values)

        Returns:
            Mapping of roles to their ranks

        """
        min_value = min((utility for utility in utilities.values() if isinstance(utility, int)), default=0)
        none_value = min_value - 1
        disqualification_value = none_value - 1
        role_value_map = {role: utility for role, utility in utilities.items() if isinstance(utility, int)}
        for role, utility in utilities.items():
            if utility is None:
                role_value_map[role] = none_value
            elif not isinstance(utility, int):
                role_value_map[role] = disqualification_value
        value_sequence = sorted(role_value_map.values(), reverse=True)

        return {role: value_sequence.index(utility) for role, utility in role_value_map.items()}
