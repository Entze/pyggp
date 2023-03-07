import logging
from typing import List, Optional

import typer
from rich import print  # pylint: disable=redefined-builtin

import pyggp.agents
from pyggp._logging import log
from pyggp.commands import (
    parse_agent_registry,
    get_ruleset,
    orchestrate_match,
    get_clock_configs,
    get_name_agenttypes_map,
)
from pyggp.gameclocks import GameClockConfiguration
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
    startclock: Optional[List[str]] = typer.Option(None, "--startclock-config", show_default=False),
    playclock: Optional[List[str]] = typer.Option(None, "--playclock-config", show_default=False),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, show_default=False),
    quiet: int = typer.Option(0, "--quiet", "-q", count=True, show_default=False),
) -> None:
    log_level = determine_log_level(verbose=verbose, quiet=quiet)

    log.setLevel(log_level)
    if __debug__:
        log.setLevel(logging.DEBUG)
    log.debug(
        "Environment: console_width=%d, log_line_length=%d",
        pyggp._logging.console_width,
        pyggp._logging.log_line_length,
    )
    log.debug(
        "Command-line config: log_level=%s, ruleset=%s, registry=%s, startclock=%s, playclock=%s",
        logging.getLevelName(log_level),
        ruleset,
        registry,
        startclock,
        playclock,
    )

    ruleset = get_ruleset(ruleset)
    interpreter = ClingoInterpreter(ruleset)
    roles = interpreter.get_roles()
    role_agentname_map = parse_agent_registry(registry, roles=roles)
    name_agenttypes_map = get_name_agenttypes_map(role_agentname_map, default=pyggp.agents.ArbitraryAgent)
    startclock_configs = get_clock_configs(
        startclock, roles=roles, default=GameClockConfiguration.default_startclock_config()
    )
    playclock_configs = get_clock_configs(
        playclock, roles=roles, default=GameClockConfiguration.default_playclock_config()
    )
    visualizer = SimpleRichVisualizer()
    log.debug(
        "Parsed Input: "
        "ruleset=(\n\t%s\n), "
        "interpreter=%s, "
        "roles=%s, "
        "role_agentname_map=%s, "
        "name_agenttypes_map=%s, "
        "startclock_configs=%s, "
        "playclock_configs=%s, "
        "visualizer=%s",
        "\n\t".join(repr(rule) for rule in ruleset.rules),
        interpreter,
        roles,
        role_agentname_map,
        name_agenttypes_map,
        startclock_configs,
        playclock_configs,
        visualizer,
    )

    orchestrate_match(
        ruleset=ruleset,
        interpreter=interpreter,
        name_agenttypes_map=name_agenttypes_map,
        role_agentname_map=role_agentname_map,
        startclock_configs=startclock_configs,
        playclock_configs=playclock_configs,
        visualizer=visualizer,
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
