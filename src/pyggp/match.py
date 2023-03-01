from concurrent.futures import ThreadPoolExecutor, Future
from typing import Mapping, Literal, NamedTuple, TypedDict, MutableMapping, TypeAlias, MutableSequence

from pyggp.actors import Actor
from pyggp.exceptions import MatchDNSError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Ruleset, Subrelation, Role, State
from pyggp.interpreters import Interpreter


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


class Match:
    def __init__(self, match_configuration: MatchConfiguration) -> None:
        self._ruleset: Ruleset = match_configuration["ruleset"]
        self._interpreter: Interpreter = match_configuration["interpreter"]
        self._role_actor_map: Mapping[Role, Actor] = match_configuration["role_actor_map"]
        self._startclock_configs: Mapping[Role, GameClockConfiguration] = match_configuration["startclock_configs"]
        self._playclock_configs: Mapping[Role, GameClockConfiguration] = match_configuration["playclock_configs"]
        self.utilities: MutableResultsMap = {role: None for role in self._role_actor_map.keys()}
        self.move_nr = 0
        self.states: MutableSequence[State] = []

    def initialize_agents(self) -> None:
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

    def initialize_state(self) -> None:
        self.states.append(self._interpreter.get_init_state())

    def execute_ply(self) -> bool:
        return False
