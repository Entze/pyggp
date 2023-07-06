import pyggp.game_description_language as gdl
from pyggp._clingo_interpreter.temporal_rule_containers import (
    TemporalInformation,
    TemporalRuleContainer,
    base_dynamic_categorization,
    base_static_categorization,
)


def test_categorize_signatures_bottom_up_classifies_correctly() -> None:
    rules = """
    role(p1).

    lt(0, 1). lt(0, 2). lt(1, 2).

    next(A) :- non_static(A).

    non_static(0).
    non_static(1) :- non_static(0), dynamic(0).

    dynamic(A) :- true(A).

    """
    ruleset = gdl.parse(rules)
    actual_static, actual_dynamic = TemporalRuleContainer.categorize_signatures(ruleset.rules)

    expected_static = {
        gdl.Relation.Signature(name="lt", arity=2): TemporalInformation(name="lt_static", time=None, timeshift=None),
    }
    expected_static.update(base_static_categorization)
    expected_dynamic = {
        gdl.Relation.Signature(name="non_static", arity=1): TemporalInformation(
            name="non_static_at",
            time="__time",
            timeshift=None,
        ),
        gdl.Relation.Signature(name="dynamic", arity=1): TemporalInformation(
            name="dynamic_at",
            time="__time",
            timeshift=None,
        ),
    }
    expected_dynamic.update(base_dynamic_categorization)

    assert actual_static == expected_static
    assert actual_dynamic == expected_dynamic
