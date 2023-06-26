"""Defines the CLI commands."""
import logging
import pathlib
from typing import List

import typer

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
    visualizer: str = typer.Option(None, "--visualizer", show_default=False),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, show_default=False),
    quiet: int = typer.Option(0, "--quiet", "-q", count=True, show_default=False),
) -> None:
    """Run a match between agents."""
    log_level = determine_log_level(verbose=verbose, quiet=quiet)

    log.setLevel(log_level)
    log.debug(
        "Arguments: log_level=%s, files=%s, registry=%s, startclock=%s, playclock=%s, visualizer=%s",
        logging.getLevelName(log_level),
        files,
        registry,
        startclock,
        playclock,
        visualizer,
    )

    match_params = handle_match_command_args(
        files=files,
        role_agentname_registry=registry,
        role_startclockconfig_registry=startclock,
        role_playclockconfig_registry=playclock,
        visualizer_str=visualizer,
    )

    log.debug("Parameters: %s", match_params)

    run_local_match(
        ruleset=match_params.ruleset,
        interpreter=match_params.interpreter,
        agentname_agenttype_map=match_params.agentname_agenttype_map,
        role_agentname_map=match_params.role_agentname_map,
        role_startclockconfig_map=match_params.role_startclockconfig_map,
        role_playclockconfig_map=match_params.role_playclockconfig_map,
        visualizer=match_params.visualizer,
    )
