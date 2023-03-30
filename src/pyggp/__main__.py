"""Entrypoint for the pyggp package."""

import sys

import typer

import pyggp.cli._common
import pyggp.cli.commands
from pyggp._logging import log

if __name__ == "__main__":
    _major, _minor = sys.version_info[:2]

    _SUPPORTED_VERSIONS = ((3, 8), (3, 9), (3, 10), (3, 11))

    if (_major, _minor) not in _SUPPORTED_VERSIONS:
        log.error(
            "Unsupported Python version: %s.%s. Supported versions: %s",
            _major,
            _minor,
            ", ".join(f"{_ma}.{_mo}" for (_ma, _mo) in _SUPPORTED_VERSIONS),
        )
        raise typer.Exit(1)
    pyggp.cli.commands.app(prog_name="pyggp")
