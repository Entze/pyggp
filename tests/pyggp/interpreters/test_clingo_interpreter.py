from unittest import mock

import clingo
import clingo.ast as clingo_ast
import pyggp._clingo as clingo_helper
import pyggp.game_description_language as gdl
import pytest
from pyggp.exceptions.interpreter_exceptions import (
    ModelTimeoutInterpreterError,
    MoreThanOneModelInterpreterError,
    SolveTimeoutInterpreterError,
)
from pyggp.interpreters import ClingoInterpreter


def test_protected_get_model() -> None:
    interpreter = ClingoInterpreter()

    ctl = clingo.Control()
    ctl.configuration.solve.models = 2
    ctl.add("base", [], "a.")

    model = interpreter._get_model(ctl)
    actual = tuple(model)
    expected = (clingo.Function("a"),)
    assert actual == expected


def test_protected_get_model_empty() -> None:
    interpreter = ClingoInterpreter()

    ctl = clingo.Control()
    ctl.configuration.solve.models = 2
    ctl.add("base", [], "a :- b.")

    model = interpreter._get_model(ctl)
    actual = tuple(model)
    expected = ()
    assert actual == expected


def test_protected_get_model_timeout() -> None:
    interpreter = ClingoInterpreter(model_timeout=0.1, solve_timeout=0.1)

    ctl = clingo.Control()
    ctl.configuration.solve.models = 2

    model = interpreter._get_model(ctl)
    with mock.patch("clingo.solving.SolveHandle.wait", return_value=False), pytest.raises(ModelTimeoutInterpreterError):
        tuple(model)


def test_protected_get_model_unsat() -> None:
    interpreter = ClingoInterpreter()

    ctl = clingo.Control()
    ctl.configuration.solve.models = 2
    ctl.add("base", [], "a :- not a.")

    model = interpreter._get_model(ctl)
    with pytest.raises(ClingoInterpreter.Unsat):
        tuple(model)


def test_protected_get_model_multiple() -> None:
    interpreter = ClingoInterpreter()

    ctl = clingo.Control()
    ctl.configuration.solve.models = 2
    ctl.add("base", [], "a :- not b. b :- not a.")

    model = interpreter._get_model(ctl)
    with pytest.raises(MoreThanOneModelInterpreterError):
        tuple(model)


def test_protected_get_model_multiple_timeout() -> None:
    interpreter = ClingoInterpreter(model_timeout=0.1, solve_timeout=0.1)

    ctl = clingo.Control()
    ctl.configuration.solve.models = 2
    ctl.add("base", [], "a :- not b. b :- not a.")

    with mock.patch("clingo.solving.SolveHandle.wait", side_effect=(True, False)):
        model = interpreter._get_model(ctl)
        with pytest.raises(SolveTimeoutInterpreterError):
            tuple(model)


def test_from_ruleset_static_only() -> None:
    rules = (
        gdl.Sentence(gdl.Relation("fact")),
        gdl.Sentence(gdl.Relation("rule"), body=(gdl.Literal(gdl.Relation("fact")),)),
    )

    ruleset = gdl.Ruleset.from_rules(rules)

    actual = ClingoInterpreter.from_ruleset(ruleset)
    expected = ClingoInterpreter(
        ruleset=ruleset,
        _rules=ClingoInterpreter.ClingoASTRules(
            dynamic_rules=(
                (clingo_helper.PROGRAM_STATEMACHINE, ()),
                (
                    clingo_helper.PROGRAM_STATIC,
                    (
                        clingo_helper.create_rule(
                            clingo_helper.create_literal(
                                atom=clingo_helper.create_atom(clingo_helper.create_function("fact_static")),
                            ),
                        ),
                        clingo_helper.create_rule(
                            clingo_helper.create_literal(
                                atom=clingo_helper.create_atom(clingo_helper.create_function("rule_static")),
                            ),
                            (
                                clingo_helper.create_literal(
                                    atom=clingo_helper.create_atom(clingo_helper.create_function("fact_static")),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    assert actual._rules.dynamic_rules == expected._rules.dynamic_rules
    assert actual == expected


def test_ruleset_with_dynamic_rules() -> None:
    rules = (
        gdl.Sentence(gdl.Relation("irrelevant")),
        gdl.Sentence(gdl.Relation("relevant")),
        gdl.Sentence(gdl.Relation("init", (gdl.Subrelation(gdl.Relation("state")),))),
        gdl.Sentence(
            gdl.Relation("rule"),
            body=(
                gdl.Literal(gdl.Relation("true", (gdl.Subrelation(gdl.Relation("state")),))),
                gdl.Literal(gdl.Relation("relevant")),
                gdl.Literal(gdl.Relation("unrelated"), sign=gdl.Literal.Sign.NEGATIVE),
            ),
        ),
        gdl.Sentence(
            gdl.Relation("next", (gdl.Subrelation(gdl.Relation("state")),)),
            body=(gdl.Literal(gdl.Relation("true", (gdl.Subrelation(gdl.Relation("state")),))),),
        ),
    )
    ruleset = gdl.Ruleset.from_rules(rules)

    actual = ClingoInterpreter.from_ruleset(ruleset)

    expected_static_rules = (
        clingo_helper.PROGRAM_STATIC,
        (
            clingo_helper.create_rule(
                clingo_helper.create_literal(
                    atom=clingo_helper.create_atom(clingo_helper.create_function("irrelevant_static")),
                ),
            ),
            clingo_helper.create_rule(
                clingo_helper.create_literal(
                    atom=clingo_helper.create_atom(clingo_helper.create_function("relevant_static")),
                ),
            ),
            clingo_helper.create_rule(
                clingo_helper.create_literal(
                    atom=clingo_helper.create_atom(
                        clingo_helper.create_function(
                            "holds_at",
                            arguments=(
                                clingo_helper.create_function("state"),
                                clingo_helper.create_symbolic_term(clingo.Number(0)),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    expected_dynamic_rules = (
        clingo_helper.PROGRAM_DYNAMIC,
        (
            clingo_helper.create_rule(
                clingo_helper.create_literal(
                    atom=clingo_helper.create_atom(
                        clingo_helper.create_function("rule_at", arguments=(clingo_helper.create_function("__time"),)),
                    ),
                ),
                (
                    clingo_helper.create_literal(
                        atom=clingo_helper.create_atom(
                            clingo_helper.create_function(
                                "holds_at",
                                arguments=(
                                    clingo_helper.create_function("state"),
                                    clingo_helper.create_function("__time"),
                                ),
                            ),
                        ),
                    ),
                    clingo_helper.create_literal(
                        atom=clingo_helper.create_atom(clingo_helper.create_function("relevant_static")),
                    ),
                    clingo_helper.create_literal(
                        sign=clingo_ast.Sign.Negation,
                        atom=clingo_helper.create_atom(clingo_helper.create_function("unrelated")),
                    ),
                ),
            ),
        ),
    )
    expected_statemachine_rules = (
        clingo_helper.PROGRAM_STATEMACHINE,
        (
            clingo_helper.create_rule(
                clingo_helper.create_literal(
                    atom=clingo_helper.create_atom(
                        clingo_helper.create_function(
                            "holds_at",
                            arguments=(
                                clingo_helper.create_function("state"),
                                clingo_helper.create_binary_operation(
                                    left=clingo_helper.create_function("__time"),
                                    right=clingo_helper.create_symbolic_term(clingo.Number(1)),
                                ),
                            ),
                        ),
                    ),
                ),
                (
                    clingo_helper.create_literal(
                        atom=clingo_helper.create_atom(
                            clingo_helper.create_function(
                                "holds_at",
                                arguments=(
                                    clingo_helper.create_function("state"),
                                    clingo_helper.create_function("__time"),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    expected = (
        expected_static_rules,
        expected_dynamic_rules,
        expected_statemachine_rules,
    )

    assert sorted(actual._rules.dynamic_rules) == sorted(expected)


def test_ruleset_with_comp() -> None:
    rules = (
        gdl.Sentence(
            gdl.Relation("static", (gdl.Subrelation(gdl.Variable("A")), gdl.Variable("B"))),
            (
                gdl.Literal(
                    gdl.Relation(
                        "__comp_not_equal",
                        (gdl.Subrelation(gdl.Variable("A")), gdl.Subrelation(gdl.Variable("B"))),
                    ),
                ),
            ),
        ),
    )
    ruleset = gdl.Ruleset.from_rules(rules)

    actual = ClingoInterpreter.from_ruleset(ruleset)
    expected_static_rules = (
        clingo_helper.PROGRAM_STATIC,
        (
            clingo_helper.create_rule(
                clingo_helper.create_literal(
                    atom=clingo_helper.create_atom(
                        clingo_helper.create_function(
                            "static_static",
                            arguments=(
                                clingo_helper.create_variable("A"),
                                clingo_helper.create_variable("B"),
                            ),
                        ),
                    ),
                ),
                (
                    clingo_helper.create_literal(
                        atom=clingo_helper.create_comparison(
                            clingo_helper.create_variable("A"),
                            (
                                clingo_helper.create_guard(
                                    clingo_ast.ComparisonOperator.NotEqual,
                                    clingo_helper.create_variable("B"),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    expected_statemachine_rules = (clingo_helper.PROGRAM_STATEMACHINE, ())
    expected = sorted(
        [
            expected_static_rules,
            expected_statemachine_rules,
        ],
    )
    assert sorted(actual._rules.dynamic_rules) == expected
