"""Entrypoint for the pyggp package."""

import logging
import sys

import rich.logging
import typer

import pyggp.cli._common
import pyggp.cli.commands

if __name__ == "__main__":
    _major, _minor = sys.version_info[:2]

    _SUPPORTED_VERSIONS = ((3, 9), (3, 10), (3, 11), (3, 12))

    log: logging.Logger = logging.getLogger("pyggp")

    if (_major, _minor) not in _SUPPORTED_VERSIONS:
        log.error(
            "Unsupported Python version: %s.%s. Supported versions: %s",
            _major,
            _minor,
            ", ".join(f"{_ma}.{_mo}" for (_ma, _mo) in _SUPPORTED_VERSIONS),
        )
        raise typer.Exit(1)

    handler: rich.logging.RichHandler = rich.logging.RichHandler(
        rich_tracebacks=True,
        markup=True,
    )

    if not __debug__:
        handler.tracebacks_suppress = [
            typer,
            rich,
        ]

    FORMAT: str = "%(message)s"
    logging.basicConfig(
        level=logging.NOTSET,
        format=FORMAT,
        datefmt="[%X]",
        handlers=[handler],
    )

    pyggp.cli.commands.app(prog_name="pyggp")
