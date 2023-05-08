import abc
from dataclasses import dataclass, field
from typing import FrozenSet, Iterator, Mapping, Protocol, Sequence, Union

import clingo
from clingo import ast as clingo_ast

from pyggp import _clingo as clingo_helper
from pyggp.engine_primitives import Move, Role, State, Turn, View


class Record(Protocol):
    @property
    @abc.abstractmethod
    def horizon(self) -> int:
        """Maximum ply associated with either states, views or turns."""

    def get_state_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the states of the game.

        Yields:
            Clingo assertions for the states of the game

        """

    def get_view_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the views of the game.

        Yields:
            Clingo assertions for the views of the game

        """

    def get_turn_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the turns of the game.

        Yields:
            Clingo assertions for the turns of the game

        """


def get_assertions_from_state(
    current: Union[State, View],
    name: str = "true",
    pre_arguments: Sequence[clingo_ast.AST] = (),
    post_arguments: Sequence[clingo_ast.AST] = (),
) -> Iterator[clingo_ast.AST]:
    """Get the clingo assertions for the given state.

    Args:
        current: State or view
        name: Name of the relation
        pre_arguments: Arguments before the subrelation
        post_arguments: Arguments after the subrelation

    Returns:
        Iterator of clingo assertions

    """
    return (
        clingo_helper.create_rule(
            body=(
                clingo_helper.create_literal(
                    sign=clingo_ast.Sign.Negation,
                    atom=clingo_helper.create_atom(
                        clingo_helper.create_function(
                            name=name,
                            arguments=(
                                *pre_arguments,
                                subrelation.as_clingo_ast(),
                                *post_arguments,
                            ),
                        ),
                    ),
                ),
            ),
        )
        for subrelation in current
    )


@dataclass(frozen=True)
class PerfectInformationRecord(Record):
    """Record (possibly partial) of a game."""

    states: Mapping[int, State] = field(default_factory=dict)
    """States of the game by ply."""
    views: Mapping[int, Mapping[Role, View]] = field(default_factory=dict)
    """Views of the state by role by ply."""
    turns: Mapping[int, Turn] = field(default_factory=dict)
    """Turns of the game by ply."""

    @property
    def horizon(self) -> int:
        """Maximum ply associated with either states, views or turns."""
        return max(
            max(self.states.keys(), default=0),
            max(self.views.keys(), default=0),
            max(self.turns.keys(), default=0),
        )

    def get_state_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the states of the game.

        Yields:
            Clingo assertions for the states of the game

        """
        for ply, state in self.states.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            yield from get_assertions_from_state(
                state,
                name="holds_at",
                post_arguments=(current_time,),
            )

    def get_view_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the views of the game.

        Yields:
            Clingo assertions for the views of the game

        """
        for ply, views in self.views.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            for role, view in views.items():
                role_ast = role.as_clingo_ast()
                yield from get_assertions_from_state(
                    view,
                    name="sees_at",
                    pre_arguments=(role_ast,),
                    post_arguments=(current_time,),
                )

    def get_turn_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the turns of the game.

        Yields:
            Clingo assertions for the turns of the game

        """
        for ply, turn in self.turns.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            yield from turn.get_assertions(current_time)


@dataclass(frozen=True)
class ImperfectInformationRecord(Record):
    possible_states: Mapping[int, FrozenSet[State]] = field(default_factory=dict)
    """Possible states of the game by ply."""

    views: Mapping[int, Mapping[Role, View]] = field(default_factory=dict)
    """Views of the state by role by ply."""

    possible_turns: Mapping[int, FrozenSet[Turn]] = field(default_factory=dict)
    """Possible turns of the game by ply."""

    role_move_map: Mapping[int, Mapping[Role, Move]] = field(default_factory=dict)

    @property
    def horizon(self) -> int:
        """Maximum ply associated with either states, views or turns."""
        return max(
            max(self.possible_states.keys(), default=0),
            max(self.views.keys(), default=0),
            max(self.possible_turns.keys(), default=0),
        )

    def get_state_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the states of the game.

        Yields:
            Clingo assertions for the states of the game

        """
        for ply, states in self.possible_states.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            common = State(frozenset.intersection(*states))
            yield from get_assertions_from_state(
                common,
                name="holds_at",
                post_arguments=(current_time,),
            )

    def get_view_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the views of the game.

        Yields:
            Clingo assertions for the views of the game

        """
        for ply, views in self.views.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            for role, view in views.items():
                role_ast = role.as_clingo_ast()
                yield from get_assertions_from_state(
                    view,
                    name="sees_at",
                    pre_arguments=(role_ast,),
                    post_arguments=(current_time,),
                )

    def get_turn_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the turns of the game.

        Yields:
            Clingo assertions for the turns of the game

        """
        for ply, turns in self.possible_turns.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))

            first_turn = next(iter(turns))
            common_pairs = set(first_turn.items())
            for turn in turns:
                common_pairs.intersection_update(turn.items())
            common = Turn(common_pairs)
            yield from common.get_assertions(current_time)

        for ply, role_move_map in self.role_move_map.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            turn = Turn(role_move_map.items())
            yield from turn.get_assertions(current_time)
