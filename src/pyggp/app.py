import logging
from typing import List, Optional

import typer
from rich import print  # pylint: disable=redefined-builtin

import pyggp.agents
from pyggp._logging import log
from pyggp.commands import (
    get_clock_configs,
    get_name_agenttypes_map,
    get_ruleset,
    orchestrate_match,
    parse_agent_registry,
)
from pyggp.gameclocks import GameClockConfiguration
from pyggp.gdl import Relation
from pyggp.interpreters import ClingoInterpreter
from pyggp.visualizers import SimpleRichVisualizer

app = typer.Typer()


def version_callback(value: bool) -> None:
    if value:
        print("[bold]pyggp[/bold] (version %s)" % pyggp.__version__)
        raise typer.Exit()


def determine_log_level(verbose: int = 0, quiet: int = 0) -> int:
    verbosity = verbose - quiet
    if verbosity > 0:
        log_level = logging.DEBUG
    elif verbosity == 0:
        log_level = logging.INFO
    elif verbosity == -1:
        log_level = logging.WARNING
    elif verbosity == -2:
        log_level = logging.ERROR
    else:
        log_level = logging.CRITICAL

    return log_level


# Disables too-many-arguments, because typer builds the CLI from the function signature.
# pylint: disable=too-many-arguments
@app.command()
def match(
    ruleset: str = typer.Argument(..., show_default=False),
    registry: Optional[List[str]] = typer.Argument(None, metavar="[ROLE=AGENT]...", show_default=False),
    startclock: Optional[List[str]] = typer.Option(None, show_default=False),
    playclock: Optional[List[str]] = typer.Option(None, show_default=False),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, show_default=False),
    quiet: int = typer.Option(0, "--quiet", "-q", count=True, show_default=False),
) -> None:
    log_level = determine_log_level(verbose=verbose, quiet=quiet)

    log.setLevel(log_level)
    if __debug__:
        log.setLevel(logging.DEBUG)
    log.debug(
        "Command-line config: log_level=%s, ruleset=%s, registry=%s, startclock=%s, playclock=%s",
        logging.getLevelName(log_level),
        ruleset,
        registry,
        startclock,
        playclock,
    )

    log.debug("Fetching ruleset")
    ruleset_ = get_ruleset(ruleset)
    log.debug("Instantiating interpreter")
    interpreter_ = ClingoInterpreter(ruleset_)
    roles_ = interpreter_.get_roles()
    log.debug("Mapping roles to agent names")
    role_agentname_map_ = parse_agent_registry(registry, roles=roles_)
    log.debug("Mapping agent names to agent types")
    name_agenttypes_map_ = get_name_agenttypes_map(role_agentname_map_, default=pyggp.agents.HumanAgent)
    log.debug("Mapping clock configs to roles")
    default_config = {
        role: GameClockConfiguration.default_no_timeout_config()
        for role in roles_
        if role == Relation.random() or name_agenttypes_map_[role_agentname_map_[role]] == pyggp.agents.HumanAgent
    }
    startclock_configs_ = get_clock_configs(
        startclock,
        roles=roles_,
        default_config=default_config,
        default_clock_config=GameClockConfiguration.default_startclock_config(),
    )
    playclock_configs_ = get_clock_configs(
        playclock,
        roles=roles_,
        default_config=default_config,
        default_clock_config=GameClockConfiguration.default_playclock_config(),
    )
    log.debug("Initializing visualizer")
    visualizer_ = SimpleRichVisualizer()
    log.debug(
        "Finalized Config: "
        "ruleset=\n%s\n, "
        "interpreter=%s, "
        "roles=%s, "
        "role_agentname_map=%s, "
        "name_agenttypes_map=%s, "
        "startclock_configs=%s, "
        "playclock_configs=%s, "
        "visualizer=%s",
        ruleset_,
        interpreter_,
        roles_,
        role_agentname_map_,
        name_agenttypes_map_,
        startclock_configs_,
        playclock_configs_,
        visualizer_,
    )

    orchestrate_match(
        ruleset=ruleset_,
        interpreter=interpreter_,
        name_agenttypes_map=name_agenttypes_map_,
        role_agentname_map=role_agentname_map_,
        startclock_configs=startclock_configs_,
        playclock_configs=playclock_configs_,
        visualizer=visualizer_,
    )


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version number and exit", is_eager=True, callback=version_callback
    )
) -> None:
    """A GGP engine.

    Use pyggp COMMAND --help for more information.

    """


if __name__ == "__main__":
    app(prog_name="pyggp")
