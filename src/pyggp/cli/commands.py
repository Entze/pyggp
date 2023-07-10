"""Defines the CLI commands."""
import logging
import pathlib
from typing import List

import typer

from pyggp._logging import rich
from pyggp.cli._common import (
    determine_log_level,
)
from pyggp.cli._main import sys_info_callback, version_callback
from pyggp.cli._match import (
    handle_match_command_args,
    run_local_match,
)

log: logging.Logger = logging.getLogger("pyggp")

app = typer.Typer()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version number and exit",
        is_eager=True,
        callback=version_callback,
    ),
    sys_info: bool = typer.Option(
        False,
        "--sys-info",
        "-S",
        help="Show system information and exit",
        is_eager=True,
        callback=sys_info_callback,
    ),
) -> None:
    """A GGP engine.

    Use pyggp COMMAND --help for more information.

    """


@app.command()
def match(
    registry: List[str] = typer.Argument(None, metavar="[ROLE=AGENT]...", show_default=False),
    files: List[pathlib.Path] = typer.Option(..., "--ruleset", "--file", "-f", show_default=False),
    startclock: List[str] = typer.Option(None, "--startclock", "-s", show_default=False),
    playclock: List[str] = typer.Option(None, "--playclock", "-p", show_default=False),
    clairvoyant: List[str] = typer.Option(None, "--clairvoyant", "-c", show_default=False),
    visualizer: str = typer.Option(None, "--visualizer", show_default=False),
    default_agent: str = typer.Option("Human", "-d", "--default-agent", show_default=True),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, show_default=False),
    quiet: int = typer.Option(0, "--quiet", "-q", count=True, show_default=False),
) -> None:
    """Run a match between agents."""
    log_level = determine_log_level(verbose=verbose, quiet=quiet)

    log.setLevel(log_level)
    log.debug(
        "Received [bold]match[/bold] command "
        "registry=%s, "
        "files=%s, "
        "startclock=%s, "
        "playclock=%s, "
        "clairvoyant=%s, "
        "visualizer=%s, "
        "default_agent=%s, "
        "log_level=%s",
        registry,
        files,
        startclock,
        playclock,
        clairvoyant,
        visualizer,
        default_agent,
        logging.getLevelName(log_level),
    )

    match_params = handle_match_command_args(
        files=files,
        role_agentspec_registry=registry,
        role_startclockconfiguration_registry=startclock,
        role_playclockconfiguration_registry=playclock,
        clairvoyant_roles=clairvoyant,
        visualizer_str=visualizer,
        default_agent_str=default_agent,
    )

    log.debug("Starting match with the following parameters: %s", rich(match_params))

    run_local_match(
        ruleset=match_params.ruleset,
        interpreter=match_params.interpreter,
        role_to_agentfactory=match_params.role_to_agentfactory,
        role_to_startclockconfiguration=match_params.role_to_startclockconfiguration,
        role_to_playclockconfiguration=match_params.role_to_playclockconfiguration,
        clairvoyant_roles=match_params.clairvoyant_roles,
        visualizer=match_params.visualizer,
    )
