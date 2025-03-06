from typing import Mapping, Sequence

import pytest

from pyggp.cli._common import parse_registry


@pytest.mark.parametrize(
    ("registry", "expected"),
    [
        ([], {}),
        (["a"], {"a": ""}),
        (["a=b"], {"a": "b"}),
        (["a=b", "c=d"], {"a": "b", "c": "d"}),
    ],
)
def test_parse_registry(registry: Sequence[str], expected: Mapping[str, str]) -> None:
    actual_iterator = parse_registry(registry, default_value="")
    actual = dict(actual_iterator)
    assert actual == expected
