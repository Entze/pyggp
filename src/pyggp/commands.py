import contextlib
import importlib
from typing import Mapping, Type, NamedTuple, TypeVar, Generic, Self

from pyggp.actors import LocalActor
from pyggp.agents import Agent
from pyggp.exceptions.match_exceptions import MatchDNSError, MatchDNFError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Ruleset, Relation
from pyggp.interpreters import Interpreter
from pyggp.match import MatchConfiguration, Match
from pyggp.visualizers import Visualizer

T = TypeVar("T")


class DynamicLoader(NamedTuple, Generic[T]):
    module: str
    name: str

    @classmethod
    def from_absolute_module_name(cls, module_name: str) -> Self:
        module_name, name = module_name.rsplit(".", 1)
        return cls(module_name, name)

    def __call__(self, *args, **kwargs) -> Type[T]:
        return self.load()

    def load(self) -> Type[T]:
        module = importlib.import_module(self.module)
        cls: Type[T] = getattr(module, self.name)
        return cls


def orchestrate_match(
    ruleset: Ruleset,
    interpreter_type: Type[Interpreter],
    name_agenttypes_map: Mapping[str, Type[Agent]],
    role_agentname_map: Mapping[Relation | str | int, str],
    startclock_configs: Mapping[Relation | str | int, GameClockConfiguration],
    playclock_configs: Mapping[Relation | str | int, GameClockConfiguration],
    visualizer: Visualizer,
) -> None:
    agents = []
    agent_role_map = {}
    for role, agent_name in role_agentname_map.items():
        agent_type = name_agenttypes_map[agent_name]
        agent = agent_type()
        agent_role_map[agent] = role
        agents.append(agent)

    actors = []
    role_actor_map = {}
    with contextlib.ExitStack() as stack:
        for agent in agents:
            stack.enter_context(agent)
            role = agent_role_map[agent]
            actor = LocalActor(agent)
            actors.append(actor)
            role_actor_map[role] = actor

        interpreter = interpreter_type(ruleset)
        match_configuration = MatchConfiguration(
            ruleset=ruleset,
            interpreter=interpreter,
            role_actor_map=role_actor_map,
            startclock_configs=startclock_configs,
            playclock_configs=playclock_configs,
        )
        match = Match(match_configuration)
        aborted = False
        try:
            match.start_match()
            visualizer.update_state(match.states[0], 0)
        except MatchDNSError:
            aborted = True
            visualizer.update_abort()
            # TODO: logger

        while not match.is_finished and not aborted:
            visualizer.draw()
            try:
                match.execute_ply()
            except* MatchDNFError as eg:
                aborted = True
                visualizer.update_abort()
                # TODO: logger

            visualizer.update_state(match.states[-1])
            visualizer.draw()

        if not aborted:
            match.conclude_match()
        else:
            match.abort_match()

        for move_nr, state in enumerate(match.states):
            visualizer.update_state(state, move_nr)

        visualizer.update_result(match.get_result())
        visualizer.draw()
