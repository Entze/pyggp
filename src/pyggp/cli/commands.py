"""Defines the CLI commands."""
import logging
from typing import List, Optional

import typer

from pyggp._logging import log
from pyggp.cli._common import (
    determine_log_level,
)
from pyggp.cli._main import version_callback
from pyggp.cli._match import (
    handle_match_args,
    run_local_match,
)

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
) -> None:
    """A GGP engine.

    Use pyggp COMMAND --help for more information.

    """


@app.command()
def match(
    ruleset: str = typer.Argument(..., show_default=False),
    registry: Optional[List[str]] = typer.Argument(None, metavar="[ROLE=AGENT]...", show_default=False),
    startclock: Optional[List[str]] = typer.Option(None, show_default=False),
    playclock: Optional[List[str]] = typer.Option(None, show_default=False),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, show_default=False),
    quiet: int = typer.Option(0, "--quiet", "-q", count=True, show_default=False),
) -> None:
    """Run a match between agents."""
    log_level = determine_log_level(verbose=verbose, quiet=quiet)

    log.setLevel(log_level)
    if __debug__:
        log.setLevel(logging.DEBUG)
    log.debug(
        "Arguments: log_level=%s, ruleset=%s, registry=%s, startclock=%s, playclock=%s",
        logging.getLevelName(log_level),
        ruleset,
        registry,
        startclock,
        playclock,
    )
    assert ruleset is not None, "Assumption: Type of ruleset_resource is str"
    assert registry is not None, "Assumption: Typer guarantees registry is at least the emtpy list"
    assert startclock is not None, "Assumption: Typer guarantees startclock is at least the emtpy list"
    assert playclock is not None, "Assumption: Typer guarantees playclock is at least the emtpy list"

    match_params = handle_match_args(
        ruleset_str=ruleset,
        role_agentname_registry=registry,
        role_startclockconfig_registry=startclock,
        role_playclockconfig_registry=playclock,
    )

    log.debug("Parameters: %s", match_params)

    run_local_match(
        **match_params,
    )
