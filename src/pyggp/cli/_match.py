import contextlib
from typing import (
    Mapping,
    Sequence,
    Type,
)

import exceptiongroup
from exceptiongroup import ExceptionGroup
from typing_extensions import TypedDict

from pyggp._logging import log
from pyggp.actors import LocalActor
from pyggp.agents import Agent, HumanAgent
from pyggp.cli._common import check_roles, get_agentname_from_str, load_agent_by_name, load_ruleset, parse_registry
from pyggp.exceptions.match_exceptions import DidNotFinishMatchError, DidNotStartMatchError
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import ConcreteRole, Relation, Ruleset, get_concrete_role_from_str
from pyggp.interpreters import ClingoInterpreter, Interpreter
from pyggp.match import Match, MatchConfiguration
from pyggp.visualizers import SimpleRichVisualizer, Visualizer


class MatchParams(TypedDict):
    ruleset: Ruleset
    interpreter: Interpreter
    role_agentname_map: Mapping[ConcreteRole, str]
    agentname_agenttype_map: Mapping[str, Type[Agent]]
    role_startclockconfig_map: Mapping[ConcreteRole, GameClockConfiguration]
    role_playclockconfig_map: Mapping[ConcreteRole, GameClockConfiguration]
    visualizer: Visualizer


def handle_match_args(
    *,
    ruleset_str: str,
    role_agentname_registry: Sequence[str],
    role_startclockconfig_registry: Sequence[str],
    role_playclockconfig_registry: Sequence[str],
) -> MatchParams:
    log.debug("Fetching ruleset")
    ruleset = load_ruleset(ruleset_str)

    log.debug("Instantiating interpreter")
    interpreter = ClingoInterpreter(ruleset=ruleset)
    roles = interpreter.get_roles()

    log.debug("Mapping roles to agent names")
    role_agentname_map = {role: "Human" for role in roles}

    if Relation.random() in roles:
        role_agentname_map[Relation.random()] = "Random"

    role_agentname_map.update(
        parse_registry(
            registry=role_agentname_registry,
            default_value="Human",
            str_to_key=get_concrete_role_from_str,
            str_to_value=get_agentname_from_str,
        ),
    )
    check_roles(roles, role_agentname_map)

    log.debug("Mapping agent names to agent types")
    agentname_agenttype_map = {agentname: load_agent_by_name(agentname) for agentname in role_agentname_map.values()}

    log.debug("Mapping clock configs to roles")
    role_startclockconfig_map = {role: GameClockConfiguration.default_startclock_config() for role in roles}
    role_playclockconfig_map = {role: GameClockConfiguration.default_playclock_config() for role in roles}
    for role, agentname in role_agentname_map.items():
        if agentname == "Human" or role == Relation.random():
            role_startclockconfig_map[role] = GameClockConfiguration.default_no_timeout_config()
            role_playclockconfig_map[role] = GameClockConfiguration.default_no_timeout_config()

    role_playclockconfig_map.update(
        parse_registry(
            role_startclockconfig_registry,
            default_value=GameClockConfiguration.default_playclock_config(),
            str_to_key=get_concrete_role_from_str,
            str_to_value=GameClockConfiguration.from_str,
        ),
    )
    role_startclockconfig_map.update(
        parse_registry(
            role_playclockconfig_registry,
            default_value=GameClockConfiguration.default_startclock_config(),
            str_to_key=get_concrete_role_from_str,
            str_to_value=GameClockConfiguration.from_str,
        ),
    )

    log.debug("Instantiating visualizer")
    visualizer = SimpleRichVisualizer()

    return MatchParams(
        ruleset=ruleset,
        interpreter=interpreter,
        role_agentname_map=role_agentname_map,
        agentname_agenttype_map=agentname_agenttype_map,
        role_startclockconfig_map=role_startclockconfig_map,
        role_playclockconfig_map=role_playclockconfig_map,
        visualizer=visualizer,
    )


# Disables mypy type-arg. Because exceptiongroup seems not to be typed correctly.
def _match_error_handler(excgroup: ExceptionGroup) -> None:  # type: ignore[type-arg]
    for exc in excgroup.exceptions:
        log.exception(exc)


def run_match(
    match: Match,
    visualizer: Visualizer,
) -> None:
    log.info("Starting %s", match)
    aborted = True
    # Disables PyCharms PyTypeChecker. Because exceptiongroup seems not to be typed correctly.
    # noinspection PyTypeChecker
    with exceptiongroup.catch(
        {
            # Disables mypy dict-item. Because exceptiongroup seems not to be typed correctly.
            DidNotStartMatchError: _match_error_handler,  # type: ignore[dict-item]
        },
    ):
        match.start_match()
        visualizer.update_state(match.states[0], 0)
        aborted = False

    if aborted:
        visualizer.update_abort()

    while not match.is_finished and not aborted:
        visualizer.draw()
        aborted = True
        # Disables PyCharms PyTypeChecker. Because exceptiongroup seems not to be typed correctly.
        # noinspection PyTypeChecker
        with exceptiongroup.catch(
            {
                # Disables mypy dict-item. Because exceptiongroup seems not to be typed correctly.
                DidNotFinishMatchError: _match_error_handler,  # type: ignore[dict-item]
            },
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


def run_local_match(
    ruleset: Ruleset,
    interpreter: Interpreter,
    agentname_agenttype_map: Mapping[str, Type[Agent]],
    role_agentname_map: Mapping[ConcreteRole, str],
    role_startclockconfig_map: Mapping[ConcreteRole, GameClockConfiguration],
    role_playclockconfig_map: Mapping[ConcreteRole, GameClockConfiguration],
    visualizer: Visualizer,
) -> None:
    log.debug("Started orchestrating match")
    agents = []
    agent_role_map = {}
    for role, agent_name in role_agentname_map.items():
        log.debug(
            "Instantiating agent [italic]%s[/italic] for role [italic yellow]%s[/italic yellow]",
            agent_name,
            role,
        )
        agent_type = agentname_agenttype_map[agent_name]
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
            role_startclockconfig_map=role_startclockconfig_map,
            role_playclockconfig_map=role_playclockconfig_map,
        )
        match = Match(match_configuration)
        run_match(match, visualizer)

    log.info("Finished orchestrating %s", match)
