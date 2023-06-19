from typing import FrozenSet

import pyggp.game_description_language as gdl
import pytest
from pyggp.engine_primitives import Move, Role, State, Turn, View
from pyggp.exceptions.interpreter_exceptions import (
    GoalNotIntegerInterpreterError,
    MoreThanOneModelInterpreterError,
    MultipleGoalsInterpreterError,
    UnsatGoalInterpreterError,
    UnsatInitInterpreterError,
    UnsatLegalInterpreterError,
    UnsatNextInterpreterError,
    UnsatRolesInterpreterError,
    UnsatSeesInterpreterError,
    UnsatTerminalInterpreterError,
)
from pyggp.game_description_language import Number, Relation, String, Subrelation
from pyggp.interpreters import ClingoInterpreter, Interpreter


@pytest.mark.parametrize(
    ("view", "expected"),
    [
        (View(State(frozenset())), frozenset()),
        (
            View(
                State(frozenset({Subrelation(Relation(name="control", arguments=(Subrelation(Relation(name="x")),)))})),
            ),
            frozenset({Role(Subrelation(Relation("x")))}),
        ),
        (
            View(
                State(
                    frozenset(
                        {
                            Subrelation(Relation(name="control", arguments=(Subrelation(Relation(name="x")),))),
                            Subrelation(Relation(name="control", arguments=(Subrelation(Relation(name="y")),))),
                            Subrelation(Relation(name="unrelated")),
                            Subrelation(String("unrelated")),
                        },
                    ),
                ),
            ),
            frozenset({Role(Subrelation(Relation("x"))), Role(Subrelation(Relation("y")))}),
        ),
    ],
)
def test_get_roles_in_control(view: View, expected: FrozenSet[Role]) -> None:
    actual = Interpreter.get_roles_in_control(view)
    assert actual == expected


@pytest.fixture(params=[ClingoInterpreter.from_ruleset])
def interpreter_factory(request):
    return request.param


@pytest.mark.parametrize(
    ("rules_str", "expected"),
    [
        ("role(x). role(y).", frozenset({Role(Subrelation(Relation("x"))), Role(Subrelation(Relation("y")))})),
        ("role(1).", frozenset({Role(Subrelation(Number(1)))})),
        ("", frozenset()),
    ],
)
def test_get_roles(interpreter_factory, rules_str, expected) -> None:
    ruleset = gdl.parse(rules_str)
    interpreter = interpreter_factory(ruleset)

    actual = interpreter.get_roles()
    assert actual == expected


def test_get_roles_raises_on_unsat(interpreter_factory) -> None:
    ruleset = gdl.parse("role(x) :- not role(x).")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(UnsatRolesInterpreterError):
        interpreter.get_roles()


def test_get_roles_raises_on_multiple_models(interpreter_factory) -> None:
    ruleset = gdl.parse("role(x) :- not role(y). role(y) :- not role(x).")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(MoreThanOneModelInterpreterError):
        interpreter.get_roles()


@pytest.mark.parametrize(
    ("rules_str", "expected"),
    [
        ("init(x).", State(frozenset({Subrelation(Relation("x"))}))),
        ("init(1).", State(frozenset({Subrelation(Number(1))}))),
        ("init(control(x)).", State(frozenset({Subrelation(Relation("control", (Subrelation(Relation("x")),)))}))),
        (
            "init(yes) :- static. init(no) :- unrelated. init(no) :- not static. static.",
            State(frozenset({Subrelation(Relation("yes"))})),
        ),
    ],
)
def test_get_init_state(interpreter_factory, rules_str, expected) -> None:
    ruleset = gdl.parse(rules_str)
    interpreter = interpreter_factory(ruleset)

    actual = interpreter.get_init_state()
    assert actual == expected


def test_get_init_state_raises_on_unsat(interpreter_factory) -> None:
    ruleset = gdl.parse("init(x) :- not init(x).")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(UnsatInitInterpreterError):
        interpreter.get_init_state()


def test_get_init_state_raises_on_multiple_models(interpreter_factory) -> None:
    ruleset = gdl.parse("init(x) :- not init(y). init(y) :- not init(x).")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(MoreThanOneModelInterpreterError):
        interpreter.get_init_state()


@pytest.mark.parametrize(
    ("rules_str", "current", "turn", "expected"),
    [
        ("next(x).", State(frozenset()), {}, State(frozenset({Subrelation(Relation("x"))}))),
        (
            "next(x).",
            State(frozenset({Subrelation(Relation("x"))})),
            {},
            State(frozenset({Subrelation(Relation("x"))})),
        ),
        ("", State(frozenset()), {}, State(frozenset())),
        ("", State(frozenset({Subrelation(Relation("unrelated"))})), {}, State(frozenset())),
        ("init(y). next(x) :- true(y).", State(frozenset()), {}, State(frozenset())),
        (
            "init(y). next(x) :- true(y).",
            State(frozenset({Subrelation(Relation("y"))})),
            {},
            State(frozenset({Subrelation(Relation("x"))})),
        ),
        ("init(x). init(y). next(x) :- true(y). next(y) :- true(x).", State(frozenset()), {}, State(frozenset())),
        (
            "init(x). init(y). next(x) :- true(y). next(y) :- true(x).",
            State(frozenset({Subrelation(Relation("y"))})),
            {},
            State(frozenset({Subrelation(Relation("x"))})),
        ),
        (
            "init(x). init(y). next(x) :- true(y). next(y) :- true(x).",
            State(frozenset({Subrelation(Relation("x"))})),
            {},
            State(frozenset({Subrelation(Relation("y"))})),
        ),
        (
            "init(z). next(V) :- static(V). static(x) :- true(y). static(y) :- true(z).",
            State(frozenset()),
            {},
            State(frozenset()),
        ),
        (
            "init(z). next(V) :- static(V). static(x) :- static(y). static(y) :- true(z).",
            State(frozenset({Subrelation(Relation("z"))})),
            {},
            State(frozenset({Subrelation(Relation("x")), Subrelation(Relation("y"))})),
        ),
        (
            "init(z). next(x) :- not true(z).",
            State(frozenset({Subrelation(Relation("z"))})),
            {},
            State(frozenset()),
        ),
        (
            "init(z). next(x) :- not true(z).",
            State(frozenset()),
            {},
            State(frozenset({Subrelation(Relation("x"))})),
        ),
        (
            "init(z). role(p1). role(p2). next(mark(R)) :- role(R).",
            State(frozenset()),
            {},
            State(
                frozenset(
                    {
                        Subrelation(Relation("mark", (Subrelation(Relation("p1")),))),
                        Subrelation(Relation("mark", (Subrelation(Relation("p2")),))),
                    },
                ),
            ),
        ),
        (
            "role(p1). role(p2). next(mark(R)) :- role(R), does(R, mark). legal(R, mark) :- role(R).",
            State(frozenset()),
            {},
            State(frozenset()),
        ),
        (
            "role(p1). role(p2). next(mark(R)) :- role(R), does(R, mark). legal(R, mark) :- role(R).",
            State(frozenset()),
            {Role(Subrelation(Relation("p1"))): Move(Subrelation(Relation("mark")))},
            State(frozenset({Subrelation(Relation("mark", (Subrelation(Relation("p1")),)))})),
        ),
        (
            "role(p1). role(p2). next(mark(R)) :- role(R), does(R, mark). legal(R, mark) :- role(R).",
            State(frozenset()),
            {
                Role(Subrelation(Relation("p1"))): Move(Subrelation(Relation("mark"))),
                Role(Subrelation(Relation("p2"))): Move(Subrelation(Relation("mark"))),
            },
            State(
                frozenset(
                    {
                        Subrelation(Relation("mark", (Subrelation(Relation("p1")),))),
                        Subrelation(Relation("mark", (Subrelation(Relation("p2")),))),
                    },
                ),
            ),
        ),
    ],
)
def test_get_next_state(interpreter_factory, rules_str, current, turn, expected) -> None:
    ruleset = gdl.parse(rules_str)
    interpreter = interpreter_factory(ruleset)

    actual = interpreter.get_next_state(current, Turn(turn))
    assert actual == expected


def test_get_next_state_raises_on_unsat(interpreter_factory) -> None:
    ruleset = gdl.parse("next(x) :- static. static :- not static.")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(UnsatNextInterpreterError):
        interpreter.get_next_state(State(frozenset()), Turn())


def test_get_next_state_raises_on_multiple_models(interpreter_factory) -> None:
    ruleset = gdl.parse("next(x) :- static1. static1 :- not static2. static2 :- not static1.")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(MoreThanOneModelInterpreterError):
        interpreter.get_next_state(State(frozenset()), Turn())


@pytest.mark.parametrize(
    ("rules_str", "current", "expected"),
    [
        ("", State(frozenset()), {}),
        ("", State(frozenset({Subrelation(Relation("unrelated"))})), {}),
        (
            "init(a). role(x). role(y). sees(x, X) :- true(X).",
            State(frozenset({Subrelation(Relation("a"))})),
            {Role(Subrelation(Relation("x"))): View(State(frozenset({Subrelation(Relation("a"))})))},
        ),
        (
            "init(a). role(x). role(y). sees(Everyone, X) :- role(Everyone), true(X).",
            State(frozenset({Subrelation(Relation("a"))})),
            {
                Role(Subrelation(Relation("x"))): View(State(frozenset({Subrelation(Relation("a"))}))),
                Role(Subrelation(Relation("y"))): View(State(frozenset({Subrelation(Relation("a"))}))),
            },
        ),
        (
            "init(a). init(b). role(x). role(y). sees(x, a) :- true(a). sees(y, b) :- true(b).",
            State(frozenset({Subrelation(Relation("a")), Subrelation(Relation("b"))})),
            {
                Role(Subrelation(Relation("x"))): View(State(frozenset({Subrelation(Relation("a"))}))),
                Role(Subrelation(Relation("y"))): View(State(frozenset({Subrelation(Relation("b"))}))),
            },
        ),
        (
            "init(a). init(b). role(x). role(y). sees(x, a) :- true(a). sees(y, b) :- true(b).",
            State(frozenset({Subrelation(Relation("a"))})),
            {
                Role(Subrelation(Relation("x"))): View(State(frozenset({Subrelation(Relation("a"))}))),
            },
        ),
        (
            "init(a). init(b). role(x). role(y). sees(x, a) :- true(a). sees(y, b) :- true(b).",
            State(frozenset({Subrelation(Relation("b"))})),
            {
                Role(Subrelation(Relation("y"))): View(State(frozenset({Subrelation(Relation("b"))}))),
            },
        ),
        (
            "init(a). init(b). "
            "role(x). role(y). sees(x, a) :- true(a), not true(b). sees(y, b) :- not true(a), true(b).",
            State(frozenset({Subrelation(Relation("b"))})),
            {
                Role(Subrelation(Relation("y"))): View(State(frozenset({Subrelation(Relation("b"))}))),
            },
        ),
    ],
)
def test_get_sees(interpreter_factory, rules_str, current, expected) -> None:
    ruleset = gdl.parse(rules_str)
    interpreter = interpreter_factory(ruleset)

    actual = interpreter.get_sees(current)
    assert actual == expected


def test_get_sees_throws_on_unsat(interpreter_factory) -> None:
    ruleset = gdl.parse("role(x). sees(x, a) :- true(a), static. static :- not static.")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(UnsatSeesInterpreterError):
        interpreter.get_sees(State(frozenset()))


def test_get_sees_throws_on_multiple_models(interpreter_factory) -> None:
    ruleset = gdl.parse("role(x). sees(x, a) :- true(a), static1. static1 :- not static2. static2 :- not static1.")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(MoreThanOneModelInterpreterError):
        interpreter.get_sees(State(frozenset()))


@pytest.mark.parametrize(
    ("rules_str", "current", "expected"),
    [
        ("", State(frozenset()), {}),
        ("", State(frozenset({Subrelation(Relation("unrelated"))})), {}),
        (
            "role(x). legal(x, action).",
            State(frozenset()),
            {Role(Subrelation(Relation("x"))): frozenset({Move(Subrelation(Relation("action")))})},
        ),
        ("init(mark). role(x). legal(x, action) :- true(mark).", State(frozenset()), {}),
        (
            "init(mark). role(x). legal(x, action) :- true(mark).",
            State(frozenset({Subrelation(Relation("mark"))})),
            {Role(Subrelation(Relation("x"))): frozenset({Move(Subrelation(Relation("action")))})},
        ),
        (
            "init(mark1). init(mark2). role(x). legal(x, action1) :- true(mark1). legal(x, action2) :- true(mark2).",
            State(frozenset({Subrelation(Relation("mark1")), Subrelation(Relation("mark2"))})),
            {
                Role(Subrelation(Relation("x"))): frozenset(
                    {Move(Subrelation(Relation("action1"))), Move(Subrelation(Relation("action2")))},
                ),
            },
        ),
        (
            "init(mark1). init(mark2). role(x). role(y). "
            "legal(x, action1) :- true(mark1). "
            "legal(x, action2) :- not true(mark2). "
            "legal(y, action1) :- not true(mark1). "
            "legal(y, action2) :- true(mark2). ",
            State(frozenset({Subrelation(Relation("mark1"))})),
            {
                Role(Subrelation(Relation("x"))): frozenset(
                    {Move(Subrelation(Relation("action1"))), Move(Subrelation(Relation("action2")))},
                ),
            },
        ),
    ],
)
def test_get_legal_moves(interpreter_factory, rules_str, current, expected) -> None:
    ruleset = gdl.parse(rules_str)
    interpreter = interpreter_factory(ruleset)

    actual = interpreter.get_legal_moves(current)
    assert actual == expected


def test_get_legal_moves_throws_on_unsat(interpreter_factory) -> None:
    ruleset = gdl.parse("role(x). legal(x, action) :- true(a), static. static :- not static.")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(UnsatLegalInterpreterError):
        interpreter.get_legal_moves(State(frozenset()))


def test_get_legal_moves_throws_on_multiple_models(interpreter_factory) -> None:
    ruleset = gdl.parse(
        "role(x). legal(x, action) :- true(a), static1. static1 :- not static2. static2 :- not static1.",
    )
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(MoreThanOneModelInterpreterError):
        interpreter.get_legal_moves(State(frozenset()))


@pytest.mark.parametrize(
    ("rules_str", "current", "expected"),
    [
        ("", State(frozenset()), {}),
        ("", State(frozenset({Subrelation(Relation("unrelated"))})), {}),
        ("role(x). goal(x, 100).", State(frozenset()), {Role(Subrelation(Relation("x"))): 100}),
        (
            "init(mark). role(x). goal(x, 100) :- true(mark).",
            State(frozenset()),
            {Role(Subrelation(Relation("x"))): None},
        ),
        (
            "init(mark). role(x). goal(x, 100) :- true(mark).",
            State(frozenset({Subrelation(Relation("mark"))})),
            {Role(Subrelation(Relation("x"))): 100},
        ),
        (
            "init(win). init(lose). role(x). "
            "goal(x, 0) :- true(lose). "
            "goal(x, 50) :- not true(lose), not true(win). "
            "goal(x, 100) :- true(win).",
            State(frozenset({Subrelation(Relation("win"))})),
            {Role(Subrelation(Relation("x"))): 100},
        ),
        (
            "init(win). init(lose). role(x). "
            "goal(x, 0) :- true(lose). "
            "goal(x, 50) :- not true(lose), not true(win). "
            "goal(x, 100) :- true(win).",
            State(frozenset()),
            {Role(Subrelation(Relation("x"))): 50},
        ),
        (
            "init(a). init(b). role(x). role(y). goal(x, 100) :- true(a). goal(y, 100) :- true(b).",
            State(frozenset()),
            {Role(Subrelation(Relation("x"))): None, Role(Subrelation(Relation("y"))): None},
        ),
    ],
)
def test_get_goals(interpreter_factory, rules_str, current, expected) -> None:
    ruleset = gdl.parse(rules_str)
    interpreter = interpreter_factory(ruleset)

    actual = interpreter.get_goals(current)
    assert actual == expected


def test_get_goals_throws_on_unsat(interpreter_factory) -> None:
    ruleset = gdl.parse("role(x). goal(x, 100) :- true(a), static. static :- not static.")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(UnsatGoalInterpreterError):
        interpreter.get_goals(State(frozenset()))


def test_get_goals_throws_on_multiple_models(interpreter_factory) -> None:
    ruleset = gdl.parse("role(x). goal(x, 100) :- static1. static1 :- not static2. static2 :- not static1.")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(MoreThanOneModelInterpreterError):
        interpreter.get_goals(State(frozenset()))


def test_get_goals_throws_on_multiple_goals(interpreter_factory) -> None:
    ruleset = gdl.parse("role(x). goal(x, 0). goal(x, 100).")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(MultipleGoalsInterpreterError):
        interpreter.get_goals(State(frozenset()))


def test_get_goals_throws_on_goal_not_integer(interpreter_factory) -> None:
    ruleset = gdl.parse("role(x). goal(x, a).")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(GoalNotIntegerInterpreterError):
        interpreter.get_goals(State(frozenset()))


@pytest.mark.parametrize(
    ("rules_str", "current", "expected"),
    [
        ("", State(frozenset()), False),
        ("", State(frozenset({Subrelation(Relation("unrelated"))})), False),
        ("terminal :- true(a).", State(frozenset()), False),
        ("init(a). terminal :- true(a).", State(frozenset({Subrelation(Relation("a"))})), True),
        ("init(marked). terminal :- not open. open :- not true(marked).", State(frozenset()), False),
        (
            "init(marked). terminal :- not open. open :- not true(marked).",
            State(frozenset({Subrelation(Relation("marked"))})),
            True,
        ),
    ],
)
def test_is_terminal(interpreter_factory, rules_str, current, expected) -> None:
    ruleset = gdl.parse(rules_str)
    interpreter = interpreter_factory(ruleset)

    actual = interpreter.is_terminal(current)
    assert actual == expected


def test_is_terminal_throws_on_unsat(interpreter_factory) -> None:
    ruleset = gdl.parse("terminal :- true(a), static. static :- not static.")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(UnsatTerminalInterpreterError):
        interpreter.is_terminal(State(frozenset()))


def test_is_terminal_throws_on_multiple_models(interpreter_factory) -> None:
    ruleset = gdl.parse("terminal :- static1. static1 :- not static2. static2 :- not static1.")
    interpreter = interpreter_factory(ruleset)

    with pytest.raises(MoreThanOneModelInterpreterError):
        interpreter.is_terminal(State(frozenset()))
