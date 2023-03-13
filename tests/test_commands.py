from typing import List, Mapping

import pytest

from pyggp.commands import parse_agent_registry
from pyggp.gdl import Relation


@pytest.mark.skip
@pytest.mark.parametrize(
    "input,expected",
    [
        ([], {}),
        (["a=b"], {Relation("a"): "b"}),
        (["a=b", "c=d"], {Relation("a"): "b", Relation("c"): "d"}),
        (["r1"], {Relation("r1"): None}),
        (["r1="], {Relation("r1"): ""}),
        (["'r1'="], {"r1": ""}),
        (['"r1"='], {"r1": ""}),
        (["1=b", "2=d"], {1: "b", 2: "d"}),
    ],
)
def test_parse_agent_registry(input: List[str], expected: Mapping[str, str]):
    assert parse_agent_registry(input, frozenset()) == expected
