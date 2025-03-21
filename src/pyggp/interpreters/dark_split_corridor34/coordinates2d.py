import math
from typing import NamedTuple, Self

from pyggp import game_description_language as gdl


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

    def __truediv__(self, other: float) -> Self:
        return Coordinates2D(self.x / other, self.y / other)

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
