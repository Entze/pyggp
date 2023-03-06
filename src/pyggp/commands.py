import contextlib
import importlib
import importlib.util
from dataclasses import dataclass
from functools import cached_property
from typing import Mapping, Type, TypeVar, Generic, Self, List, Optional, FrozenSet

import inflection

from pyggp.actors import LocalActor
from pyggp.agents import Agent
from pyggp.exceptions.match_exceptions import MatchDNSError, MatchDNFError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Ruleset, Relation
from pyggp.interpreters import Interpreter
from pyggp.logging import log
from pyggp.match import MatchConfiguration, Match
from pyggp.visualizers import Visualizer

T = TypeVar("T")


@dataclass
class DynamicLoader(Generic[T]):
    module: str | None
    name: str

    @classmethod
    def from_absolute_module_name(cls, module_name: str) -> Self:
        basename, *rest = module_name.rsplit(".", 1)
        if rest:
            _module = basename
            name = rest[0]
        else:
            _module = None
            name = basename

        return cls(_module, name)

    def __str__(self) -> str:
        if self.module is None:
            return self.name
        return f"{self.module}.{self.name}"

    def __call__(self, *args, **kwargs) -> T:
        return self.cls

    @property
    def exists(self) -> bool:
        if self.module is None:
            return False
        try:
            spec = importlib.util.find_spec(self.module)
        except ModuleNotFoundError:
            return False
        if spec is None:
            return False
        try:
            self.cls()
        except AttributeError:
            return False
        return True

    @cached_property
    def cls(self) -> T:
        module = importlib.import_module(self.module)
        cls: T = getattr(module, self.name)
        return cls


def load_by_name(name: str) -> Type[Agent] | Ruleset:
    loader = DynamicLoader.from_absolute_module_name(name)
    if loader.exists:
        return loader()
    if "." not in name:
        snake_case_name = inflection.underscore(name)
        loaders = (
            DynamicLoader(f"pyggp.games.{snake_case_name}", name),
            DynamicLoader("pyggp.games", name),
            DynamicLoader(f"pyggp.agents.{snake_case_name}", name),
            DynamicLoader("pyggp.agents", name),
            DynamicLoader(f"pyggp.{snake_case_name}", name),
            DynamicLoader("pyggp", name),
            DynamicLoader(snake_case_name, name),
        )
        valid_loaders = tuple(loader for loader in loaders if loader.exists)
        if len(valid_loaders) == 1:
            return valid_loaders[0]()
        if len(valid_loaders) > 1:
            raise ValueError(f"Multiple resources for {name}: {valid_loaders}")
    raise ValueError(f"No resources for {name}")


def load_ruleset_by_file(ruleset_file: str) -> Ruleset:
    # TODO: Implement real method
    if ruleset_file == "tic-tac-toe":
        from pyggp.games import tic_tac_toe_ruleset

        return tic_tac_toe_ruleset
    if ruleset_file == "rock-paper-scissors":
        from pyggp.games import rock_paper_scissors_ruleset

        return rock_paper_scissors_ruleset
    if ruleset_file == "minipoker":
        from pyggp.games import minipoker_ruleset

        return minipoker_ruleset
    raise FileNotFoundError(f"No rulesets for {ruleset_file}")


def parse_role_str(role_str: str) -> Relation | str | int:
    try:
        return int(role_str)
    except ValueError:
        pass
    if (role_str.startswith('"') and role_str.endswith('"')) or (role_str.startswith("'") and role_str.endswith("'")):
        return role_str[1:-1]
    return Relation(role_str)


def parse_agent_registry(
    registry: List[str], roles: FrozenSet[Relation | str | int]
) -> Mapping[Relation | str | int, str | None]:
    rolestr_agentstr_map = {role: None for role in roles}
    for rolestr_agentstr in registry:
        rolestr, *rest = rolestr_agentstr.split("=", maxsplit=1)
        agentstr: str | None = None
        if rest:
            agentstr = rest[0]
        role = parse_role_str(rolestr)
        rolestr_agentstr_map[role] = agentstr
    return rolestr_agentstr_map


def get_clock_configs(
    clock_config_strs: List[str] | None, roles: FrozenSet[Relation | str | int], default: GameClockConfiguration
) -> Mapping[Relation | str | int, GameClockConfiguration]:
    clock_configs = {role: default for role in roles}
    for clock_config_str in clock_config_strs:
        rolestr, *rest = clock_config_str.split("=", maxsplit=1)
        clock_config: GameClockConfiguration | None = None
        if rest:
            clock_config = GameClockConfiguration.from_str(rest[0])
        role = parse_role_str(rolestr)
        clock_configs[role] = clock_config or default
    return clock_configs


def get_ruleset(ruleset_str: str) -> Ruleset:
    try:
        return load_ruleset_by_file(ruleset_str)
    except FileNotFoundError:
        pass
    try:
        return load_by_name(ruleset_str)
    except ValueError:
        pass
    raise ValueError(f"No ruleset for {ruleset_str}")


def get_name_agenttypes_map(
    role_agentname_map: Mapping[Relation | str | int, str | None], default: Optional[Type[Agent]] = None
) -> Mapping[str, Type[Agent]]:
    if default is None:
        raise ValueError("Default agent type must be specified")  # TODO: Remove this requirement
    name_agenttypes_map = {}
    for agent_name in role_agentname_map.values():
        if agent_name is not None:
            agent_type = load_by_name(agent_name)
        else:
            agent_type = default
        name_agenttypes_map[agent_name] = agent_type
    return name_agenttypes_map


def orchestrate_match(
    ruleset: Ruleset,
    interpreter: Interpreter,
    name_agenttypes_map: Mapping[str, Type[Agent]],
    role_agentname_map: Mapping[Relation | str | int, str],
    startclock_configs: Mapping[Relation | str | int, GameClockConfiguration],
    playclock_configs: Mapping[Relation | str | int, GameClockConfiguration],
    visualizer: Visualizer,
) -> None:
    log.debug("Started orchestrating match")
    agents = []
    agent_role_map = {}
    for role, agent_name in role_agentname_map.items():
        log.debug(f"Instantiating agent {agent_name} for role {role}")
        agent_type = name_agenttypes_map[agent_name]
        agent = agent_type()
        agent_role_map[agent] = role
        agents.append(agent)

    actors = []
    role_actor_map = {}
    with contextlib.ExitStack() as stack:
        for agent in agents:
            role = agent_role_map[agent]
            log.debug(f"Setting up role {role}'s agent {agent}")
            stack.enter_context(agent)
            actor = LocalActor(agent)
            log.debug(f"Instantiating actor {actor} with agent {agent} for role {role}")
            actors.append(actor)
            role_actor_map[role] = actor

        match_configuration = MatchConfiguration(
            ruleset=ruleset,
            interpreter=interpreter,
            role_actor_map=role_actor_map,
            startclock_configs=startclock_configs,
            playclock_configs=playclock_configs,
        )
        match = Match(match_configuration)
        log.info(f"Starting {match}")
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
            log.debug(f"Concluded {match}")
            match.conclude_match()
        else:
            log.debug(f"Aborted {match}")
            match.abort_match()

        for move_nr, state in enumerate(match.states):
            visualizer.update_state(state, move_nr)

        visualizer.update_result(match.get_result())
        visualizer.draw()

    log.info(f"Finished orchestrating {match}.")
