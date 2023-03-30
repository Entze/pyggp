import time
from unittest import mock

import clingo
import pytest
from common import Returner
from pyggp.exceptions.interpreter_exceptions import (
    ModelTimeoutInterpreterError,
    MoreThanOneModelInterpreterError,
    SolveTimeoutInterpreterError,
    TimeoutInterpreterError,
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

    with mock.patch("clingo.solving.SolveHandle.wait", return_value=False):
        with pytest.raises(ModelTimeoutInterpreterError):
            model = interpreter._get_model(ctl)
            actual = tuple(model)


def test_protected_get_model_unsat() -> None:
    interpreter = ClingoInterpreter()

    ctl = clingo.Control()
    ctl.configuration.solve.models = 2
    ctl.add("base", [], "a :- not a.")

    with pytest.raises(ClingoInterpreter.Unsat):
        model = interpreter._get_model(ctl)
        actual = tuple(model)


def test_protected_get_model_multiple() -> None:
    interpreter = ClingoInterpreter()

    ctl = clingo.Control()
    ctl.configuration.solve.models = 2
    ctl.add("base", [], "a :- not b. b :- not a.")

    with pytest.raises(MoreThanOneModelInterpreterError):
        model = interpreter._get_model(ctl)
        actual = tuple(model)


def test_protected_get_model_multiple_timeout() -> None:
    interpreter = ClingoInterpreter(model_timeout=0.1, solve_timeout=0.1)

    ctl = clingo.Control()
    ctl.configuration.solve.models = 2
    ctl.add("base", [], "a :- not b. b :- not a.")

    with mock.patch("clingo.solving.SolveHandle.wait", side_effect=Returner((True, False))):
        with pytest.raises(SolveTimeoutInterpreterError):
            model = interpreter._get_model(ctl)
            actual = tuple(model)
