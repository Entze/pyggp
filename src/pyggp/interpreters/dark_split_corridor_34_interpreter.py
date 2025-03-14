import dataclasses
from collections import deque
from dataclasses import dataclass
from typing import (
    Deque,
    Dict,
    Final,
    FrozenSet,
    Iterator,
    Mapping,
    MutableSequence,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Development, Move, Role, State, View
from pyggp.interpreters import ClingoInterpreter
from pyggp.interpreters.base_interpreters import CachingInterpreter, Interpreter
from pyggp.records import Record

left: Final[Role] = Role(gdl.Subrelation(gdl.Relation("left")))
right: Final[Role] = Role(gdl.Subrelation(gdl.Relation("right")))

north: Final[gdl.Subrelation] = gdl.Subrelation(gdl.Relation("north"))
east: Final[gdl.Subrelation] = gdl.Subrelation(gdl.Relation("east"))
south: Final[gdl.Subrelation] = gdl.Subrelation(gdl.Relation("south"))
west: Final[gdl.Subrelation] = gdl.Subrelation(gdl.Relation("west"))

move_north: Final[Move] = Move(
    gdl.Subrelation(
        gdl.Relation(
            "move",
            (north,),
        ),
    ),
)
move_east: Final[Move] = Move(
    gdl.Subrelation(
        gdl.Relation(
            "move",
            (east,),
        ),
    ),
)
move_south: Final[Move] = Move(
    gdl.Subrelation(
        gdl.Relation(
            "move",
            (south,),
        ),
    ),
)
move_west: Final[Move] = Move(
    gdl.Subrelation(
        gdl.Relation(
            "move",
            (west,),
        ),
    ),
)

a1: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(1))))
)
a2: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(2))))
)
a3: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(3))))
)
a4: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(4))))
)

b1: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(1))))
)
b2: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(2))))
)
b3: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(3))))
)
b4: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(4))))
)

c1: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(1))))
)
c2: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(2))))
)
c3: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(3))))
)
c4: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(4))))
)

finish_line: Final[FrozenSet[gdl.Subrelation]] = frozenset((a4, b4, c4))

crossings: Final[FrozenSet[gdl.Subrelation]] = frozenset(
    (
        gdl.Subrelation(gdl.Relation(None, (a1, a2))),
        gdl.Subrelation(gdl.Relation(None, (a2, a3))),
        gdl.Subrelation(gdl.Relation(None, (a3, a4))),
        gdl.Subrelation(gdl.Relation(None, (b1, b2))),
        gdl.Subrelation(gdl.Relation(None, (b2, b3))),
        gdl.Subrelation(gdl.Relation(None, (b3, b4))),
        gdl.Subrelation(gdl.Relation(None, (c1, c2))),
        gdl.Subrelation(gdl.Relation(None, (c2, c3))),
        gdl.Subrelation(gdl.Relation(None, (c3, c4))),
        gdl.Subrelation(gdl.Relation(None, (a1, b1))),
        gdl.Subrelation(gdl.Relation(None, (b1, c1))),
        gdl.Subrelation(gdl.Relation(None, (a2, b2))),
        gdl.Subrelation(gdl.Relation(None, (b2, c2))),
        gdl.Subrelation(gdl.Relation(None, (a3, b3))),
        gdl.Subrelation(gdl.Relation(None, (b3, c3))),
        gdl.Subrelation(gdl.Relation(None, (a4, b4))),
        gdl.Subrelation(gdl.Relation(None, (b4, c4))),
    )
)
relevant_crossings: Final[FrozenSet[gdl.Subrelation]] = frozenset(
    (
        gdl.Subrelation(gdl.Relation(None, (a1, a2))),
        gdl.Subrelation(gdl.Relation(None, (a2, a3))),
        gdl.Subrelation(gdl.Relation(None, (a3, a4))),
        gdl.Subrelation(gdl.Relation(None, (b1, b2))),
        gdl.Subrelation(gdl.Relation(None, (b2, b3))),
        gdl.Subrelation(gdl.Relation(None, (b3, b4))),
        gdl.Subrelation(gdl.Relation(None, (c1, c2))),
        gdl.Subrelation(gdl.Relation(None, (c2, c3))),
        gdl.Subrelation(gdl.Relation(None, (c3, c4))),
        gdl.Subrelation(gdl.Relation(None, (a1, b1))),
        gdl.Subrelation(gdl.Relation(None, (b1, c1))),
        gdl.Subrelation(gdl.Relation(None, (a2, b2))),
        gdl.Subrelation(gdl.Relation(None, (b2, c2))),
        gdl.Subrelation(gdl.Relation(None, (a3, b3))),
        gdl.Subrelation(gdl.Relation(None, (b3, c3))),
    )
)


def at(role: gdl.Subrelation, pos: gdl.Subrelation) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("at", (role, pos)))


def control(role: gdl.Subrelation) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("control", (role,)))


def border(role: gdl.Subrelation, crossing: Tuple[gdl.Subrelation, gdl.Subrelation]) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("border", (role, gdl.Subrelation(gdl.Relation(None, crossing)))))


def _block(crossing: gdl.Subrelation) -> Move:
    return Move(gdl.Subrelation(gdl.Relation("block", (crossing,))))


def block(crossing: Tuple[gdl.Subrelation, gdl.Subrelation]) -> Move:
    return _block(gdl.Subrelation(gdl.Relation(None, crossing)))


def revealed(role: gdl.Subrelation, crossing: Tuple[gdl.Subrelation, gdl.Subrelation]) -> gdl.Subrelation:
    return gdl.Subrelation(gdl.Relation("revealed", (role, gdl.Subrelation(gdl.Relation(None, crossing)))))


ruleset_str: Final[
    str
] = """

role(left).
role(right).

succ(a, b). succ(b, c).
succ(1, 2). succ(2, 3). succ(3, 4).

col(a). col(b). col(c).
row(1). row(2). row(3). row(4).

startcol(b).

firstcol(C) :-
    col(C),
    not succ(_, C).
lastcol(C) :-
    col(C),
    not succ(C, _).
firstrow(R) :-
    row(R),
    not succ(_, R).
lastrow(R) :-
    row(R),
    not succ(R, _).

cell((C, R)) :-
    col(C), row(R).

finishcell((C, R)) :-
    col(C), lastrow(R).

direction(north). direction(east). direction(south). direction(west).

cell_direction_cell((C, R2), north, (C, R1)) :-
    cell((C, R2)), cell((C, R1)),
    col(C), row(R2), row(R1),
    succ(R1, R2).

cell_direction_cell((C1, R), east, (C2, R)) :-
    cell((C1, R)), cell((C2, R)),
    col(C1), row(R), col(C2),
    succ(C1, C2).

cell_direction_cell((C, R1), south, (C, R2)) :-
    cell((C, R1)), cell((C, R2)),
    col(C), row(R1), row(R2),
    succ(R1, R2).

cell_direction_cell((C2, R), west, (C1, R)) :-
    cell((C2, R)), cell((C1, R)),
    col(C2), row(R), col(C1),
    succ(C1, C2).

crossing((Cell1, Cell2)) :-
    cell(Cell1), cell(Cell2),
    cell_direction_cell(Cell1, south, Cell2).

crossing((Cell1, Cell2)) :-
    cell(Cell1), cell(Cell2),
    cell_direction_cell(Cell1, east, Cell2).

quadrant((Cell, Right, Bottom, Diag)) :-
    cell(Cell), cell(Right), cell(Bottom), cell(Diag),
    cell_direction_cell(Cell, east, Right),
    cell_direction_cell(Cell, south, Bottom),
    cell_direction_cell(Right, south, Diag),
    cell_direction_cell(Bottom, east, Diag).

blocked(Role, Cell1, Cell2) :-
    true(border(Role, (Cell1, Cell2))),
    role(Role), crossing((Cell1, Cell2)).
blocked(Role, Cell1, Cell2) :-
    role(Role), cell(Cell1), cell(Cell2),
    blocked(Role, Cell2, Cell1).

visiblyblocked(Role, Cell1, Cell2) :-
    true(revealed(Role, (Cell1, Cell2))),
    role(Role), crossing((Cell1, Cell2)).
visiblyblocked(Role, Cell1, Cell2) :-
    role(Role), cell(Cell1), cell(Cell2),
    visiblyblocked(Role, Cell2, Cell1).

unblockable(Role, (Cell1, Cell2)) :-
    role(Role), finishcell(Cell1), finishcell(Cell2),
    crossing((Cell1, Cell2)).
unblockable(Role, Crossing) :-
    role(Role), crossing(Crossing),
    true(border(Role, Crossing)).
unblockable(Role, Crossing) :-
    role(Role), crossing(Crossing),
    critical(Role, Crossing).

critical(Role, Crossing) :-
    role(Role), crossing(Crossing),
    finishcell(FinishCell),
    not reachable(Role, Crossing, FinishCell).

reachable(Role2, AssumedBorder, Cell) :-
    true(control(Role1)),
    true(at(Role2, Cell)),
    not true(border(Role2, AssumedBorder)),
    role(Role2), crossing(AssumedBorder), cell(Cell),
    role(Role1), distinct(Role1, Role2).

reachable(Role2, AssumedBorder, Cell) :-
    true(control(Role1)),
    not true(border(Role2, AssumedBorder)),
    not true(border(Role2, (Cell, AdjacentCell))),
    role(Role2), crossing(AssumedBorder), cell(Cell),
    role(Role1), distinct(Role1, Role2),
    crossing((Cell, AdjacentCell)), distinct((Cell, AdjacentCell), AssumedBorder),
    reachable(Role2, AssumedBorder, AdjacentCell).

reachable(Role2, AssumedBorder, Cell) :-
    true(control(Role1)),
    not true(border(Role2, AssumedBorder)),
    not true(border(Role2, (AdjacentCell, Cell))),
    role(Role2), crossing(AssumedBorder), cell(Cell),
    role(Role1), distinct(Role1, Role2),
    crossing((AdjacentCell, Cell)), distinct((AdjacentCell, Cell), AssumedBorder),
    reachable(Role2, AssumedBorder, AdjacentCell).

init(at(Role, (StartCol, FirstRow))) :- role(Role), startcol(StartCol), firstrow(FirstRow).
init(control(left)).

next(control(Role2)) :-
    true(control(Role1)),
    role(Role2), role(Role1),
    distinct(Role1, Role2).

next(at(Role2, Cell)) :-
    does(Role1, _Action),
    true(at(Role2, Cell)),
    role(Role2), cell(Cell),
    role(Role1), distinct(Role1, Role2).

next(at(Role, Cell)) :-
    does(Role, block(_Crossing)),
    true(at(Role, Cell)),
    role(Role), cell(Cell).

next(at(Role, Cell2)) :-
    does(Role, move(Direction)),
    true(at(Role, Cell1)),
    role(Role), cell(Cell1), cell(Cell2),
    cell_direction_cell(Cell1, Direction, Cell2),
    not blocked(Role, Cell1, Cell2).

next(at(Role, Cell1)) :-
    does(Role, move(Direction)),
    true(at(Role, Cell1)),
    role(Role), cell(Cell1), cell(Cell2),
    cell_direction_cell(Cell1, Direction, Cell2),
    blocked(Role, Cell1, Cell2).

next(revealed(Role, (Cell1, Cell2))) :-
    does(Role, move(Direction)),
    true(at(Role, Cell1)),
    true(border(Role, (Cell1, Cell2))),
    role(Role), crossing((Cell1, Cell2)),
    direction(Direction),
    cell_direction_cell(Cell1, Direction, Cell2).

next(revealed(Role, (Cell1, Cell2))) :-
    does(Role, move(Direction)),
    true(at(Role, Cell2)),
    true(border(Role, (Cell1, Cell2))),
    role(Role), crossing((Cell1, Cell2)),
    direction(Direction),
    cell_direction_cell(Cell2, Direction, Cell1).

next(revealed(Role, Crossing)) :-
    true(revealed(Role, Crossing)),
    role(Role), crossing(Crossing).

next(border(Role2, Crossing)) :-
    does(Role1, block(Crossing)),
    role(Role2), crossing(Crossing), role(Role1),
    distinct(Role1, Role2).

next(border(Role, Crossing)) :-
    true(border(Role, Crossing)),
    role(Role), crossing(Crossing).

sees(Everyone, control(Role)) :-
    true(control(Role)),
    role(Everyone), role(Role).

sees(Everyone, at(Role, Cell)) :-
    true(at(Role, Cell)),
    role(Everyone), role(Role), cell(Cell).

sees(Role, revealed(Role, Crossing)) :-
    true(revealed(Role, Crossing)),
    role(Role), crossing(Crossing).

sees(Role2, border(Role1, Crossing)) :-
    true(border(Role1, Crossing)),
    role(Role2), role(Role1), crossing(Crossing),
    distinct(Role1, Role2).

sees(Role, border(Role, Crossing)) :-
    true(border(Role, Crossing)),
    true(revealed(Role, Crossing)),
    role(Role), crossing(Crossing).

legal(Role, move(Direction)) :-
    true(at(Role, Cell1)),
    role(Role), direction(Direction),
    cell(Cell1), cell(Cell2),
    cell_direction_cell(Cell1, Direction, Cell2),
    not visiblyblocked(Role, Cell1, Cell2).

legal(Role2, block(Crossing)) :-
    not unblockable(Role1, Crossing),
    role(Role2), crossing(Crossing),
    role(Role1), distinct(Role1, Role2).

goal(Role1, 0) :-
    finished(Role2),
    not finished(Role1),
    role(Role1), role(Role2),
    distinct(Role1, Role2).

goal(Role1, 50) :-
    finished(Role1),
    finished(Role2),
    role(Role1), role(Role2),
    distinct(Role1, Role2).

goal(Role2, 100) :-
    finished(Role2),
    not finished(Role1),
    role(Role1), role(Role2),
    distinct(Role1, Role2).

finished(Role) :-
    true(at(Role, (_, LastRow))),
    role(Role), lastrow(LastRow).


terminal :- finished(_Role).
"""

ruleset: Final[gdl.Ruleset] = gdl.parse(ruleset_str)
ref_interpreter: Final[Interpreter] = ClingoInterpreter.from_ruleset(ruleset, disable_cache=True)

TRANSLATION: Final[Dict[Move, Tuple[int, int]]] = {
    move_north: (0, -1),
    move_east: (1, 0),
    move_south: (0, 1),
    move_west: (-1, 0),
}

OTHER: Final[Dict[Role, Role]] = {
    left: right,
    right: left,
}

NEXT_CELL: Final[Dict[gdl.Subrelation, Dict[Move, gdl.Subrelation]]] = {
    # First row: a1, b1, c1
    a1: {
        move_south: a2,
        move_east: b1,
    },
    b1: {
        move_south: b2,
        move_west: a1,
        move_east: c1,
    },
    c1: {
        move_south: c2,
        move_west: b1,
    },
    # Second row: a2, b2, c2
    a2: {
        move_south: a3,
        move_east: b2,
        move_north: a1,
    },
    b2: {
        move_south: b3,
        move_west: a2,
        move_east: c2,
        move_north: b1,
    },
    c2: {
        move_south: c3,
        move_west: b2,
        move_north: c1,
    },
    # Third row: a3, b3, c3
    a3: {
        move_south: a4,
        move_east: b3,
        move_north: a2,
    },
    b3: {move_south: b4, move_west: a3, move_east: c3, move_north: b2},
    c3: {
        move_south: c4,
        move_west: b3,
        move_north: c2,
    },
    # Fourth row: a4, b4, c4
    a4: {move_north: a3, move_east: b4},
    b4: {move_north: b3, move_west: a4, move_east: c4},
    c4: {move_north: c3, move_west: b4},
}

MOVE_TO_REACH: Final[Dict[gdl.Subrelation, Dict[gdl.Subrelation, Move]]] = {
    # First row: a1, b1, c1
    a1: {b1: move_east, a2: move_south},
    b1: {a1: move_west, c1: move_east, b2: move_south},
    c1: {b1: move_west, c2: move_south},
    # Second row: a2, b2, c2
    a2: {a1: move_north, b2: move_east, a3: move_south},
    b2: {b1: move_north, a2: move_west, c2: move_east, b3: move_south},
    c2: {c1: move_north, b2: move_west, c3: move_south},
    # Third row: a3, b3, c3
    a3: {a2: move_north, b3: move_east, a4: move_south},
    b3: {b2: move_north, a3: move_west, c3: move_east, b4: move_south},
    c3: {c2: move_north, b3: move_west, c4: move_south},
    # Fourth row: a4, b4, c4
    a4: {a3: move_north, b4: move_east},
    b4: {b3: move_north, a4: move_west, c4: move_east},
    c4: {c3: move_north, b4: move_west},
}


def is_crossing(cell: gdl.Subrelation, neighbor: gdl.Subrelation, crossing: gdl.Subrelation) -> bool:
    return cell in crossing.symbol.arguments and neighbor in crossing.symbol.arguments


def _get_legal_moves_by_role_parse_current(current, role):
    pos: Optional[gdl.Subrelation] = None
    other_pos: Optional[gdl.Subrelation] = None
    in_control: bool | None = None
    blocked_crossings_role: Set[gdl.Subrelation] = set()
    blocked_crossings_other: Set[gdl.Subrelation] = set()
    for subrelation in current:
        if subrelation.symbol.name == "border":
            if subrelation.symbol.arguments[0] != role:
                blocked_crossings_other.add(subrelation.symbol.arguments[1])
            continue
        if subrelation.symbol.name == "revealed":
            if subrelation.symbol.arguments[0] == role:
                blocked_crossings_role.add(subrelation.symbol.arguments[1])
            continue
        if subrelation.symbol.name == "control":
            in_control = subrelation.symbol.arguments[0] == role
            continue
        if pos is not None and other_pos is not None and in_control is not None:
            continue
        if subrelation.symbol.name != "at":
            continue
        coords = subrelation.symbol.arguments[1]
        if subrelation.symbol.arguments[0] == role:
            pos = coords
        else:
            other_pos = coords
    assert pos is not None
    assert other_pos is not None
    assert in_control is not None
    return blocked_crossings_other, blocked_crossings_role, in_control, other_pos, pos


def _get_legal_moves_by_role_find_moves(blocked_crossings_role, legal_moves, pos):
    legal_moves.update(NEXT_CELL[pos])
    for crossing in blocked_crossings_role:
        if pos in crossing.symbol.arguments:
            next_pos_rank: int = 1
            if crossing.symbol.arguments[next_pos_rank] == pos:
                next_pos_rank = 0
            next_pos = crossing.symbol.arguments[next_pos_rank]
            assert pos != next_pos
            legal_moves.remove(MOVE_TO_REACH[pos][next_pos])
    assert legal_moves


def _get_legal_moves_by_role_find_blocks(blocked_crossings_other, in_control, legal_moves, other_pos):
    blockable_crossings: Set[gdl.Subrelation] = set()
    if in_control:
        blockable_crossings = set(
            crossing for crossing in relevant_crossings if crossing not in blocked_crossings_other
        )

        critical_crossings: Set[gdl.Subrelation] = set()
        for crossing in blockable_crossings:
            positions: Deque[gdl.Subrelation] = deque((other_pos,))
            visited: Set[gdl.Subrelation] = set()
            reached_finish_line: bool = False
            while positions and not reached_finish_line:
                position: gdl.Subrelation = positions.pop()
                visited.add(position)
                for next_position in MOVE_TO_REACH[position].keys():
                    if next_position in visited:
                        continue
                    if is_crossing(position, next_position, crossing) or any(
                        is_crossing(position, next_position, c) for c in blocked_crossings_other
                    ):
                        continue
                    if next_position in finish_line:
                        reached_finish_line = True
                    positions.append(next_position)
            if not reached_finish_line:
                critical_crossings.add(crossing)

        blockable_crossings.difference_update(critical_crossings)
    legal_moves.update(_block(crossing) for crossing in blockable_crossings)


@dataclass
class DarkSplitCorridor34Interpreter(CachingInterpreter):

    @property
    def has_incomplete_information(self) -> bool:
        return True

    def _get_roles(self) -> FrozenSet[Role]:
        return frozenset((left, right))

    def _get_init_state(self) -> State:
        return State(frozenset((at(left, b1), at(right, b1), control(left))))

    def _get_next_state(self, current: Union[State, View], turn: Mapping[Role, Move]) -> State:
        role: Role = left
        if role not in turn:
            role = right
        move: Move = turn[role]
        if move in (move_north, move_east, move_south, move_west):
            return self._get_next_state_move(current, role, move)

        return self._get_next_state_block(current, role, move)

    @staticmethod
    def _get_next_state_move(current: Union[State, View], role: Role, move: Move) -> State:
        assert move in (move_north, move_east, move_south, move_west)
        nstate: Set[gdl.Subrelation] = set(current)

        nstate.remove(control(role))
        nstate.add(control(OTHER[role]))

        pos, x, y = DarkSplitCorridor34Interpreter.__get_next_state_move_find_pos(current, nstate, role)
        npos = DarkSplitCorridor34Interpreter.__get_next_state_move_calculate_npos(
            current, move, nstate, pos, role, x, y
        )
        nstate.add(at(role, npos))
        return State(frozenset(nstate))

    @staticmethod
    def __get_next_state_move_calculate_npos(current, move, nstate, pos, role, x, y):
        xd, yd = TRANSLATION[move]
        pos_rank: int = 0
        npos_rank: int = 1
        if xd + yd < 0:
            pos_rank = 1
            npos_rank = 0
        nx: int = x + xd
        ny: int = y + yd
        npos: gdl.Subrelation = gdl.Subrelation(
            gdl.Relation(None, (gdl.Subrelation(gdl.Relation(chr(ord("a") - 1 + nx))), gdl.Subrelation(gdl.Number(ny))))
        )
        crossing: Optional[gdl.Subrelation] = None
        has_border: bool = False
        for subrelation in current:
            if subrelation.symbol.name != "border":
                continue
            if subrelation.symbol.arguments[0] != role:
                continue
            if subrelation.symbol.arguments[1].symbol.arguments[pos_rank] != pos:
                continue
            if subrelation.symbol.arguments[1].symbol.arguments[npos_rank] != npos:
                continue
            has_border = True
            crossing = subrelation.symbol.arguments[1]
        if has_border:
            assert crossing is not None
            npos = pos
            nstate.add(revealed(role, crossing.symbol.arguments))
        return npos

    @staticmethod
    def __get_next_state_move_find_pos(current, nstate, role):
        x: int = 0
        y: int = 0
        pos: Optional[gdl.Subrelation] = None
        for subrelation in current:

            if subrelation.symbol.name != "at":
                continue
            if subrelation.symbol.arguments[0] != role:
                continue
            nstate.remove(subrelation)
            pos = subrelation.symbol.arguments[1]
            x = ord(pos.symbol.arguments[0].symbol.name) - (ord("a") - 1)
            y = pos.symbol.arguments[1].symbol.number
        return pos, x, y

    @staticmethod
    def _get_next_state_block(current: Union[State, View], role: Role, move: Move) -> State:
        nstate: Set[gdl.Subrelation] = set(current)
        nstate.remove(control(role))
        nstate.add(control(OTHER[role]))

        crossing: gdl.Subrelation = move.symbol.arguments[0]
        nstate.add(border(OTHER[role], crossing.symbol.arguments))
        return State(frozenset(nstate))

    def _get_sees(self, current: Union[State, View]) -> Mapping[Role, View]:
        return ref_interpreter.get_sees(current)

    def _get_legal_moves_by_role(self, current: Union[State, View], role: Role) -> FrozenSet[Move]:
        legal_moves: Set[Move] = set()

        blocked_crossings_other, blocked_crossings_role, in_control, other_pos, pos = (
            _get_legal_moves_by_role_parse_current(current, role)
        )

        _get_legal_moves_by_role_find_moves(blocked_crossings_role, legal_moves, pos)

        _get_legal_moves_by_role_find_blocks(blocked_crossings_other, in_control, legal_moves, other_pos)
        assert all(ref_interpreter.is_legal(current, role, move) for move in legal_moves)
        return frozenset(legal_moves)

    def _get_goals(self, current: Union[State, View]) -> Mapping[Role, Optional[int]]:
        return ref_interpreter.get_goals(current)

    def _is_terminal(self, current: Union[State, View]) -> bool:
        found_ats = 0
        for subrelation in current:
            if subrelation.symbol.name == "at":
                if subrelation.symbol.arguments[1] in finish_line:
                    assert ref_interpreter.is_terminal(current)
                    return True
                found_ats += 1
                if found_ats >= 2:
                    break
        assert not ref_interpreter.is_terminal(current)
        return False

    def get_developments(
        self, record: Record, *, last_ply_is_final_state: Optional[bool] = None
    ) -> Iterator[Development]:
        return ref_interpreter.get_developments(record, last_ply_is_final_state=last_ply_is_final_state)
