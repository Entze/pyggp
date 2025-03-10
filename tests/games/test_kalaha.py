import pathlib
from typing import Mapping, Optional

import pytest

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Development, DevelopmentStep, Move, Role, State, Turn
from pyggp.interpreters import ClingoRegroundingInterpreter, Interpreter
from pyggp.records import PerfectInformationRecord


@pytest.fixture(scope="session")
def kalaha_str() -> str:
    if pathlib.Path("src/games/kalaha(4,3).gdl").exists():
        return pathlib.Path("src/games/kalaha(4,3).gdl").read_text()
    return pathlib.Path("../src/games/kalaha(4,3).gdl").read_text()


@pytest.fixture(scope="session")
def kalaha_ruleset(kalaha_str) -> gdl.Ruleset:
    return gdl.parse(kalaha_str)


@pytest.fixture(scope="session")
def kalaha_interpreter(kalaha_ruleset) -> Interpreter:
    return ClingoRegroundingInterpreter.from_ruleset(kalaha_ruleset)


@pytest.fixture
def south() -> Role:
    return Role(gdl.Subrelation(gdl.Relation("south")))


@pytest.fixture
def north() -> Role:
    return Role(gdl.Subrelation(gdl.Relation("north")))


def house(role: Role, number: int, stones: Optional[int] = None) -> gdl.Subrelation:
    if stones is None:
        return gdl.Subrelation(gdl.Relation("house", (role, gdl.Subrelation(gdl.Number(number)))))
    return gdl.Subrelation(
        gdl.Relation("house", (role, gdl.Subrelation(gdl.Number(number)), gdl.Subrelation(gdl.Number(stones)))),
    )


def store(role: Role, stones: int) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("store", (role, gdl.Subrelation(gdl.Number(stones)))))


def control(role: Role) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("control", (role,)))


def get_state(
    role_in_control: Optional[Role] = None,
    stores: Optional[Mapping[Role, int]] = None,
    houses: Optional[Mapping[Role, Mapping[int, int]]] = None,
    nr_of_houses: int = 4,
    nr_of_stones: int = 0,
) -> State:
    subrelations = set()
    roles = frozenset((Role(gdl.Subrelation(gdl.Relation("south"))), Role(gdl.Subrelation(gdl.Relation("north")))))

    stores = stores or {}
    houses = houses or {}
    for role in roles:
        subrelations.add(store(role, stores.get(role, 0)))
        for house_ in range(1, nr_of_houses + 1):
            subrelations.add(house(role, house_, houses.get(role, {}).get(house_, nr_of_stones)))

    if role_in_control is not None:
        subrelations.add(control(role_in_control))

    return State(frozenset(subrelations))


def test_roles(kalaha_interpreter, north, south) -> None:
    actual = kalaha_interpreter.get_roles()

    expected = frozenset((north, south))

    assert actual == expected


def test_init_state(kalaha_interpreter, north, south) -> None:
    actual = kalaha_interpreter.get_init_state()

    expected = get_state(
        north,
        nr_of_houses=4,
        nr_of_stones=3,
    )

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_single_stone_non_capture(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)
    state = get_state(p1, houses={p1: {1: 1, 2: 1}, p2: {4: 1}})

    move = Move(gdl.Subrelation(gdl.Number(1)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, houses={p1: {2: 2}, p2: {4: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_single_stone_capture_empty(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)
    state = get_state(p1, houses={p1: {1: 1}, p2: {1: 1}})

    move = Move(gdl.Subrelation(gdl.Number(1)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, stores={p1: 1}, houses={p2: {1: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_single_stone_capture_nonempty(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)
    state = get_state(p1, houses={p1: {1: 1}, p2: {3: 1, 4: 1}})

    move = Move(gdl.Subrelation(gdl.Number(1)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, stores={p1: 2}, houses={p2: {4: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_single_stone_move_again(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)
    state = get_state(p1, houses={p1: {4: 1, 1: 1}})

    move = Move(gdl.Subrelation(gdl.Number(4)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p1, stores={p1: 1}, houses={p1: {1: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_move_again(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {1: 4}})

    move = Move(gdl.Subrelation(gdl.Number(1)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p1, stores={p1: 1}, houses={p1: {1: 0, 2: 1, 3: 1, 4: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_capture(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {1: 2}, p2: {2: 3, 1: 1}})

    move = Move(gdl.Subrelation(gdl.Number(1)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, stores={p1: 4}, houses={p1: {2: 1}, p2: {1: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_spill(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {4: 2}})

    move = Move(gdl.Subrelation(gdl.Number(4)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, stores={p1: 1}, houses={p2: {1: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_skips_other_store(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {4: 6, 1: 1}})

    move = Move(gdl.Subrelation(gdl.Number(4)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, stores={p1: 1}, houses={p1: {1: 2}, p2: {1: 1, 2: 1, 3: 1, 4: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_spill_capture(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {4: 6}, p2: {4: 2}})

    move = Move(gdl.Subrelation(gdl.Number(4)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, stores={p1: 5}, houses={p2: {1: 1, 2: 1, 3: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_overspill(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {3: 10}})

    move = Move(gdl.Subrelation(gdl.Number(3)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(
        p2,
        stores={p1: 1},
        houses={p1: {1: 1, 2: 1, 3: 1, 4: 2}, p2: {1: 1, 2: 1, 3: 1, 4: 1}},
    )

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_overspill_move_again(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {4: 10}})

    move = Move(gdl.Subrelation(gdl.Number(4)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(
        p1,
        stores={p1: 2},
        houses={p1: {1: 1, 2: 1, 3: 1, 4: 1}, p2: {1: 1, 2: 1, 3: 1, 4: 1}},
    )

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_overspill_capture(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {3: 9}, p2: {2: 1}})

    move = Move(gdl.Subrelation(gdl.Number(3)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(
        p2,
        stores={p1: 4},
        houses={p1: {4: 1, 3: 0, 1: 1, 2: 1}, p2: {1: 1, 2: 0, 3: 1, 4: 1}},
    )

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_legal_all(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {1: 1, 2: 1, 3: 1, 4: 1}})

    actual = kalaha_interpreter.get_legal_moves_by_role(state, p1)

    expected = frozenset(Move(gdl.Subrelation(gdl.Number(m))) for m in range(1, 5))

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_legal_missing(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {1: 1, 2: 1, 3: 0, 4: 1}})

    actual = kalaha_interpreter.get_legal_moves_by_role(state, p1)

    expected = frozenset(
        (Move(gdl.Subrelation(gdl.Number(m))) for m in (1, 2, 4)),
    )

    assert actual == expected


def test_is_terminal(kalaha_interpreter) -> None:
    state = kalaha_interpreter.get_init_state()

    actual = kalaha_interpreter.is_terminal(state)
    expected = False

    assert actual == expected


def test_developments(kalaha_interpreter, north) -> None:
    state = kalaha_interpreter.get_init_state()
    move = Move(gdl.Subrelation(gdl.Number(3)))
    turn = Turn({north: move})
    next_state = kalaha_interpreter.get_next_state(state, turn)

    record = PerfectInformationRecord(states={0: state, 1: next_state})

    actual = tuple(kalaha_interpreter.get_developments(record))

    expected = (
        Development(
            (
                DevelopmentStep(
                    state=state,
                    turn=turn,
                ),
                DevelopmentStep(
                    state=next_state,
                    turn=None,
                ),
            ),
        ),
    )

    assert actual == expected
