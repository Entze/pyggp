from typing import Final, FrozenSet, Iterator, NamedTuple, NewType, Optional, Sequence

import clingo.ast as clingo_ast

import pyggp._clingo as clingo_helper
from pyggp import game_description_language as gdl
from pyggp.mappings import FrozenDict

_State = FrozenSet[gdl.Subrelation]
State = NewType("State", _State)
"""States are sets of subrelations."""

View = NewType("View", State)
"""Views are (partial) states."""

Role = NewType("Role", gdl.Subrelation)
"""Roles are relations, numbers, or string."""

Play = NewType("Play", gdl.Relation)
"""Plays are does/2 relations.

Plays are of the form does(Subrelation(Role), Subrelation(Move)).

"""

Move = NewType("Move", gdl.Subrelation)
"""Moves are relations, numbers, or strings."""

RANDOM: Final[Role] = Role(gdl.Subrelation(gdl.Relation("random")))


class Turn(FrozenDict[Role, Move]):
    """Mapping of roles to a move.

    Resembles a collection of plays.

    """

    def as_plays(self) -> Iterator[Play]:
        """Return the plays of the turn.

        Returns:
            Plays of the turn

        """
        return (Play(gdl.Relation("does", arguments=(role, move))) for role, move in self._pairs)

    def get_assertions(self, current_time: clingo_ast.AST) -> Iterator[clingo_ast.AST]:
        for role, move in self.items():
            role_ast = role.as_clingo_ast()
            move_ast = move.as_clingo_ast()
            yield clingo_helper.create_rule(
                body=(
                    clingo_helper.create_literal(
                        sign=clingo_ast.Sign.Negation,
                        atom=clingo_helper.create_atom(
                            clingo_helper.create_function(
                                name="does_at",
                                arguments=(role_ast, move_ast, current_time),
                            ),
                        ),
                    ),
                ),
            )


class DevelopmentStep(NamedTuple):
    """Describes a possible state and a turn that leads to the next state."""

    state: State
    """State of that step."""
    turn: Optional[Turn]
    """Turn of that step, None if ambiguous."""


_Development = Sequence[DevelopmentStep]
Development = NewType("Development", _Development)
"""A sequence of development steps."""
