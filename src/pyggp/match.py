from concurrent.futures import Executor, Future, ThreadPoolExecutor
from typing import (
    Literal,
    Mapping,
    MutableMapping,
    MutableSequence,
    NamedTuple,
    Optional,
    TypedDict,
    Union,
)

import exceptiongroup
import rich.progress as rich_progress
from typing_extensions import TypeAlias

from pyggp._logging import inflect, log
from pyggp.actors import Actor
from pyggp.exceptions.actor_exceptions import ActorIllegalMoveError, ActorTimeoutError
from pyggp.exceptions.match_exceptions import (
    DidNotStartMatchError,
    IllegalMoveMatchError,
    TimeoutMatchError,
)
from pyggp.gameclocks import GameClock, GameClockConfiguration
from pyggp.gdl import ConcreteRole, Move, Relation, Ruleset, State, Subrelation
from pyggp.interpreters import Interpreter, get_roles_in_control


class MatchConfiguration(TypedDict):  # as in PEP 692
    ruleset: Ruleset
    interpreter: Interpreter
    role_actor_map: Mapping[ConcreteRole, Actor]
    role_startclockconfig_map: Mapping[ConcreteRole, GameClockConfiguration]
    role_playclockconfig_map: Mapping[ConcreteRole, GameClockConfiguration]


_DNS: Literal["DNS"] = "DNS"
_DNF_ILLEGAL_MOVE: Literal["DNF(Illegal Move)"] = "DNF(Illegal Move)"
_DNF_TIMEOUT: Literal["DNF(Timeout)"] = "DNF(Timeout)"
Disqualification: TypeAlias = Literal["DNS", "DNF(Illegal Move)", "DNF(Timeout)"]
ResultsMap: TypeAlias = Mapping[Subrelation, Union[int, None, Disqualification]]
MutableResultsMap: TypeAlias = MutableMapping[Subrelation, Union[int, None, Disqualification]]


class MatchResult(NamedTuple):
    utilities: ResultsMap


def _get_executor(*actors: Actor) -> Executor:
    return ThreadPoolExecutor()


class Match:
    def __init__(self, match_configuration: MatchConfiguration, max_wait: float = 60 * 60, slack: float = 2.5) -> None:
        self._ruleset: Ruleset = match_configuration["ruleset"]
        self._interpreter: Interpreter = match_configuration["interpreter"]
        self._role_actor_map: Mapping[ConcreteRole, Actor] = match_configuration["role_actor_map"]
        self._startclock_configs: Mapping[ConcreteRole, GameClockConfiguration] = match_configuration[
            "role_startclockconfig_map"
        ]
        self._playclock_configs: Mapping[ConcreteRole, GameClockConfiguration] = match_configuration[
            "role_playclockconfig_map"
        ]
        self.utilities: MutableResultsMap = {role: None for role in self._role_actor_map}
        self.ply = 0
        self.states: MutableSequence[State] = []
        self._max_wait = max_wait
        self._slack = slack
        self._polling_rate = 0.1

    def __repr__(self) -> str:
        ply = self.ply
        roles = set(self._role_actor_map.keys())
        return f"Match(id={hex(id(self))}, {ply=}, {roles=})"

    @property
    def is_finished(self) -> bool:
        return bool(self.states) and self._interpreter.is_terminal(self.states[-1])

    def start_match(self) -> None:
        self._initialize_agents()
        self._initialize_state()

    def conclude_match(self) -> None:
        self.utilities |= self._interpreter.get_goals(self.states[-1])
        self._finalize_agents()

    def abort_match(self) -> None:
        self._abort_agents()

    def execute_ply(self) -> None:
        log.debug("Starting to execute ply %d", self.ply)
        state = self.states[-1]
        roles_in_control = get_roles_in_control(state)
        views = self._interpreter.get_sees(state)
        actor_movefuture_map: MutableMapping[Actor, Future[Optional[Move]]] = {}
        role_movemap = {role: None for role in roles_in_control}

        raises: MutableSequence[Union[TimeoutMatchError, IllegalMoveMatchError]] = []
        with _get_executor(*(self._role_actor_map[role] for role in roles_in_control)) as executor:
            for role in roles_in_control:
                actor = self._role_actor_map[role]
                log.debug("Submitting send_play to %s", actor)
                actor_movefuture_map[actor] = executor.submit(actor.send_play, self.ply, views[role])

            wait_time = 0.0
            for actor in actor_movefuture_map:
                wait_time = min(self._max_wait, max(wait_time, actor.playclock.get_timeout()))
            log.debug(
                "Waiting at most [bold cyan]%.2fs[/bold cyan] for %s to send a play",
                wait_time,
                inflect("actor", len(actor_movefuture_map)),
            )
            wait_clock_config = GameClockConfiguration(wait_time + self._slack, 0.0, 0.0)
            wait_clock = GameClock(wait_clock_config)

            role_padding = max(len(str(role)) for role in roles_in_control) + 2
            display = not any(actor.is_human_actor for actor in self._role_actor_map.values())

            with rich_progress.Progress(
                rich_progress.TextColumn("[progress.description]{task.description}"),
                rich_progress.BarColumn(),
                rich_progress.TimeElapsedColumn(),
                rich_progress.TextColumn("/"),
                rich_progress.TimeRemainingColumn(),
                disable=not display,
                transient=True,
            ) as progress:
                role_task_map = {}
                for role in roles_in_control:
                    actor = self._role_actor_map[role]
                    task = progress.add_task(
                        str(role).rjust(role_padding) + f"{'(calculating)': >14}",
                        total=actor.playclock.get_timeout(),
                    )
                    role_task_map[role] = task

                while (
                    not wait_clock.is_expired
                    and not raises
                    and not all(move is not None for move in role_movemap.values())
                ):
                    for role in roles_in_control:
                        if role_movemap[role] is not None:
                            continue
                        actor = self._role_actor_map[role]
                        if actor.playclock.is_expired:
                            continue

                        timeout = min(self._polling_rate, wait_clock.get_timeout())
                        if actor.is_human_actor:
                            timeout = actor.playclock.get_timeout()
                            if timeout == float("inf"):
                                timeout = None
                        try:
                            with wait_clock:
                                move = actor_movefuture_map[actor].result(timeout=timeout)
                            if not self._interpreter.is_legal(state, role, move):
                                raise ActorIllegalMoveError
                            role_movemap[role] = move
                            progress.update(
                                role_task_map[role],
                                description=str(role).rjust(role_padding) + f"{'(done)': >14}",
                            )
                            progress.stop_task(role_task_map[role])
                        except TimeoutError:
                            pass
                        except ActorTimeoutError:
                            log.warning("%s timed out", actor)
                            self.utilities[role] = _DNF_TIMEOUT
                            raises.append(TimeoutMatchError(self.ply, actor, role))
                        except ActorIllegalMoveError:
                            log.warning("%s sent an illegal move", actor)
                            self.utilities[role] = _DNF_ILLEGAL_MOVE
                            raises.append(IllegalMoveMatchError(self.ply, actor, role, move))
                        disable = False
                        for role_ in roles_in_control:
                            if role_movemap[role_] is None:
                                progress.advance(role_task_map[role_], advance=wait_clock.last_delta)
                                actor = self._role_actor_map[role_]
                                disable = disable or actor.is_human_actor

                        progress.disable = disable
                        if not display and not disable:
                            progress.live.start(refresh=True)

        for role in roles_in_control:
            if role_movemap[role] is None and self.utilities[role] not in ("DNF(Timeout)", "DNF(Illegal Move)"):
                actor = self._role_actor_map[role]
                log.warning("%s timed out", actor)
                self.utilities[role] = "DNF(Timeout)"
                raises.append(TimeoutMatchError(self.ply, actor, role))

        if raises:
            raise exceptiongroup.ExceptionGroup("Match aborted", raises)

        self.ply += 1
        plays = (Relation.does(role, move) for role, move in role_movemap.items())
        next_state = self._interpreter.get_next_state(state, *plays)
        self.states.append(next_state)
        log.debug("Finished executing ply %d", self.ply - 1)

    def get_result(self) -> MatchResult:
        return MatchResult(self.utilities)

    def _initialize_agents(self) -> None:
        actor_startfuture_map: MutableMapping[Actor, Future[None]] = {}

        dns = []
        with ThreadPoolExecutor() as executor:
            for role, actor in self._role_actor_map.items():
                startclock_config = self._startclock_configs[role]
                playclock_config = self._playclock_configs[role]

                actor_startfuture_map[actor] = executor.submit(
                    actor.send_start,
                    role,
                    self._ruleset,
                    startclock_config,
                    playclock_config,
                )

            for role, actor in self._role_actor_map.items():
                try:
                    startclock_config = self._startclock_configs[role]
                    actor_startfuture_map[actor].result(
                        min(self._max_wait, startclock_config.total_time + startclock_config.delay + self._slack),
                    )
                except TimeoutError:
                    self.utilities[role] = "DNS"
                    dns.append(DidNotStartMatchError(role, actor))

        if dns:
            raise exceptiongroup.ExceptionGroup("Timeout while initializing agents", dns)

    def _finalize_agents(self) -> None:
        views = self._interpreter.get_sees(self.states[-1])
        for role, actor in self._role_actor_map.items():
            view = views[role]
            actor.send_stop(view)

    def _abort_agents(self) -> None:
        for actor in self._role_actor_map.values():
            actor.send_abort()

    def _initialize_state(self) -> None:
        self.states = [self._interpreter.get_init_state()]
