import pathlib

import pytest

import pyggp.game_description_language as gdl
from pyggp.agents import MOISMCTSAgent
from pyggp.agents.tree_agents.agents import ONE_S_IN_NS
from pyggp.engine_primitives import Move, Role
from pyggp.gameclocks import DEFAULT_NO_TIMEOUT_CONFIGURATION, DEFAULT_START_CLOCK_CONFIGURATION
from pyggp.interpreters import ClingoInterpreter, Interpreter


@pytest.fixture
def corridor_str() -> str:
    if pathlib.Path("../src/games/dark_split_corridor(3,4).gdl").exists():
        return pathlib.Path("../src/games/dark_split_corridor(3,4).gdl").read_text()
    return pathlib.Path("src/games/dark_split_corridor(3,4).gdl").read_text()


@pytest.fixture
def corridor_ruleset(corridor_str) -> gdl.Ruleset:
    return gdl.parse(corridor_str)


@pytest.fixture
def corridor_interpreter(corridor_ruleset) -> Interpreter:
    return ClingoInterpreter.from_ruleset(corridor_ruleset, disable_cache=True)


@pytest.fixture
def corridor_left() -> Role:
    return Role(gdl.Subrelation(gdl.Relation("left")))


@pytest.fixture
def corridor_right() -> Role:
    return Role(gdl.Subrelation(gdl.Relation("right")))


@pytest.fixture
def a2() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(2)))))


@pytest.fixture
def a3() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(3)))))


@pytest.fixture
def a4() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(4)))))


@pytest.fixture
def b1() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(1)))))


@pytest.fixture
def b2() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(2)))))


@pytest.fixture
def b3() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(3)))))


@pytest.fixture
def b4() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(4)))))


@pytest.fixture
def c1() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(1)))))


@pytest.fixture
def c2() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(2)))))


@pytest.fixture
def c3() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(3)))))


@pytest.fixture
def a2_a3(a2, a3) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (a2, a3)))


@pytest.fixture
def a3_a4(a3, a4) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (a3, a4)))


@pytest.fixture
def b3_b4(b3, b4) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (b3, b4)))


@pytest.fixture
def c1_c2(c1, c2) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (c1, c2)))


@pytest.fixture
def c2_c3(c2, c3) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation(None, (c2, c3)))


@pytest.fixture
def block_a2_a3(a2_a3) -> Move:
    return Move(gdl.Subrelation(gdl.Relation("block", (a2_a3,))))


@pytest.fixture
def block_a3_a4(a3_a4) -> Move:
    return Move(gdl.Subrelation(gdl.Relation("block", (a3_a4,))))


@pytest.fixture
def block_b3_b4(b3_b4) -> Move:
    return Move(gdl.Subrelation(gdl.Relation("block", (b3_b4,))))


@pytest.fixture
def block_c1_c2(c1_c2) -> Move:
    return Move(gdl.Subrelation(gdl.Relation("block", (c1_c2,))))


@pytest.fixture
def block_c2_c3(c2_c3) -> Move:
    return Move(gdl.Subrelation(gdl.Relation("block", (c2_c3,))))


@pytest.fixture
def east() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("east"))


@pytest.fixture
def move_east(east) -> Move:
    return Move(gdl.Subrelation(gdl.Relation("move", (east,))))


@pytest.fixture
def left() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("left"))


@pytest.fixture
def right() -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("right"))


@pytest.fixture
def border_right_a2_a3(right, a2_a3) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("border", (right, a2_a3)))


@pytest.fixture
def control_left(left) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("control", (left,)))


@pytest.fixture
def at_left_b1(left, b1) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("at", (left, b1)))


@pytest.fixture
def at_left_c1(left, c1) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("at", (left, c1)))


@pytest.fixture
def at_right_b1(right, b1) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("at", (right, b1)))


@pytest.fixture
def at_right_c1(right, c1) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("at", (right, c1)))


def cell(col: str, row: int) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("", (gdl.Subrelation(gdl.Relation(col)), gdl.Subrelation(gdl.Number(row)))))


def border_role_cell_cell(role: Role, cell1: gdl.Subrelation, cell2: gdl.Subrelation) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("border", (role, gdl.Subrelation(gdl.Relation("", (cell1, cell2))))))


def revealed_role_cell_cell(role: Role, cell1: gdl.Subrelation, cell2: gdl.Subrelation) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("revealed", (role, gdl.Subrelation(gdl.Relation("", (cell1, cell2))))))


def test_possible_states_with_dark_split_corridor_1(
    corridor_interpreter,
    corridor_left,
    corridor_right,
    move_east,
    block_c1_c2,
    block_a2_a3,
    block_a3_a4,
    border_right_a2_a3,
    control_left,
    at_left_c1,
    at_right_b1,
    corridor_ruleset,
) -> None:
    state_0 = corridor_interpreter.get_init_state()
    move_0 = move_east
    state_1 = corridor_interpreter.get_next_state(state_0, {corridor_left: move_0})
    move_1 = block_c1_c2
    state_2 = corridor_interpreter.get_next_state(state_1, {corridor_right: move_1})
    view_2 = corridor_interpreter.get_sees_by_role(state_2, corridor_left)
    move_2 = block_a2_a3
    state_3 = corridor_interpreter.get_next_state(state_2, {corridor_left: move_2})
    move_3 = block_a3_a4
    state_4 = corridor_interpreter.get_next_state(state_3, {corridor_right: move_3})
    view_4 = corridor_interpreter.get_sees_by_role(state_4, corridor_left)

    assert view_4 == frozenset({border_right_a2_a3, control_left, at_left_c1, at_right_b1})

    agent_left = MOISMCTSAgent(interpreter=corridor_interpreter, skip_book=True)
    with agent_left:
        agent_left.prepare_match(
            role=corridor_left,
            ruleset=corridor_ruleset,
            startclock_config=DEFAULT_START_CLOCK_CONFIGURATION,
            playclock_config=DEFAULT_NO_TIMEOUT_CONFIGURATION,
        )

        tree = agent_left.trees[corridor_left]
        tree.expand(interpreter=corridor_interpreter)
        for child in tree.children.values():
            child.expand(interpreter=corridor_interpreter)
            for grandchild in child.children.values():
                grandchild.expand(interpreter=corridor_interpreter)
        tree.move = move_0

        agent_left.update(2, view_2, 0)

        tree = agent_left.trees[corridor_left]
        tree.move = move_2

        assert state_2 in tree.possible_states
        assert all(view_2 <= state for state in tree.possible_states)

        agent_left.update(4, view_4, 0)

        tree = agent_left.trees[corridor_left]
        assert state_4 in tree.possible_states
        assert all(view_4 <= state for state in tree.possible_states)

        assert view_4 not in tree.possible_states


def test_possible_states_with_dark_split_corridor_2(
    corridor_interpreter,
    corridor_left,
    corridor_right,
    block_b3_b4,
    block_c2_c3,
    block_c1_c2,
    move_east,
    control_left,
    at_right_c1,
    at_left_b1,
) -> None:
    state_0 = corridor_interpreter.get_init_state()
    view_0 = corridor_interpreter.get_sees_by_role(state_0, corridor_left)
    move_0 = block_b3_b4
    state_1 = corridor_interpreter.get_next_state(state_0, {corridor_left: move_0})
    move_1 = block_c2_c3
    state_2 = corridor_interpreter.get_next_state(state_1, {corridor_right: move_1})
    view_2 = corridor_interpreter.get_sees_by_role(state_2, corridor_left)
    move_2 = block_c1_c2
    state_3 = corridor_interpreter.get_next_state(state_2, {corridor_left: move_2})
    move_3 = move_east
    state_4 = corridor_interpreter.get_next_state(state_3, {corridor_right: move_3})
    view_4 = corridor_interpreter.get_sees_by_role(state_4, corridor_left)

    impossible = frozenset(
        {
            border_role_cell_cell(corridor_right, cell("c", 1), cell("c", 2)),
            at_right_c1,
            revealed_role_cell_cell(corridor_right, cell("c", 1), cell("c", 2)),
            at_left_b1,
            control_left,
            border_role_cell_cell(corridor_right, cell("b", 3), cell("b", 4)),
        },
    )

    agent_left = MOISMCTSAgent(interpreter=corridor_interpreter, skip_book=True)
    with agent_left:
        agent_left.prepare_match(
            role=corridor_left,
            ruleset=corridor_interpreter.ruleset,
            startclock_config=DEFAULT_START_CLOCK_CONFIGURATION,
            playclock_config=DEFAULT_NO_TIMEOUT_CONFIGURATION,
        )

        tree = agent_left.trees[corridor_left]

        tree.expand(interpreter=corridor_interpreter)
        for child in tree.children.values():
            child.expand(interpreter=corridor_interpreter)
            for grandchild in child.children.values():
                grandchild.expand(interpreter=corridor_interpreter)

        agent_left.update(0, view_0, 100 * ONE_S_IN_NS)
        tree = agent_left.trees[corridor_left]
        assert len(tree.possible_states) == 1
        tree.move = move_0
        agent_left.update(2, view_2, 100 * ONE_S_IN_NS)
        tree = agent_left.trees[corridor_left]
        assert len(tree.possible_states) == 15
        tree.move = move_2

        tree.expand(interpreter=corridor_interpreter)
        for child in tree.children.values():
            child.expand(interpreter=corridor_interpreter)

        agent_left.update(4, view_4, 100 * ONE_S_IN_NS)

        tree = agent_left.trees[corridor_left]

        assert impossible not in tree.possible_states
        assert len(tree.possible_states) == 15
