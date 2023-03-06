import logging

import pytest

from pyggp.app import determine_log_level


@pytest.mark.parametrize(
    "verbose,quiet,expected",
    [
        (0, 0, logging.INFO),
        (1, 0, logging.DEBUG),
        (2, 0, logging.DEBUG),
        (0, 1, logging.WARNING),
        (1, 1, logging.INFO),
        (0, 2, logging.ERROR),
        (0, 3, logging.CRITICAL),
        (0, 4, logging.CRITICAL),
    ],
)
def test_determine_log_level(verbose: int, quiet: int, expected: int):
    assert determine_log_level(verbose=verbose, quiet=quiet) == expected
