from typing import Mapping, Sequence

import pytest
from pyggp.cli._common import get_agentname_from_str, parse_registry


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


@pytest.mark.parametrize(
    ("string", "expected"),
    [
        ("a", "a"),
        ("A", "A"),
        ("a.b", "a.b"),
        ("a.b.c", "a.b.c"),
        ("randomhumanagent", "randomhumanagent"),
        ("Human1Agent", "Human1Agent"),
        ("RandomAgent", "Random"),
        ("randomagent", "Random"),
        ("Human", "Human"),
        ("hUmAnAgEnT", "Human"),
    ],
)
def test_get_agentname_by_str(string: str, expected: str) -> None:
    actual = get_agentname_from_str(string)
    assert actual == expected
