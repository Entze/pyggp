import pathlib
import random
from random import shuffle

import pytest
from pytest_unordered import unordered

from pyggp.engine_primitives import State, Turn
from pyggp.interpreters import ClingoInterpreter
from pyggp.interpreters.dark_split_corridor_34_interpreter import *
from pyggp.interpreters.dark_split_corridor_34_interpreter import _border


@pytest.fixture
def ruleset_path() -> pathlib.Path:
    return pathlib.Path("./src/games/dark_split_corridor(3,4).gdl")


@pytest.fixture
def ruleset_str(ruleset_path) -> str:
    return ruleset_path.read_text()


@pytest.fixture
def ruleset_gdl(ruleset_str) -> gdl.Ruleset:
    return gdl.parse(ruleset_str)


@pytest.fixture
def reference_interpreter(ruleset_gdl) -> ClingoInterpreter:
    return ClingoInterpreter.from_ruleset(ruleset_gdl, disable_cache=True)


@pytest.fixture
def interpreter(ruleset_gdl) -> DarkSplitCorridor34Interpreter:
    return DarkSplitCorridor34Interpreter.from_ruleset(ruleset=ruleset_gdl, disable_cache=True)


def test_get_roles(reference_interpreter: ClingoInterpreter, interpreter: DarkSplitCorridor34Interpreter) -> None:
    expected = reference_interpreter.get_roles()
    actual = interpreter.get_roles()

    assert actual == expected


def test_get_init_state(reference_interpreter: ClingoInterpreter, interpreter: DarkSplitCorridor34Interpreter) -> None:
    expected = reference_interpreter.get_init_state()
    actual = interpreter.get_init_state()

    assert actual == expected


_states_without_borders = list(
    (State(frozenset({at(left, pos1), at(right, pos2), control(in_control)})),)
    for pos1 in (a1, a2, a3, a4, b1, b2, b3, b4, c1, c2, c3, c4)
    for pos2 in (a1, a2, a3, a4, b1, b2, b3, b4, c1, c2, c3, c4)
    for in_control in (left, right)
    if not (pos1 in (a4, b4, c4) and pos2 in (a4, b4, c4))
    and not (pos1 in (a4, b4, c4) and in_control == left)
    and not (pos2 in (a4, b4, c4) and in_control == right)
)

_states_with_one_or_two_borders = list(
    (
        State(
            frozenset(
                {
                    at(left, pos1),
                    at(right, pos2),
                    _border(left, crossing1),
                    _border(left, crossing2),
                    control(in_control),
                }
            )
        ),
    )
    for pos1 in (a2, a3, a4, b1, b2, b3, b4, c2, c3, c4)
    for pos2 in (a1, a2, a3, a4, b1, b2, b3, b4, c1, c2, c3, c4)
    for in_control in (left, right)
    for crossing1 in relevant_crossings
    for crossing2 in relevant_crossings
    if not (pos1 in (a4, b4, c4) and pos2 in (a4, b4, c4))
    and not (pos1 in (a4, b4, c4) and in_control == left)
    and not (pos2 in (a4, b4, c4) and in_control == right)
)

rnd = random.Random(0)

states_without_borders = rnd.sample(_states_without_borders, k=16)
states_with_one_or_two_borders = rnd.sample(_states_with_one_or_two_borders, k=16)

states = {
    *states_without_borders,
    *states_with_one_or_two_borders,
    (State(frozenset((at(left, b2), at(right, b2), control(left), border(left, (b2, c2))))),),
    (State(frozenset((at(left, b1), at(right, b1), border(right, (b1, b2)), control(right)))),),
    (
        State(
            frozenset((at(left, b2), at(right, b1), border(right, (b1, b2)), revealed(right, (b1, b2)), control(right)))
        ),
    ),
    (
        State(
            frozenset(
                (
                    at(left, b1),
                    at(right, b1),
                    control(left),
                    border(left, (b1, b2)),
                    border(right, (b1, b2)),
                    revealed(left, (b1, b2)),
                )
            )
        ),
    ),
    (
        State(
            frozenset(
                (
                    at(left, b1),
                    at(right, b1),
                    control(left),
                    border(left, (b1, b2)),
                    border(left, (a2, b2)),
                    revealed(left, (b1, b2)),
                    border(right, (b1, b2)),
                    border(right, (b2, c2)),
                )
            )
        ),
    ),
    (
        State(
            frozenset((at(left, b2), at(right, b1), border(right, (b1, b2)), revealed(right, (b1, b2)), control(right)))
        ),
    ),
    (
        State(
            frozenset(
                (
                    at(left, a1),
                    border(left, (a2, a3)),
                    border(left, (a3, a4)),
                    border(left, (a1, b1)),
                    border(left, (a3, b3)),
                    border(left, (b1, b2)),
                    border(left, (b3, b4)),
                    border(left, (b1, c1)),
                    border(left, (b2, c2)),
                    border(left, (c1, c2)),
                    border(left, (c2, c3)),
                    at(right, b2),
                    control(right),
                )
            )
        ),
    ),
    (
        State(
            frozenset(
                (
                    at(left, a2),
                    border(left, (a2, a3)),
                    border(left, (a3, a4)),
                    border(left, (a1, b1)),
                    border(left, (a3, b3)),
                    border(left, (b1, b2)),
                    border(left, (b3, b4)),
                    border(left, (b1, c1)),
                    border(left, (b2, c2)),
                    border(left, (c1, c2)),
                    border(left, (c2, c3)),
                    at(right, b2),
                    control(right),
                )
            )
        ),
    ),
    (
        State(
            frozenset(
                (
                    at(left, c3),
                    border(left, (a2, a3)),
                    border(left, (a3, a4)),
                    border(left, (a1, b1)),
                    border(left, (a3, b3)),
                    border(left, (b1, b2)),
                    border(left, (b3, b4)),
                    border(left, (b1, c1)),
                    border(left, (b2, c2)),
                    border(left, (c1, c2)),
                    border(left, (c2, c3)),
                    at(right, b2),
                    control(right),
                )
            )
        ),
    ),
    (
        State(
            frozenset(
                (
                    at(left, a3),
                    border(left, (a2, a3)),
                    border(left, (a3, b3)),
                    at(right, b1),
                    control(right),
                )
            )
        ),
    ),
    (
        State(
            frozenset(
                (
                    at(left, b3),
                    border(left, (a3, a4)),
                    border(left, (b3, b4)),
                    at(right, b1),
                    control(right),
                )
            )
        ),
    ),
    (
        State(
            frozenset(
                {
                    at(left, a1),
                    at(right, b2),
                    border(left, (a1, a2)),
                    border(left, (a2, b2)),
                    border(left, (b2, b3)),
                    border(left, (b2, c2)),
                    border(right, (a1, b1)),
                    border(right, (a2, a3)),
                    border(right, (a2, b2)),
                    border(right, (b2, b3)),
                    border(right, (b3, b4)),
                    border(right, (b3, c3)),
                    border(right, (c1, c2)),
                    control(right),
                    revealed(right, (a1, b1)),
                    revealed(right, (b2, b3)),
                }
            )
        ),
    ),
    (
        State(
            frozenset(
                {
                    at(left, c1),
                    at(right, c1),
                    border(left, (a1, a2)),
                    border(left, (b1, b2)),
                    border(left, (b2, b3)),
                    border(left, (b3, b4)),
                    border(left, (b3, c3)),
                    border(left, (c2, c3)),
                    border(left, (c3, c4)),
                    border(right, (a1, a2)),
                    border(right, (a1, b1)),
                    border(right, (a2, a3)),
                    border(right, (a2, b2)),
                    border(right, (a3, b3)),
                    border(right, (b2, c2)),
                    border(right, (b3, b4)),
                    border(right, (c1, c2)),
                    border(right, (c2, c3)),
                    control(right),
                    revealed(right, (c1, c2)),
                }
            )
        ),
    ),
}


@pytest.mark.parametrize(
    ("state", "turn"),
    (
        (State(frozenset((at(left, b2), at(right, b2), control(left)))), Turn({left: move_north})),
        (
            State(frozenset((at(left, b2), at(right, b2), control(left), border(left, (b2, c2))))),
            Turn({left: move_east}),
        ),
        (State(frozenset((at(left, b2), at(right, b2), control(left)))), Turn({left: block((b2, b3))})),
    ),
)
def test_get_next_state(
    reference_interpreter: ClingoInterpreter, interpreter: DarkSplitCorridor34Interpreter, state: State, turn: Turn
) -> None:
    expected = reference_interpreter.get_next_state(state, turn)
    actual = interpreter.get_next_state(state, turn)
    assert actual == expected


@pytest.mark.parametrize(("state",), states)
def test_get_all_next_states(
    reference_interpreter: ClingoInterpreter, interpreter: DarkSplitCorridor34Interpreter, state: State
) -> None:
    if reference_interpreter.is_terminal(state):
        return
    expected = tuple(reference_interpreter.get_all_next_states(state))
    actual = tuple(interpreter.get_all_next_states(state))

    assert actual == unordered(expected)


@pytest.mark.parametrize(("state",), states)
def test_get_sees(
    reference_interpreter: ClingoInterpreter, interpreter: DarkSplitCorridor34Interpreter, state: State
) -> None:
    if reference_interpreter.is_terminal(state):
        return
    expected = reference_interpreter.get_sees(state)
    actual = interpreter.get_sees(state)

    assert actual == expected


@pytest.mark.parametrize(("state",), states)
def test_get_legal_moves(
    reference_interpreter: ClingoInterpreter, interpreter: DarkSplitCorridor34Interpreter, state: State
) -> None:
    if reference_interpreter.is_terminal(state):
        return
    expected = reference_interpreter.get_legal_moves(state)
    actual = interpreter.get_legal_moves(state)

    assert actual == expected


@pytest.mark.parametrize(("state",), states)
def test_get_goals(
    reference_interpreter: ClingoInterpreter, interpreter: DarkSplitCorridor34Interpreter, state: State
) -> None:
    expected = reference_interpreter.get_goals(state)
    actual = interpreter.get_goals(state)

    assert actual == expected


@pytest.mark.parametrize(("state",), states)
def test_is_terminal(
    reference_interpreter: ClingoInterpreter, interpreter: DarkSplitCorridor34Interpreter, state: State
) -> None:
    expected = reference_interpreter.is_terminal(state)
    actual = interpreter.is_terminal(state)

    assert actual == expected


@pytest.mark.parametrize(("record", "last_ply_is_final_state"), ())
def test_get_developments(
    reference_interpreter: ClingoInterpreter,
    interpreter: DarkSplitCorridor34Interpreter,
    record: Record,
    last_ply_is_final_state: Optional[bool],
) -> None:
    expected = reference_interpreter.get_developments(record, last_ply_is_final_state=last_ply_is_final_state)
    actual = interpreter.get_developments(record, last_ply_is_final_state=last_ply_is_final_state)

    assert actual == expected
