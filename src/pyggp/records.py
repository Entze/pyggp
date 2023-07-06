import abc
from dataclasses import dataclass, field
from typing import FrozenSet, Iterable, Iterator, Mapping, Protocol, Sequence, Union

import clingo
from clingo import ast as clingo_ast

from pyggp import _clingo as clingo_helper
from pyggp.engine_primitives import (
    Move,
    Role,
    SeesShape,
    State,
    StateShape,
    Turn,
    View,
    invert_sees,
    invert_state,
)


class Record(Protocol):
    @property
    @abc.abstractmethod
    def offset(self) -> int:
        """Earliest ply of the record."""

    @property
    @abc.abstractmethod
    def horizon(self) -> int:
        """Maximum ply associated with either states, views or turns."""

    def get_state_assertions(self, state_shape: StateShape) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the states of the game.

        Args:
            state_shape: Shape of state

        Yields:
            Clingo assertions for the states of the game

        """

    def get_view_assertions(self, sees_shape: SeesShape) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the views of the game.

        Args:
            sees_shape: Shape of view

        Yields:
            Clingo assertions for the views of the game

        """

    def get_turn_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the turns of the game.

        Yields:
            Clingo assertions for the turns of the game

        """

    def get_incidental_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the incidental facts of the game.

        Yields:
            Clingo assertions for the incidental facts of the game

        """


def get_as_facts(
    current: Union[State, View],
    name: str = "true",
    pre_arguments: Sequence[clingo_ast.AST] = (),
    post_arguments: Sequence[clingo_ast.AST] = (),
) -> Iterator[clingo_ast.AST]:
    symbols = (
        clingo_helper.create_function(name=name, arguments=(*pre_arguments, elem.as_clingo_ast(), *post_arguments))
        for elem in current
    )
    atoms = (clingo_helper.create_atom(symbol=symbol) for symbol in symbols)
    literals = (clingo_helper.create_literal(atom=atom) for atom in atoms)
    facts = (clingo_helper.create_rule(head=literal) for literal in literals)
    yield from facts


def get_as_assertions(
    current: Union[State, View, Iterable[Move]],
    name: str = "true",
    pre_arguments: Sequence[clingo_ast.AST] = (),
    post_arguments: Sequence[clingo_ast.AST] = (),
    *,
    exclude: bool = False,
) -> Iterator[clingo_ast.AST]:
    """Get the clingo assertions for the given state.

    Args:
        current: State or view or moves
        name: Name of the relation
        pre_arguments: Arguments before the subrelation
        post_arguments: Arguments after the subrelation
        exclude: Whether to exclude current

    Yields:
        clingo assertions

    """
    symbols = (
        clingo_helper.create_function(name=name, arguments=(*pre_arguments, elem.as_clingo_ast(), *post_arguments))
        for elem in current
    )
    atoms = (clingo_helper.create_atom(symbol=symbol) for symbol in symbols)
    sign = clingo_ast.Sign.Negation if not exclude else clingo_ast.Sign.NoSign
    literals = (clingo_helper.create_literal(atom=atom, sign=sign) for atom in atoms)
    assertions = (clingo_helper.create_rule(body=(literal,)) for literal in literals)
    yield from assertions


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
    def offset(self) -> int:
        return min(self.states.keys(), default=0)

    @property
    def horizon(self) -> int:
        """Maximum ply associated with either states, views or turns."""
        return max(
            max(self.states.keys(), default=0),
            max(self.views.keys(), default=0),
            max(self.turns.keys(), default=0),
        )

    def get_state_assertions(self, state_shape: StateShape) -> Iterator[clingo_ast.AST]:
        if self.offset > 0:
            current_time = clingo_helper.create_symbolic_term(clingo.Number(self.offset))
            state = self.states[self.offset]
            yield from get_as_facts(state, name="holds_at", post_arguments=(current_time,))

        for ply, state in self.states.items():
            if ply == 0:
                continue
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            yield from get_as_assertions(
                state,
                name="holds_at",
                post_arguments=(current_time,),
            )
            inverted_state = invert_state(state_shape, state)
            yield from get_as_assertions(
                inverted_state,
                name="holds_at",
                post_arguments=(current_time,),
                exclude=True,
            )

    def get_view_assertions(self, sees_shape: SeesShape) -> Iterator[clingo_ast.AST]:
        for ply, views in self.views.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            for role, view in views.items():
                role_ast = role.as_clingo_ast()
                yield from get_as_assertions(
                    view,
                    name="sees_at",
                    pre_arguments=(role_ast,),
                    post_arguments=(current_time,),
                )
                inverted_view = invert_sees(sees_shape, role, view)
                yield from get_as_assertions(
                    inverted_view,
                    name="sees_at",
                    pre_arguments=(role_ast,),
                    post_arguments=(current_time,),
                    exclude=True,
                )

    def get_turn_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the turns of the game.

        Yields:
            Clingo assertions for the turns of the game

        """
        for ply, turn in self.turns.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            for role, move in turn.items():
                role_ast = role.as_clingo_ast()
                yield from get_as_assertions(
                    (move,),
                    name="does_at",
                    pre_arguments=(role_ast,),
                    post_arguments=(current_time,),
                )

    def get_incidental_assertions(self) -> Iterator[clingo_ast.AST]:
        plies = range(self.offset, self.horizon)
        current_times = (clingo_helper.create_symbolic_term(clingo.Number(ply)) for ply in plies)
        terminal_at_functions = (
            clingo_helper.create_function(name="terminal_at", arguments=(current_time,))
            for current_time in current_times
        )
        terminal_at_atoms = (
            clingo_helper.create_atom(symbol=terminal_at_function) for terminal_at_function in terminal_at_functions
        )
        terminal_at_literals = (
            clingo_helper.create_literal(atom=terminal_at_atom) for terminal_at_atom in terminal_at_atoms
        )
        terminal_at_rules = (
            clingo_helper.create_rule(body=(terminal_at_literal,)) for terminal_at_literal in terminal_at_literals
        )
        yield from terminal_at_rules


def _get_indirect_state_assertions(
    ply: int,
    possible_states: Iterable[State],
    state_shape: StateShape,
) -> Iterator[clingo_ast.AST]:
    state_literals = []
    ply_number = clingo_helper.create_symbolic_term(clingo.Number(ply))
    for n, state in enumerate(possible_states):
        state_number = clingo_helper.create_symbolic_term(clingo.Number(n))
        state_atom = clingo_helper.create_atom(
            clingo_helper.create_function(
                name="__state",
                arguments=(
                    ply_number,
                    state_number,
                ),
            ),
        )
        state_literal = clingo_helper.create_literal(atom=state_atom)
        state_literals.append(state_literal)
        yield from _pin_state_indirectly(ply_number, state, state_literal)
        inverted_state = invert_state(state_shape, state)
        yield from _pin_state_indirectly(ply_number, inverted_state, state_literal, exclude=True)

    yield from _choose_state(state_literals)


def _pin_state_indirectly(
    ply_number: clingo_ast.AST,
    state: State,
    state_literal: clingo_ast.AST,
    *,
    exclude: bool = False,
) -> Iterator[clingo_ast.AST]:
    temporal_symbols = (
        clingo_helper.create_function(name="holds_at", arguments=(elem.as_clingo_ast(), ply_number)) for elem in state
    )
    atoms = (clingo_helper.create_atom(temporal_symbol) for temporal_symbol in temporal_symbols)
    sign = clingo_ast.Sign.Negation if not exclude else clingo_ast.Sign.NoSign
    literals = (clingo_helper.create_literal(sign=sign, atom=atom) for atom in atoms)
    bodies = ((state_literal, literal) for literal in literals)
    rules = (clingo_helper.create_rule(body=body) for body in bodies)
    yield from rules


_left_guard = clingo_helper.create_guard(
    comparison=clingo_ast.ComparisonOperator.LessEqual,
    term=clingo_helper.create_symbolic_term(clingo.Number(1)),
)
_right_guard = clingo_helper.create_guard(
    comparison=clingo_ast.ComparisonOperator.LessEqual,
    term=clingo_helper.create_symbolic_term(clingo.Number(1)),
)


def _choose_state(state_literals: Iterable[clingo_ast.AST]) -> Iterator[clingo_ast.AST]:
    conditional_literals = tuple(
        clingo_helper.create_conditional_literal(
            literal=state_literal,
        )
        for state_literal in state_literals
    )
    choice_aggregate = clingo_helper.create_aggregate(
        left_guard=_left_guard,
        elements=conditional_literals,
        right_guard=_right_guard,
    )
    choice_rule = clingo_helper.create_rule(head=choice_aggregate)

    yield choice_rule


def _get_direct_state_assertions(ply: int, possible_states: Iterable[State]) -> Iterator[clingo_ast.AST]:
    state_literals = []
    ply_number = clingo_helper.create_symbolic_term(clingo.Number(ply))
    for n, state in enumerate(possible_states):
        state_number = clingo_helper.create_symbolic_term(clingo.Number(n))
        state_atom = clingo_helper.create_atom(
            clingo_helper.create_function(
                name="__state",
                arguments=(
                    ply_number,
                    state_number,
                ),
            ),
        )
        state_literal = clingo_helper.create_literal(atom=state_atom)
        state_literals.append(state_literal)
        yield from _pin_state_directly(ply_number, state, state_literal)

    yield from _choose_state(state_literals)


def _pin_state_directly(
    ply_number: clingo_ast.AST,
    state: State,
    state_literal: clingo_ast.AST,
) -> Iterator[clingo_ast.AST]:
    body = (state_literal,)
    temporal_symbols = (
        clingo_helper.create_function(name="holds_at", arguments=(elem.as_clingo_ast(), ply_number)) for elem in state
    )
    atoms = (clingo_helper.create_atom(temporal_symbol) for temporal_symbol in temporal_symbols)
    heads = (clingo_helper.create_literal(atom=atom) for atom in atoms)
    rules = (clingo_helper.create_rule(head=head, body=body) for head in heads)
    yield from rules


@dataclass(frozen=True)
class ImperfectInformationRecord(Record):
    possible_states: Mapping[int, FrozenSet[State]] = field(default_factory=dict)
    """Possible states of the game by ply."""

    views: Mapping[int, Mapping[Role, View]] = field(default_factory=dict)
    """Views of the state by role by ply."""

    role_move_map: Mapping[int, Mapping[Role, Move]] = field(default_factory=dict)
    """Known moves by role by ply."""

    @property
    def offset(self) -> int:
        return min(self.possible_states.keys(), default=0)

    @property
    def horizon(self) -> int:
        """Maximum ply associated with either states, views or turns."""
        return max(
            max(self.possible_states.keys(), default=0),
            max(self.views.keys(), default=0),
            max(self.role_move_map.keys(), default=0),
        )

    def get_state_assertions(self, state_shape: StateShape) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the states of the game.

        Yields:
            Clingo assertions for the states of the game

        """
        if self.offset > 0:
            yield from _get_direct_state_assertions(self.offset, self.possible_states[self.offset])

        for ply, possible_states in self.possible_states.items():
            if ply == self.offset:
                continue
            yield from _get_indirect_state_assertions(ply, possible_states, state_shape)

    def get_view_assertions(self, sees_shape: SeesShape) -> Iterator[clingo_ast.AST]:
        for ply, views in self.views.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            for role, view in views.items():
                role_ast = role.as_clingo_ast()
                yield from get_as_assertions(
                    view,
                    name="sees_at",
                    pre_arguments=(role_ast,),
                    post_arguments=(current_time,),
                )
                inverted_view = invert_sees(sees_shape, role, view)
                yield from get_as_assertions(
                    inverted_view,
                    name="sees_at",
                    pre_arguments=(role_ast,),
                    post_arguments=(current_time,),
                    exclude=True,
                )

    def get_turn_assertions(self) -> Iterator[clingo_ast.AST]:
        """Get the clingo assertions for the turns of the game.

        Yields:
            Clingo assertions for the turns of the game

        """
        for ply, role_to_move in self.role_move_map.items():
            current_time = clingo_helper.create_symbolic_term(clingo.Number(ply))
            for role, move in role_to_move.items():
                role_ast = role.as_clingo_ast()
                yield from get_as_assertions(
                    (move,),
                    name="does_at",
                    pre_arguments=(role_ast,),
                    post_arguments=(current_time,),
                )

    def get_incidental_assertions(self) -> Iterator[clingo_ast.AST]:
        plies = range(self.offset, self.horizon)
        current_times = (clingo_helper.create_symbolic_term(clingo.Number(ply)) for ply in plies)
        terminal_at_functions = (
            clingo_helper.create_function(name="terminal_at", arguments=(current_time,))
            for current_time in current_times
        )
        terminal_at_atoms = (
            clingo_helper.create_atom(symbol=terminal_at_function) for terminal_at_function in terminal_at_functions
        )
        terminal_at_literals = (
            clingo_helper.create_literal(atom=terminal_at_atom) for terminal_at_atom in terminal_at_atoms
        )
        terminal_at_rules = (
            clingo_helper.create_rule(body=(terminal_at_literal,)) for terminal_at_literal in terminal_at_literals
        )
        yield from terminal_at_rules
