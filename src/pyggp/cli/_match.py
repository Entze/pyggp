import contextlib
import logging
import pathlib
from dataclasses import dataclass
from typing import (
    Callable,
    Mapping,
    MutableMapping,
    Sequence,
)

import exceptiongroup
import lark.exceptions as lark_exceptions
import typer
from exceptiongroup import ExceptionGroup

import pyggp.game_description_language as gdl
from pyggp._logging import log_time, rich
from pyggp.actors import LocalActor
from pyggp.agents import Agent, HumanAgent
from pyggp.cli._common import (
    check_roles,
    get_role_from_str,
    load_agentfactory_by_specification,
    load_ruleset,
    parse_registry,
)
from pyggp.cli.argument_specification import ArgumentSpecification
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
    role_to_agentspec: Mapping[Role, ArgumentSpecification]
    role_to_agentfactory: Mapping[Role, Callable[[], Agent]]
    role_to_startclockconfiguration: Mapping[Role, GameClock.Configuration]
    role_to_playclockconfiguration: Mapping[Role, GameClock.Configuration]
    visualizer: Visualizer

    def __rich__(self) -> str:
        ruleset_str = f"rules: {rich(self.ruleset.rules)}\n"
        interpreter_str = f"interpreter: {rich(self.interpreter)}\n"
        role_to_agentname_str = f"role_to_agentspec: {rich(self.role_to_agentspec)}\n"
        agentname_to_agenttype_str = f"agentname_to_agentfactory: {rich(self.role_to_agentfactory)}\n"
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


_RANDOMSPEC = ArgumentSpecification(name="Random")


def handle_match_command_args(
    *,
    files: Sequence[pathlib.Path],
    role_agentspec_registry: Sequence[str],
    role_startclockconfiguration_registry: Sequence[str],
    role_playclockconfiguration_registry: Sequence[str],
    visualizer_str: str,
    default_agent_str: str,
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

    try:
        default_agent_spec = ArgumentSpecification.from_str(default_agent_str)
    except lark_exceptions.UnexpectedInput:
        log.error(f'Could not parse default agent specification "{default_agent_str}"')
        raise typer.Exit(1) from None

    log.debug("Mapping roles to agent names")
    role_to_agentspec: MutableMapping[Role, ArgumentSpecification] = {role: default_agent_spec for role in roles}

    if RANDOM in roles:
        role_to_agentspec[RANDOM] = _RANDOMSPEC

    role_to_agentspec.update(
        parse_registry(
            registry=role_agentspec_registry,
            default_value=default_agent_spec,
            str_to_key=get_role_from_str,
            str_to_value=ArgumentSpecification.from_str,
        ),
    )
    try:
        check_roles(roles, role_to_agentspec)
    except RolesMismatchCLIError as roles_mismatch_error:
        log.exception(roles_mismatch_error, exc_info=False)
        raise typer.Exit(1) from None
    log.debug("Mapped roles to agent names")

    log.debug("Mapping agent specifications to agent factories")
    role_to_agentfactory: Mapping[Role, Callable[[], Agent]] = {
        role: load_agentfactory_by_specification(agentspec) for role, agentspec in role_to_agentspec.items()
    }
    log.debug("Mapped agent specifications to agent factories")

    log.debug("Mapping clock configurations to roles")
    role_to_startclockconfiguration = {role: DEFAULT_START_CLOCK_CONFIGURATION for role in roles}
    role_to_playclockconfiguration = {role: DEFAULT_PLAY_CLOCK_CONFIGURATION for role in roles}
    for role, agentname in role_to_agentspec.items():
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
        role_to_agentspec=role_to_agentspec,
        role_to_agentfactory=role_to_agentfactory,
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
    role_to_agentfactory: Mapping[Role, Callable[[], Agent]],
    role_to_startclockconfiguration: Mapping[Role, GameClock.Configuration],
    role_to_playclockconfiguration: Mapping[Role, GameClock.Configuration],
    visualizer: Visualizer,
) -> None:
    log.debug("Running match locally")
    with contextlib.ExitStack() as stack:
        stack.enter_context(visualizer)
        role_actor_map = {}
        for role, agent_factory in role_to_agentfactory.items():
            agent = agent_factory()
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
