from enum import IntEnum
from typing import NamedTuple, Protocol, Self
from unittest import case

import pyggp.game_description_language as gdl
import pyggp.interpreters.dark_split_corridor34.constants as constants
import pyggp.interpreters.dark_split_corridor34.coordinates2d
import pyggp.interpreters.dark_split_corridor34.coordinates2d as coordinates
from pyggp.engine_primitives import Move
from pyggp.interpreters.dark_split_corridor34.coordinates2d import Coordinates2D


class Action(Protocol):

    @classmethod
    def from_move(cls, move: Move) -> Self: ...

    def into_subrelation(self) -> Move: ...


class MoveAction(IntEnum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    @classmethod
    def from_move(cls, move: Move) -> Self:
        assert move.matches_signature("move", 1)
        if move.symbol.arguments[0].symbol.name == "north":
            return cls.NORTH
        elif move.symbol.arguments[0].symbol.name == "east":
            return cls.EAST
        elif move.symbol.arguments[0].symbol.name == "south":
            return cls.SOUTH
        else:
            assert move.symbol.arguments[0].symbol.name == "west", f"Unknown move: {move}"
            return cls.WEST

    def into_coordinates(self) -> coordinates.Coordinates2D:
        if self is MoveAction.NORTH:
            return coordinates.Coordinates2D(0, -1)
        elif self is MoveAction.EAST:
            return coordinates.Coordinates2D(1, 0)
        elif self is MoveAction.SOUTH:
            return coordinates.Coordinates2D(0, 1)
        else:
            assert self is MoveAction.WEST
            return coordinates.Coordinates2D(-1, 0)

    def into_subrelation(self) -> Move:
        if self is MoveAction.NORTH:
            return Move(gdl.Subrelation(gdl.Relation("move", (constants.north,))))
        elif self is MoveAction.EAST:
            return Move(gdl.Subrelation(gdl.Relation("move", (constants.east,))))
        elif self is MoveAction.SOUTH:
            return Move(gdl.Subrelation(gdl.Relation("move", (constants.south,))))
        elif self is MoveAction.WEST:
            return Move(gdl.Subrelation(gdl.Relation("move", (constants.west,))))


class BlockAction(NamedTuple):
    crossing: coordinates.Coordinates2D

    @classmethod
    def from_move(cls, move: Move) -> Self:
        assert move.matches_signature("block", 1)
        crossing_subrelation = move.symbol.arguments[0]
        crossing = Coordinates2D.from_subrelation(crossing_subrelation)
        return cls(crossing)

    def into_subrelation(self) -> Move:
        return Move(gdl.Subrelation(gdl.Relation("block", (self.crossing.into_subrelation(),))))
