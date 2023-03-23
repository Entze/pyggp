"""TODO: Add a description."""

import sys

import pyggp.app as cli

from ._logging import log

_major, _minor = sys.version_info[:2]

_SUPPORTED_VERSIONS = ((3, 8), (3, 9), (3, 10), (3, 11))

if (_major, _minor) not in _SUPPORTED_VERSIONS:
    log.error(
        "Unsupported Python version: %s.%s. Supported versions: %s",
        _major,
        _minor,
        ", ".join(f"{_ma}.{_mo}" for (_ma, _mo) in _SUPPORTED_VERSIONS),
    )
    sys.exit(1)


if __name__ == "__main__":
    cli.app(prog_name="pyggp")
