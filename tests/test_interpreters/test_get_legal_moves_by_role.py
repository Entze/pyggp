import pytest

from pyggp.gdl import Relation, Role, Ruleset, Sentence
from pyggp.interpreters import ClingoInterpreter


@pytest.mark.parametrize("role,expected_state", [(Relation("p1"), frozenset({1, 2})), (Relation("p2"), frozenset())])
def test_as_expected(role: Role, expected_state) -> None:
    mock_ruleset = Ruleset(
        (
            Sentence.fact(Relation.role(Relation("p1"))),
            Sentence.fact(Relation.role(Relation("p2"))),
            Sentence.fact(Relation.legal(Relation("p1"), 1)),
            Sentence.fact(Relation.legal(Relation("p1"), 2)),
        )
    )

    interpreter = ClingoInterpreter(mock_ruleset)
    assert interpreter.get_legal_moves_by_role(frozenset(), role) == expected_state
