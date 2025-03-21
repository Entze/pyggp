import dataclasses
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Mapping, MutableMapping, NamedTuple, Self

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Role, State
from pyggp.interpreters.dark_split_corridor34.actions import Action, BlockAction, MoveAction
from pyggp.interpreters.dark_split_corridor34.coordinates2d import Coordinates2D


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


@dataclass(frozen=False)
class Corridor:
    pawn_position: Coordinates2D = Coordinates2D(1, 0)
    borders: MutableMapping[Coordinates2D, Border] = dataclasses.field(default_factory=_default_borders)

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

    def apply_action(self, action: Action) -> None:
        if isinstance(action, MoveAction):
            return self._apply_move_action(action)
        assert isinstance(action, BlockAction)
        return self._apply_block_action(action)

    def _apply_move_action(self, action: MoveAction) -> None:
        translation = action.into_coordinates()
        crossing = self.pawn_position + (translation / 2)
        if self.borders[crossing] is Border.OPEN:
            self.pawn_position = self.pawn_position + translation
        else:
            self.borders[crossing] = Border.REVEALED

    def _apply_block_action(self, action: BlockAction) -> None:
        self.borders[action.crossing] = Border.BLOCKED

    def into_subrelations(self, role: Role) -> Iterable[gdl.Subrelation]:
        yield gdl.Subrelation(gdl.Relation("at", (role, self.pawn_position.into_subrelation())))
        for position, border in self.borders.items():
            yield from border.into_subrelations(role, position)

    def into_view_subrelations(self, role: Role, observer: Role) -> Iterable[gdl.Subrelation]:
        yield gdl.Subrelation(gdl.Relation("at", (role, self.pawn_position.into_subrelation())))
        for position, border in self.borders.items():
            if border is Border.REVEALED and role == observer:
                yield from border.into_subrelations(role, position)
            elif border is not Border.OPEN and role != observer:
                yield from Border.BLOCKED.into_subrelations(role, position)

    def actions(self, role: Role, in_control: Role, mover: Role) -> Iterable[MoveAction | BlockAction]:
        if role == mover:
            northern_border = self.pawn_position + (MoveAction.NORTH.into_coordinates() / 2)
            eastern_border = self.pawn_position + (MoveAction.EAST.into_coordinates() / 2)
            southern_border = self.pawn_position + (MoveAction.SOUTH.into_coordinates() / 2)
            western_border = self.pawn_position + (MoveAction.WEST.into_coordinates() / 2)

            if southern_border not in self.borders or self.borders[southern_border] is not Border.REVEALED:
                yield MoveAction.SOUTH
            if self.pawn_position.x > 0 and (
                western_border not in self.borders or self.borders[western_border] is not Border.REVEALED
            ):
                yield MoveAction.WEST
            if self.pawn_position.x < 2 and (
                eastern_border not in self.borders or self.borders[eastern_border] is not Border.REVEALED
            ):
                yield MoveAction.EAST
            if self.pawn_position.y > 0 and (
                northern_border not in self.borders or self.borders[northern_border] is not Border.REVEALED
            ):
                yield MoveAction.NORTH
        elif role != mover and mover == in_control:
            for position, border in self.borders.items():
                if border is Border.OPEN:
                    yield BlockAction(position)
