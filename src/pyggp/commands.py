import contextlib
import importlib
import importlib.util
from dataclasses import dataclass
from functools import cache, cached_property
from typing import FrozenSet, Generic, Iterator, List, Mapping, Optional, Type, TypeVar, Union

import exceptiongroup
import inflection
from typing_extensions import Self

from pyggp._logging import inflect, log
from pyggp.actors import LocalActor
from pyggp.agents import Agent, HumanAgent, RandomAgent
from pyggp.exceptions.match_exceptions import MatchDNFError, MatchDNSError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import ConcreteRole, Relation, Ruleset
from pyggp.interpreters import Interpreter
from pyggp.match import Match, MatchConfiguration
from pyggp.visualizers import Visualizer

T = TypeVar("T")


@dataclass(frozen=True, order=True)
class DynamicLoader(Generic[T]):
    module: Optional[str]
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
        return self.obj

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
            obj = self.obj
        except AttributeError:
            return False
        return True

    @cached_property
    def obj(self) -> T:
        module = importlib.import_module(self.module)
        obj: T = getattr(module, self.name)
        return obj


def get_loaders(name_str: str) -> Iterator[DynamicLoader]:
    snake_case_name = inflection.underscore(name_str)
    name_bases = (name_str, snake_case_name)
    if name_str == snake_case_name:
        name_bases = (name_str,)
    for top_level in ("pyggp", ""):
        for supmodule_base in ("agents", "games", ""):
            supmodule = f".{supmodule_base}" if supmodule_base != "" and top_level != "" else supmodule_base
            for submodule_base in (f"{snake_case_name}", f"{snake_case_name}_agent", f"{snake_case_name}_ruleset", ""):
                submodule = (
                    f".{submodule_base}"
                    if submodule_base != "" and (supmodule != "" or top_level != "")
                    else submodule_base
                )
                module = f"{top_level}{supmodule}{submodule}"
                assert ".." not in module
                assert not module.startswith(".")
                assert not module.endswith(".")
                if module == "":
                    continue
                for name_suffix in ("Agent", "_agent", "Ruleset", "_ruleset", ""):
                    for name_base in name_bases:
                        name = f"{name_base}{name_suffix}"
                        yield DynamicLoader(
                            module,
                            name,
                        )


@cache
def load_by_name(name: str) -> Union[Type[Agent], Ruleset]:
    loader = DynamicLoader.from_absolute_module_name(name)
    if loader.exists:
        return loader()

    loaders = ()
    if "." not in name:
        loaders = set(get_loaders(name))
        valid_loaders = tuple(loader for loader in loaders if loader.exists)
        log.debug("Found %s for [italic]%s[/italic]: %s", inflect("loader", len(valid_loaders)), name, valid_loaders)
        if len(valid_loaders) == 1:
            return valid_loaders[0]()
        if len(valid_loaders) > 1:
            raise ValueError(f"Multiple resources for {name}: {valid_loaders}")
    log.error("No loaders for [italic]%s[/italic], tried: \n%s", name, "\n".join(str(loader) for loader in loaders))
    raise ValueError(f"No resources for {name}")


def load_ruleset_by_file(ruleset_file: str) -> Ruleset:
    # TODO: Implement real method
    raise FileNotFoundError(f"No rulesets for {ruleset_file}")


def get_ruleset(ruleset_str: str) -> Ruleset:
    try:
        return load_ruleset_by_file(ruleset_str)
    except FileNotFoundError:
        pass
    try:
        return load_by_name(ruleset_str)
    except ValueError:
        pass
    raise ValueError(f"No (unique) ruleset for {ruleset_str}")


def parse_role_str(role_str: str) -> ConcreteRole:
    try:
        return int(role_str)
    except ValueError:
        pass
    if (role_str.startswith('"') and role_str.endswith('"')) or (role_str.startswith("'") and role_str.endswith("'")):
        return role_str[1:-1]
    return Relation(role_str)


def parse_agent_registry(registry: List[str], roles: FrozenSet[ConcreteRole]) -> Mapping[ConcreteRole, Optional[str]]:
    rolestr_agentstr_map = {role: None for role in roles}
    if Relation.random() in roles:
        rolestr_agentstr_map[Relation.random()] = "__random__"
    for rolestr_agentstr in registry:
        rolestr, *rest = rolestr_agentstr.split("=", maxsplit=1)
        role = parse_role_str(rolestr)
        if role not in roles:
            raise ValueError(f"Unknown role {role} in registry")
        agentstr: Optional[str] = None
        if rest:
            agentstr = rest[0]
        rolestr_agentstr_map[role] = agentstr
    if roles != set(rolestr_agentstr_map.keys()):
        superfluous = set(rolestr_agentstr_map.keys()) - roles
        raise ValueError(f"Superfluous roles in registry: {superfluous}")

    return rolestr_agentstr_map


def get_clock_configs(
    clock_config_strs: Optional[List[str]],
    roles: FrozenSet[ConcreteRole],
    default_clock_config: GameClockConfiguration,
    default_config: Optional[Mapping[ConcreteRole, GameClockConfiguration]] = None,
    **default_config_kwargs: GameClockConfiguration,
) -> Mapping[ConcreteRole, GameClockConfiguration]:
    if default_config is None:
        default_config = default_config_kwargs
    else:
        default_config = {
            **default_config,
            **{parse_role_str(role_str): config for role_str, config in default_config_kwargs.items()},
        }
    clock_configs = {role: default_clock_config for role in roles} | default_config
    for clock_config_str in clock_config_strs:
        rolestr, *rest = clock_config_str.split("=", maxsplit=1)
        clock_config: Optional[GameClockConfiguration] = None
        if rest:
            clock_config = GameClockConfiguration.from_str(rest[0])
        role = parse_role_str(rolestr)
        clock_configs[role] = clock_config or default_clock_config
    return clock_configs


def get_name_agenttypes_map(
    role_agentname_map: Mapping[ConcreteRole, Optional[str]], default: Optional[Type[Agent]] = None
) -> Mapping[str, Type[Agent]]:
    if default is None:
        raise ValueError("Default agent type must be specified")  # TODO: Remove this requirement
    name_agenttypes_map = {}
    for role, agent_name in role_agentname_map.items():
        agent_name_ = agent_name
        if agent_name is not None and agent_name != "__random__":
            agent_type = load_by_name(agent_name)
        elif role == Relation.random():
            agent_type = RandomAgent
            agent_name_ = "__random__"
        else:
            agent_type = default
        name_agenttypes_map[agent_name_] = agent_type
    return name_agenttypes_map


def _match_error_handler(excgroup: exceptiongroup.ExceptionGroup) -> None:
    for exc in excgroup.exceptions:
        log.exception(exc)


def orchestrate_match(
    ruleset: Ruleset,
    interpreter: Interpreter,
    name_agenttypes_map: Mapping[str, Type[Agent]],
    role_agentname_map: Mapping[ConcreteRole, str],
    startclock_configs: Mapping[ConcreteRole, GameClockConfiguration],
    playclock_configs: Mapping[ConcreteRole, GameClockConfiguration],
    visualizer: Visualizer,
) -> None:
    log.debug("Started orchestrating match")
    agents = []
    agent_role_map = {}
    for role, agent_name in role_agentname_map.items():
        log.debug(
            "Instantiating agent [italic]%s[/italic] for role [italic yellow]%s[/italic yellow]", agent_name, role
        )
        agent_type = name_agenttypes_map[agent_name]
        agent = agent_type()
        agent_role_map[agent] = role
        agents.append(agent)

    actors = []
    role_actor_map = {}
    with contextlib.ExitStack() as stack:
        for agent in agents:
            role = agent_role_map[agent]
            log.debug("Beginning setup for %s with role [italic yellow]%s[/italic yellow]", agent, role)
            stack.enter_context(agent)
            is_human_actor = isinstance(agent, HumanAgent)
            actor = LocalActor(agent=agent, is_human_actor=is_human_actor)
            log.debug("Instantiating %s for %s with role [italic yellow]%s[/italic yellow]", actor, agent, role)
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
        log.info("Starting %s", match)
        aborted = True
        with exceptiongroup.catch(
            {
                MatchDNSError: _match_error_handler,
            }
        ):
            match.start_match()
            visualizer.update_state(match.states[0], 0)
            aborted = False

        if aborted:
            visualizer.update_abort()

        while not match.is_finished and not aborted:
            visualizer.draw()
            aborted = True
            with exceptiongroup.catch(
                {
                    MatchDNFError: _match_error_handler,
                }
            ):
                match.execute_ply()
                aborted = False

            if not aborted:
                visualizer.update_state(match.states[-1])
                visualizer.draw()
            else:
                visualizer.update_abort()

        if not aborted:
            log.debug("Concluded %s", match)
            match.conclude_match()
        else:
            log.debug("Aborted %s", match)
            match.abort_match()

        for move_nr, state in enumerate(match.states):
            visualizer.update_state(state, move_nr)

        visualizer.update_result(match.get_result())
        visualizer.draw()

    log.info("Finished orchestrating %s", match)
