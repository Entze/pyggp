from concurrent.futures import ThreadPoolExecutor, Future, ProcessPoolExecutor, Executor
from typing import (
    Mapping,
    Literal,
    NamedTuple,
    TypedDict,
    MutableMapping,
    TypeAlias,
    MutableSequence,
)

from pyggp.actors import Actor
from pyggp.exceptions.match_exceptions import (
    MatchDNSError,
    MatchTimeoutError,
    MatchIllegalMoveError,
    MatchNotStartedError,
)
from pyggp.gameclocks import GameClockConfiguration, GameClock
from pyggp.gdl import Ruleset, Subrelation, Role, State, Move, Relation
from pyggp.interpreters import Interpreter, get_roles_in_control


class MatchConfiguration(TypedDict):  # as in PEP 692
    ruleset: Ruleset
    interpreter: Interpreter
    role_actor_map: Mapping[Role, Actor]
    startclock_configs: Mapping[Role, GameClockConfiguration]
    playclock_configs: Mapping[Role, GameClockConfiguration]


Disqualifcation: TypeAlias = Literal["DNS", "DNF(Illegal Move)", "DNF(Timeout)"]
ResultsMap: TypeAlias = Mapping[Subrelation, int | None | Disqualifcation]
MutableResultsMap: TypeAlias = MutableMapping[Subrelation, int | None | Disqualifcation]


class MatchResult(NamedTuple):
    utilities: ResultsMap


def _get_executor(*actors: Actor) -> Executor:
    if len(actors) == 1:
        return ThreadPoolExecutor()
    else:
        return ProcessPoolExecutor()


class Match:
    def __init__(self, match_configuration: MatchConfiguration, slack: float = 2.5) -> None:
        self._ruleset: Ruleset = match_configuration["ruleset"]
        self._interpreter: Interpreter = match_configuration["interpreter"]
        self._role_actor_map: Mapping[Role, Actor] = match_configuration["role_actor_map"]
        self._startclock_configs: Mapping[Role, GameClockConfiguration] = match_configuration["startclock_configs"]
        self._playclock_configs: Mapping[Role, GameClockConfiguration] = match_configuration["playclock_configs"]
        self.utilities: MutableResultsMap = {role: None for role in self._role_actor_map.keys()}
        self.move_nr = 0
        self.states: MutableSequence[State] = []
        self._slack = slack

    @property
    def is_finished(self) -> bool:
        return self.states and self._interpreter.is_terminal(self.states[-1])

    def start_match(self) -> None:
        self._initialize_agents()
        self._initialize_state()

    def conclude_match(self) -> None:
        self.utilities |= self._interpreter.get_goals(self.states[-1])
        self._finalize_agents()

    def abort_match(self) -> None:
        self._abort_agents()

    def execute_ply(self) -> None:
        state = self.states[-1]
        roles_in_control = get_roles_in_control(state)
        views = self._interpreter.get_sees(state)
        actor_movefuture_map: MutableMapping[Actor, Future[Move | None]] = {}
        role_movemap = {role: None for role in roles_in_control}

        raises: MutableSequence[MatchTimeoutError | MatchIllegalMoveError] = []
        with _get_executor(*(self._role_actor_map[role] for role in roles_in_control)) as executor:
            for role in roles_in_control:
                actor = self._role_actor_map[role]
                actor_movefuture_map[actor] = executor.submit(actor.send_play, self.move_nr, views[role])

            wait_time = 0.0
            for actor in actor_movefuture_map:
                wait_time = max(wait_time, actor.playclock.get_timeout())
            wait_clock_config = GameClockConfiguration(wait_time, 0.0, self._slack)
            wait_clock = GameClock(wait_clock_config)

            for role in roles_in_control:
                actor = self._role_actor_map[role]
                move_future = actor_movefuture_map[actor]
                try:
                    with wait_clock:
                        move = move_future.result(wait_clock.get_timeout())
                    if not self._interpreter.is_legal(state, role, move):
                        raise ValueError
                    role_movemap[role] = move
                except TimeoutError:
                    if wait_clock.is_expired:
                        # Makes sure the next actor isn't immediately expired
                        wait_clock._total_time_ns = 0.0
                        assert not wait_clock.is_expired
                    self.utilities[role] = "DNF(Timeout)"
                    raises.append(MatchTimeoutError(self.move_nr, actor, role))
                except ValueError:
                    self.utilities[role] = "DNF(Illegal Move)"
                    raises.append(MatchIllegalMoveError(self.move_nr, actor, role))

        if raises:
            raise ExceptionGroup("Match aborted", raises)

        self.move_nr += 1
        plays = (Relation.does(role, move) for role, move in role_movemap.items())
        next_state = self._interpreter.get_next_state(state, *plays)
        self.states.append(next_state)

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
                    actor.send_start, role, self._ruleset, startclock_config, playclock_config
                )

            for role, actor in self._role_actor_map.items():
                try:
                    startclock_config = self._startclock_configs[role]
                    actor_startfuture_map[actor].result(startclock_config.total_time + startclock_config.delay + 2.5)
                except TimeoutError:
                    self.utilities[role] = "DNS"
                    dns.append((role, actor))

        if dns:
            raise MatchDNSError

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
