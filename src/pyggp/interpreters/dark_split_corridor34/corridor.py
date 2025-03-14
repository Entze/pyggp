import dataclasses
import math
from collections import namedtuple
from dataclasses import dataclass
from enum import IntEnum
from typing import Final, Iterable, Mapping, MutableMapping, NamedTuple, Self

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Role, State

left: Final[Role] = Role(gdl.Subrelation(gdl.Relation("left")))
right: Final[Role] = Role(gdl.Subrelation(gdl.Relation("right")))

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


class Coordinates2D(NamedTuple):
    x: float = 0
    y: float = 0

    @classmethod
    def from_subrelation(cls, subrelation: gdl.Subrelation) -> Self:
        assert subrelation.matches_signature(None, arity=2)
        tuple_ = subrelation.symbol.arguments
        xo = 0
        yo = 0
        if tuple_[0].is_relation and tuple_[1].is_relation:
            if tuple_[0].symbol.arguments[0] == tuple_[1].symbol.arguments[0]:
                yo = 0.5
            else:
                xo = 0.5
            tuple_ = tuple_[0].symbol.arguments

        assert tuple_[0].is_relation
        assert tuple_[1].is_number
        assert isinstance(tuple_[1].symbol, gdl.Number)
        xc: str = tuple_[0].symbol.name
        yc: int = tuple_[1].symbol.number
        return cls(x=ord(xc) - ord("a") + xo, y=yc - 1 + yo)

    def __add__(self, other: Self) -> Self:
        return Coordinates2D(self.x + other.x, self.y + other.y)

    def into_subrelation(self) -> gdl.Subrelation:
        x: int = math.floor(self.x)
        y: int = math.floor(self.y)
        if self.x.is_integer() and self.y.is_integer():
            return Coordinates2D.subrelation_from_x_y(x, y)
        xn: int = math.ceil(self.x)
        yn: int = math.ceil(self.y)
        return gdl.Subrelation(
            gdl.Relation(None, (Coordinates2D.subrelation_from_x_y(x, y), Coordinates2D.subrelation_from_x_y(xn, yn)))
        )

    @staticmethod
    def subrelation_from_x_y(x: int, y: int) -> gdl.Subrelation:
        return gdl.Subrelation(
            gdl.Relation(None, (gdl.Subrelation(gdl.Relation(chr(ord("a") + x))), gdl.Subrelation(gdl.Number(y + 1))))
        )


class Border(IntEnum):
    OPEN = 0
    BLOCKED = 1
    REVEALED = 2

    def into_subrelations(self, role: Role, coordinates: Coordinates2D) -> Iterable[gdl.Subrelation]:
        if self == Border.OPEN:
            return
        coordinates_subrelation = coordinates.into_subrelation()
        yield gdl.Subrelation(gdl.Relation("border", (role, coordinates_subrelation)))
        if self == Border.REVEALED:
            yield gdl.Subrelation(gdl.Relation("revealed", (role, coordinates_subrelation)))


def _default_borders() -> MutableMapping[Coordinates2D, Border]:
    return {
        Coordinates2D(x, y): Border.OPEN
        for x, y in (
            (0.5, 0),
            (1.5, 0),
            (0, 0.5),
            (1, 0.5),
            (2, 0.5),
            (0.5, 1),
            (1.5, 1),
            (0, 1.5),
            (1, 1.5),
            (2, 1.5),
            (0.5, 2),
            (1.5, 2),
            (0, 2.5),
            (1, 2.5),
            (2, 2.5),
        )
    }


class Corridor(NamedTuple):
    pawn_position: Coordinates2D = Coordinates2D(1, 0)
    borders: Mapping[Coordinates2D, Border] = _default_borders()

    @classmethod
    def from_state(cls, state: State, role: Role) -> Self:
        pawn_position: Coordinates2D | None = None
        borders: MutableMapping[Coordinates2D, Border] = _default_borders()
        for subrelation in state:
            if subrelation.matches_signature(name="at", arity=2):
                symbol = subrelation.symbol
                assert isinstance(symbol, gdl.Relation)
                assert len(symbol.arguments) == 2
                if role != symbol.arguments[0]:
                    continue
                pawn_position = Coordinates2D.from_subrelation(symbol.arguments[1])
            elif subrelation.matches_signature(name="revealed", arity=2) or subrelation.matches_signature(
                name="border", arity=2
            ):
                symbol = subrelation.symbol
                assert isinstance(symbol, gdl.Relation)
                assert len(symbol.arguments) == 2
                if role != symbol.arguments[0]:
                    continue
                coordinates_subrelation = symbol.arguments[1]
                coordinates = Coordinates2D.from_subrelation(coordinates_subrelation)
                if subrelation.matches_signature(name="revealed", arity=2):
                    borders[coordinates] = Border.REVEALED
                elif borders[coordinates] == Border.OPEN:
                    borders[coordinates] = Border.BLOCKED

        assert pawn_position is not None
        return Corridor(pawn_position, borders)

    def into_subrelations(self, role: Role) -> Iterable[gdl.Subrelation]:
        yield gdl.Subrelation(gdl.Relation("at", (role, self.pawn_position.into_subrelation())))
        for position, border in self.borders.items():
            yield from border.into_subrelations(role, position)
