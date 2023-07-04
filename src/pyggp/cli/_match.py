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
from pyggp._logging import log_time, rich
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
from pyggp.engine_primitives import RANDOM, Role
from pyggp.exceptions.cli_exceptions import RolesMismatchCLIError, RulesetNotFoundCLIError, VisualizerNotFoundCLIError
from pyggp.exceptions.match_exceptions import DidNotFinishMatchError, DidNotStartMatchError
from pyggp.gameclocks import (
    DEFAULT_NO_TIMEOUT_CONFIGURATION,
    DEFAULT_PLAY_CLOCK_CONFIGURATION,
    DEFAULT_START_CLOCK_CONFIGURATION,
    GameClock,
)
from pyggp.interpreters import ClingoInterpreter, Interpreter
from pyggp.match import Match
from pyggp.visualizers import SimpleVisualizer, Visualizer

log: logging.Logger = logging.getLogger("pyggp")


@dataclass(frozen=True)
class MatchCommandParams:
    ruleset: gdl.Ruleset
    interpreter: Interpreter
    role_to_agentname: Mapping[Role, str]
    agentname_to_agenttype: Mapping[str, Type[Agent]]
    role_to_startclockconfiguration: Mapping[Role, GameClock.Configuration]
    role_to_playclockconfiguration: Mapping[Role, GameClock.Configuration]
    visualizer: Visualizer

    def __rich__(self) -> str:
        ruleset_str = f"rules: {rich(self.ruleset.rules)}\n"
        interpreter_str = f"interpreter: {rich(self.interpreter)}\n"
        role_to_agentname_str = f"role_to_agentname: {rich(self.role_to_agentname)}\n"
        agentname_to_agenttype_str = f"agentname_to_agenttype: {rich(self.agentname_to_agenttype)}\n"
        role_to_startclockconfiguration_str = (
            f"role_to_startclockconfiguration: {rich(self.role_to_startclockconfiguration)}\n"
        )
        role_to_playclockconfiguration_str = (
            f"role_to_playclockconfiguration: {rich(self.role_to_playclockconfiguration)}\n"
        )
        visualizer_str = f"visualizer: {rich(self.visualizer)}"
        return (
            f"{ruleset_str}"
            f"{interpreter_str}"
            f"{role_to_agentname_str}"
            f"{agentname_to_agenttype_str}"
            f"{role_to_startclockconfiguration_str}"
            f"{role_to_playclockconfiguration_str}"
            f"{visualizer_str}"
        )


def handle_match_command_args(
    *,
    files: Sequence[pathlib.Path],
    role_agentname_registry: Sequence[str],
    role_startclockconfiguration_registry: Sequence[str],
    role_playclockconfiguration_registry: Sequence[str],
    visualizer_str: str,
) -> MatchCommandParams:
    log.debug("Handling [bold]match[/bold] command arguments")
    log.debug("Loading ruleset")
    try:
        ruleset = load_ruleset(files)
    except RulesetNotFoundCLIError as ruleset_not_found_error:
        log.exception(ruleset_not_found_error, exc_info=False)
        raise typer.Exit(1) from None
    log.debug("Loaded ruleset")

    with log_time(
        level=logging.DEBUG,
        log=log,
        begin_msg="Instantiating interpreter",
        end_msg="Instantiated interpreter",
        abort_msg="Aborted instantiation of interpreter",
    ):
        interpreter = ClingoInterpreter.from_ruleset(ruleset=ruleset)
    roles = interpreter.get_roles()

    log.debug("Mapping roles to agent names")
    role_to_agentname = {role: "Human" for role in roles}

    if RANDOM in roles:
        role_to_agentname[RANDOM] = "Random"

    role_to_agentname.update(
        parse_registry(
            registry=role_agentname_registry,
            default_value="Human",
            str_to_key=get_role_from_str,
            str_to_value=get_agentname_from_str,
        ),
    )
    try:
        check_roles(roles, role_to_agentname)
    except RolesMismatchCLIError as roles_mismatch_error:
        log.exception(roles_mismatch_error, exc_info=False)
        raise typer.Exit(1) from None
    log.debug("Mapped roles to agent names")

    log.debug("Mapping agent names to agent types")
    agentname_to_agenttype = {agentname: load_agent_by_name(agentname) for agentname in role_to_agentname.values()}
    log.debug("Mapped agent names to agent types")

    log.debug("Mapping clock configurations to roles")
    role_to_startclockconfiguration = {role: DEFAULT_START_CLOCK_CONFIGURATION for role in roles}
    role_to_playclockconfiguration = {role: DEFAULT_PLAY_CLOCK_CONFIGURATION for role in roles}
    for role, agentname in role_to_agentname.items():
        if agentname == "Human" or role == RANDOM:
            role_to_startclockconfiguration[role] = DEFAULT_NO_TIMEOUT_CONFIGURATION
            role_to_playclockconfiguration[role] = DEFAULT_NO_TIMEOUT_CONFIGURATION

    role_to_startclockconfiguration.update(
        parse_registry(
            role_startclockconfiguration_registry,
            default_value=DEFAULT_START_CLOCK_CONFIGURATION,
            str_to_key=get_role_from_str,
            str_to_value=GameClock.Configuration.from_str,
        ),
    )

    role_to_playclockconfiguration.update(
        parse_registry(
            role_playclockconfiguration_registry,
            default_value=DEFAULT_PLAY_CLOCK_CONFIGURATION,
            str_to_key=get_role_from_str,
            str_to_value=GameClock.Configuration.from_str,
        ),
    )
    log.debug("Mapped clock configurations to roles")

    with log_time(
        log=log,
        level=logging.DEBUG,
        begin_msg="Instantiating visualizer",
        end_msg="Instantiated visualizer",
        abort_msg="Aborted instantiation of visualizer",
    ):
        if visualizer_str is not None:
            try:
                visualizer = Visualizer.from_argument_specification_str(
                    argument_specification_str=visualizer_str,
                    ruleset=ruleset,
                )
            except VisualizerNotFoundCLIError as visualizer_not_found_error:
                log.exception(visualizer_not_found_error, exc_info=False)
                raise typer.Exit(1) from None
        else:
            visualizer = SimpleVisualizer()

    log.debug("Handled [bold]match[/bold] command arguments")
    return MatchCommandParams(
        ruleset=ruleset,
        interpreter=interpreter,
        role_to_agentname=role_to_agentname,
        agentname_to_agenttype=agentname_to_agenttype,
        role_to_startclockconfiguration=role_to_startclockconfiguration,
        role_to_playclockconfiguration=role_to_playclockconfiguration,
        visualizer=visualizer,
    )


# Disables mypy type-arg. Because exceptiongroup seems not to be typed correctly.
def _match_error_handler(excgroup: ExceptionGroup) -> None:  # type: ignore[type-arg]
    for exc in excgroup.exceptions:
        log.exception(exc, exc_info=False)


def run_match(
    match: Match,
    visualizer: Visualizer,
) -> None:
    log.info("Starting %s", rich(match))
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
        log.info("Concluded %s", rich(match))
        match.conclude()
    else:
        log.info("Aborted %s", rich(match))
        match.abort()

    for move_nr, state in enumerate(match.states):
        visualizer.update_state(state, move_nr)

    visualizer.update_result(match.utilities)
    visualizer.draw()


def run_local_match(
    ruleset: gdl.Ruleset,
    interpreter: Interpreter,
    agentname_to_agenttype: Mapping[str, Type[Agent]],
    role_to_agentname: Mapping[Role, str],
    role_to_startclockconfiguration: Mapping[Role, GameClock.Configuration],
    role_to_playclockconfiguration: Mapping[Role, GameClock.Configuration],
    visualizer: Visualizer,
) -> None:
    log.debug("Running match locally")
    with contextlib.ExitStack() as stack:
        role_actor_map = {}
        for role, agent_name in role_to_agentname.items():
            agent_type = agentname_to_agenttype[agent_name]
            agent = agent_type()
            stack.enter_context(agent)
            is_human_actor = isinstance(agent, HumanAgent)
            actor = LocalActor(agent=agent, is_human_actor=is_human_actor)
            log.debug("Associating role %s with %s and with %s", rich(role), rich(agent), rich(actor))
            role_actor_map[role] = actor

        match = Match(
            ruleset=ruleset,
            interpreter=interpreter,
            role_to_actor=role_actor_map,
            role_to_startclockconfiguration=role_to_startclockconfiguration,
            role_to_playclockconfiguration=role_to_playclockconfiguration,
        )
        run_match(match, visualizer)

    log.debug("Ran %s locally", rich(match))
