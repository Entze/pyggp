import contextlib
import logging
import pathlib
from dataclasses import dataclass
from typing import (
    Mapping,
    Sequence,
    Type,
)

import exceptiongroup
import typer
from exceptiongroup import ExceptionGroup

import pyggp.game_description_language as gdl
from pyggp.actors import LocalActor
from pyggp.agents import Agent, HumanAgent
from pyggp.cli._common import (
    check_roles,
    get_agentname_from_str,
    get_role_from_str,
    load_agent_by_name,
    load_ruleset,
    parse_registry,
)
from pyggp.exceptions.cli_exceptions import RulesetNotFoundCLIError
from pyggp.exceptions.match_exceptions import DidNotFinishMatchError, DidNotStartMatchError
from pyggp.gameclocks import (
    DEFAULT_NO_TIMEOUT_CONFIGURATION,
    DEFAULT_PLAY_CLOCK_CONFIGURATION,
    DEFAULT_START_CLOCK_CONFIGURATION,
    GameClock,
)
from pyggp.interpreters import RANDOM, ClingoInterpreter, Interpreter, Role
from pyggp.match import Match
from pyggp.visualizers import SimpleVisualizer, Visualizer

log: logging.Logger = logging.getLogger("pyggp")


@dataclass(frozen=True)
class MatchCommandParams:
    ruleset: gdl.Ruleset
    interpreter: Interpreter
    role_agentname_map: Mapping[Role, str]
    agentname_agenttype_map: Mapping[str, Type[Agent]]
    role_startclockconfig_map: Mapping[Role, GameClock.Configuration]
    role_playclockconfig_map: Mapping[Role, GameClock.Configuration]
    visualizer: Visualizer


def handle_match_command_args(
    *,
    files: Sequence[pathlib.Path],
    role_agentname_registry: Sequence[str],
    role_startclockconfig_registry: Sequence[str],
    role_playclockconfig_registry: Sequence[str],
) -> MatchCommandParams:
    log.debug("Fetching ruleset")
    try:
        ruleset = load_ruleset(files)
    except RulesetNotFoundCLIError as ruleset_not_found_error:
        message = ruleset_not_found_error.args[0]
        # Disables TRY400 (Use `logging.exception` instead of `logging.error`). Because: The whole stacktrace is not
        # needed here.
        log.error(message)  # noqa: TRY400
        raise typer.Exit(1) from None

    log.debug("Instantiating interpreter")
    interpreter = ClingoInterpreter.from_ruleset(ruleset=ruleset)
    roles = interpreter.get_roles()

    log.debug("Mapping roles to agent names")
    role_agentname_map = {role: "Human" for role in roles}

    if RANDOM in roles:
        role_agentname_map[RANDOM] = "Random"

    role_agentname_map.update(
        parse_registry(
            registry=role_agentname_registry,
            default_value="Human",
            str_to_key=get_role_from_str,
            str_to_value=get_agentname_from_str,
        ),
    )
    check_roles(roles, role_agentname_map)

    log.debug("Mapping agent names to agent types")
    agentname_agenttype_map = {agentname: load_agent_by_name(agentname) for agentname in role_agentname_map.values()}

    log.debug("Mapping clock configs to roles")
    role_startclockconfig_map = {role: DEFAULT_START_CLOCK_CONFIGURATION for role in roles}
    role_playclockconfig_map = {role: DEFAULT_PLAY_CLOCK_CONFIGURATION for role in roles}
    for role, agentname in role_agentname_map.items():
        if agentname == "Human" or role == RANDOM:
            role_startclockconfig_map[role] = DEFAULT_NO_TIMEOUT_CONFIGURATION
            role_playclockconfig_map[role] = DEFAULT_NO_TIMEOUT_CONFIGURATION

    role_playclockconfig_map.update(
        parse_registry(
            role_startclockconfig_registry,
            default_value=DEFAULT_PLAY_CLOCK_CONFIGURATION,
            str_to_key=get_role_from_str,
            str_to_value=GameClock.Configuration.from_str,
        ),
    )
    role_startclockconfig_map.update(
        parse_registry(
            role_playclockconfig_registry,
            default_value=DEFAULT_START_CLOCK_CONFIGURATION,
            str_to_key=get_role_from_str,
            str_to_value=GameClock.Configuration.from_str,
        ),
    )

    log.debug("Instantiating visualizer")
    visualizer = SimpleVisualizer()

    return MatchCommandParams(
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
    log.debug("Starting %s", match)
    aborted = True
    # Disables PyCharms PyTypeChecker. Because exceptiongroup seems not to be typed correctly.
    # noinspection PyTypeChecker
    with exceptiongroup.catch(
        {
            # Disables mypy dict-item. Because exceptiongroup seems not to be typed correctly.
            DidNotStartMatchError: _match_error_handler,  # type: ignore[dict-item]
        },
    ):
        match.start()
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
        match.conclude()
    else:
        log.debug("Aborted %s", match)
        match.abort()

    for move_nr, state in enumerate(match.states):
        visualizer.update_state(state, move_nr)

    visualizer.update_result(match.utilities)
    visualizer.draw()


def run_local_match(
    ruleset: gdl.Ruleset,
    interpreter: Interpreter,
    agentname_agenttype_map: Mapping[str, Type[Agent]],
    role_agentname_map: Mapping[Role, str],
    role_startclockconfig_map: Mapping[Role, GameClock.Configuration],
    role_playclockconfig_map: Mapping[Role, GameClock.Configuration],
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

        match = Match(
            ruleset=ruleset,
            interpreter=interpreter,
            role_actor_map=role_actor_map,
            role_startclock_configuration_map=role_startclockconfig_map,
            role_playclock_configuration_map=role_playclockconfig_map,
        )
        run_match(match, visualizer)

    log.debug("Finished orchestrating %s", match)
