import pathlib
from typing import Mapping, Optional

import pyggp.game_description_language as gdl
import pytest
from pyggp.engine_primitives import Move, Role, State, Turn
from pyggp.interpreters import ClingoInterpreter, Interpreter


@pytest.fixture(scope="session")
def kalaha_str() -> str:
    return pathlib.Path("../src/games/kalaha(6,6).gdl").read_text()


@pytest.fixture(scope="session")
def kalaha_ruleset(kalaha_str) -> gdl.Ruleset:
    return gdl.parse(kalaha_str)


@pytest.fixture(scope="session")
def kalaha_interpreter(kalaha_ruleset) -> Interpreter:
    return ClingoInterpreter.from_ruleset(kalaha_ruleset)


@pytest.fixture()
def south() -> Role:
    return Role(gdl.Subrelation(gdl.Relation("south")))


@pytest.fixture()
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
) -> State:
    subrelations = set()
    roles = frozenset((Role(gdl.Subrelation(gdl.Relation("south"))), Role(gdl.Subrelation(gdl.Relation("north")))))

    stores = stores or {}
    houses = houses or {}
    for role in roles:
        subrelations.add(store(role, stores.get(role, 0)))
        for house_ in range(1, 7):
            subrelations.add(house(role, house_, houses.get(role, {}).get(house_, 0)))

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
        houses={north: {1: 6, 2: 6, 3: 6, 4: 6, 5: 6, 6: 6}, south: {1: 6, 2: 6, 3: 6, 4: 6, 5: 6, 6: 6}},
    )

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_single_stone_non_capture(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)
    state = get_state(p1, houses={p1: {1: 1, 2: 1}, p2: {6: 1}})

    move = Move(gdl.Subrelation(gdl.Number(1)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, houses={p1: {2: 2}, p2: {6: 1}})

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
    state = get_state(p1, houses={p1: {1: 1}, p2: {5: 1, 6: 1}})

    move = Move(gdl.Subrelation(gdl.Number(1)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, stores={p1: 2}, houses={p2: {6: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_single_stone_move_again(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)
    state = get_state(p1, houses={p1: {6: 1, 1: 1}})

    move = Move(gdl.Subrelation(gdl.Number(6)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p1, stores={p1: 1}, houses={p1: {1: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_move_again(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {1: 6}})

    move = Move(gdl.Subrelation(gdl.Number(1)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p1, stores={p1: 1}, houses={p1: {2: 1, 3: 1, 4: 1, 5: 1, 6: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_capture(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {3: 2}, p2: {5: 3, 1: 1}})

    move = Move(gdl.Subrelation(gdl.Number(3)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, stores={p1: 4}, houses={p1: {4: 1}, p2: {1: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_spill(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {6: 2}})

    move = Move(gdl.Subrelation(gdl.Number(6)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p1, stores={p1: 1}, houses={p2: {1: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_skips_other_store(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {6: 8, 1: 1}})

    move = Move(gdl.Subrelation(gdl.Number(6)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p1, stores={p1: 1}, houses={p1: {1: 2}, p2: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_spill_capture(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {6: 8}, p2: {6: 2}})

    move = Move(gdl.Subrelation(gdl.Number(6)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(p2, stores={p1: 5}, houses={p2: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1}})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_overspill(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {3: 14}})

    move = Move(gdl.Subrelation(gdl.Number(3)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(
        p2,
        stores={p1: 1},
        houses={p1: {4: 2, 5: 1, 6: 1, 1: 1, 2: 1, 3: 1}, p2: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}},
    )

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_overspill_move_again(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {6: 14}})

    move = Move(gdl.Subrelation(gdl.Number(6)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(
        p1,
        stores={p1: 2},
        houses={p1: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}, p2: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}},
    )

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_overspill_capture(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {3: 13}, p2: {3: 1}})

    move = Move(gdl.Subrelation(gdl.Number(3)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(
        p2,
        stores={p1: 4},
        houses={p1: {4: 1, 5: 1, 6: 1, 3: 0, 1: 1, 2: 1}, p2: {1: 1, 2: 1, 3: 0, 4: 1, 5: 1}},
    )

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_sweep_on_move_again(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {6: 1}, p2: {5: 5}})

    move = Move(gdl.Subrelation(gdl.Number(6)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(stores={p1: 1, p2: 5})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_next_state_sweep(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {4: 2, 6: 1, 1: 5}})

    move = Move(gdl.Subrelation(gdl.Number(4)))

    turn = Turn({p1: move})

    actual = kalaha_interpreter.get_next_state(state, turn)

    expected = get_state(stores={p1: 8, p2: 0})

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_legal_all(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}})

    actual = kalaha_interpreter.get_legal_moves_by_role(state, p1)

    expected = frozenset(Move(gdl.Subrelation(gdl.Number(m))) for m in range(1, 7))

    assert actual == expected


@pytest.mark.parametrize(("p1", "p2"), [("north", "south"), ("south", "north")])
def test_legal_missing(kalaha_interpreter, p1, p2, request) -> None:
    p1 = request.getfixturevalue(p1)
    p2 = request.getfixturevalue(p2)

    state = get_state(p1, houses={p1: {1: 1, 2: 1, 3: 0, 4: 1, 5: 1, 6: 1}})

    actual = kalaha_interpreter.get_legal_moves_by_role(state, p1)

    expected = frozenset(
        (Move(gdl.Subrelation(gdl.Number(m))) for m in (1, 2, 4, 5, 6)),
    )

    assert actual == expected
