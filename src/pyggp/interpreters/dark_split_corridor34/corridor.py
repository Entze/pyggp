import dataclasses
import math
from collections import deque
from dataclasses import dataclass
from enum import IntEnum
from typing import Deque, Iterable, Mapping, MutableMapping, MutableSequence, NamedTuple, Self, Set, Tuple

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
            yield from self._move_actions()
        elif role != mover and mover == in_control:
            yield from self._block_actions()

    def _move_actions(self) -> Iterable[MoveAction]:
        southern_border = self.pawn_position + (MoveAction.SOUTH.into_coordinates() / 2)
        if southern_border not in self.borders or self.borders[southern_border] is not Border.REVEALED:
            yield MoveAction.SOUTH
        if self.pawn_position.x > 0:
            western_border = self.pawn_position + (MoveAction.WEST.into_coordinates() / 2)
            if western_border not in self.borders or self.borders[western_border] is not Border.REVEALED:
                yield MoveAction.WEST
        if self.pawn_position.x < 2:
            eastern_border = self.pawn_position + (MoveAction.EAST.into_coordinates() / 2)
            if eastern_border not in self.borders or self.borders[eastern_border] is not Border.REVEALED:
                yield MoveAction.EAST
        if self.pawn_position.y > 0:
            northern_border = self.pawn_position + (MoveAction.NORTH.into_coordinates() / 2)
            if northern_border not in self.borders or self.borders[northern_border] is not Border.REVEALED:
                yield MoveAction.NORTH

    def _block_actions(self) -> Iterable[BlockAction]:
        graph: MutableMapping[Coordinates2D, Set[Coordinates2D]] = {
            Coordinates2D(0, 3): {Coordinates2D(1, 3)},
            Coordinates2D(1, 3): {Coordinates2D(0, 3), Coordinates2D(2, 3)},
            Coordinates2D(2, 3): {Coordinates2D(1, 3)},
        }
        node_to_parent: MutableMapping[Coordinates2D, Coordinates2D] = {}
        queue: Deque[Coordinates2D] = deque(maxlen=10)
        queue.append(self.pawn_position)

        # BFS to build DAG
        while queue:
            position: Coordinates2D = queue.popleft()
            if position in graph:
                continue
            graph[position] = set()
            for translate in (Coordinates2D(0, 1), Coordinates2D(1, 0), Coordinates2D(-1, 0), Coordinates2D(0, -1)):
                crossing = position + (translate / 2)
                if crossing not in self.borders:
                    continue
                if self.borders[crossing] is not Border.OPEN:
                    continue
                next_position: Coordinates2D = position + translate
                graph[position].add(next_position)
                if next_position not in node_to_parent:
                    node_to_parent[next_position] = position
                if next_position in graph:
                    continue
                queue.append(next_position)

        path: Deque[Coordinates2D] = deque(maxlen=10)
        for target in (Coordinates2D(0, 3), Coordinates2D(1, 3), Coordinates2D(2, 3)):  # FIXME: Infinite loop
            if target not in node_to_parent:
                continue
            node = target
            while node != self.pawn_position:
                path.appendleft(node)
                node = node_to_parent[node]
            break
        path.appendleft(self.pawn_position)
        path_len: int = len(path)
        assert path_len > 1
        assert all(position in graph for position in path)

        potentially_blockable_crossings: Set[Coordinates2D] = {
            crossing for crossing in self.borders if self.borders[crossing] is Border.OPEN
        }

        # invert path, and note potential bridges
        potential_bridges: Set[Coordinates2D] = set()
        for i in range(path_len - 1, 0, -1):
            u: Coordinates2D = path[i]
            v: Coordinates2D = path[i - 1]
            assert v in graph
            assert u in graph
            assert u in graph[v]
            graph[u].add(v)
            graph[v].remove(u)
            potential_bridges.add(Coordinates2D(0.5 * abs(u.x + v.x), 0.5 * abs(u.y + v.y)))

        blockable_crossings: Set[Coordinates2D] = {
            crossing for crossing in potentially_blockable_crossings if crossing not in potential_bridges
        }
        yield from (BlockAction(crossing) for crossing in blockable_crossings)
        potentially_blockable_crossings.difference_update(blockable_crossings)

        # DFS to find s,t bridges
        stack: Deque[Coordinates2D] = deque(maxlen=10)
        stack.append(self.pawn_position)
        bridge_start: Coordinates2D = path.popleft()
        component: Set[Coordinates2D] = set()

        while path and potentially_blockable_crossings:
            while stack:
                position: Coordinates2D = stack.pop()
                component.add(position)
                for neighbor in graph[position]:
                    if neighbor in component:
                        continue
                    if neighbor not in graph:
                        continue
                    stack.append(neighbor)

            assert bridge_start in component
            bridge_end: Coordinates2D = path.popleft()
            while path and bridge_end in component:
                bridge_start = bridge_end
                bridge_end = path.popleft()
                assert bridge_start in component
            if not path and bridge_end in component:
                break

            assert bridge_start in component
            assert bridge_end not in component

            bridge = Coordinates2D(0.5 * abs(bridge_start.x + bridge_end.x), 0.5 * abs(bridge_start.y + bridge_end.y))

            if bridge in potentially_blockable_crossings:
                potentially_blockable_crossings.remove(bridge)

            stack.append(bridge_end)
            for node in component:
                graph.pop(node)
            bridge_start = bridge_end
            component.clear()

        yield from (BlockAction(crossing) for crossing in potentially_blockable_crossings)
