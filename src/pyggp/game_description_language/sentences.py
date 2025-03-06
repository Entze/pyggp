"""Provides the `Sentence` class and supporting classes and functions."""

from dataclasses import dataclass, field
from typing import Sequence

import clingo.ast as clingo_ast

from pyggp._clingo import create_atom, create_literal, create_rule
from pyggp.game_description_language.literals import Literal
from pyggp.game_description_language.subrelations import Relation


@dataclass(frozen=True)
class Sentence:
    """Representation of a sentence.

    Sentences are also called rules.

    """

    # region Attributes and Properties

    head: Relation
    "Head of the sentence."
    body: Sequence[Literal] = field(default_factory=tuple)
    "Body of the sentence."

    @property
    def infix_str(self) -> str:
        """Infix string representation of the sentence."""
        if not self.body:
            return f"{self.head.infix_str}."
        return f"{self.head.infix_str} :- {', '.join(literal.infix_str for literal in self.body)}."

    # endregion

    # region Magic Methods

    def __str__(self) -> str:
        """Return the infix string representation of the sentence.

        Returns:
            String representation of the sentence

        """
        return self.infix_str

    def __repr__(self) -> str:
        """Return the infix string representation of the sentence.

        Returns:
            String representation of the sentence

        """
        return self.infix_str

    def __rich__(self) -> str:
        """Return the rich enhanced infix string representation of the sentence.

        Returns:
            Rich enhanced string representation of the sentence

        """
        if not self.body:
            return f"{self.head.__rich__()}."
        if len(self.body) == 1:
            return f"{self.head.__rich__()} :- {', '.join(literal.__rich__() for literal in self.body)}."
        body_str = ",\n\t".join(literal.__rich__() for literal in self.body)
        return f"{self.head.__rich__()} :-\n\t{body_str}."

    # endregion

    # region Methods

    def as_clingo_ast(self) -> clingo_ast.AST:
        """Convert to semantically equivalent clingo AST.

        Returns:
            Semantically equivalent clingo AST

        """
        return create_rule(
            head=create_literal(atom=create_atom(symbol=self.head.as_clingo_ast())),
            body=tuple(literal.as_clingo_ast() for literal in self.body),
        )

    # endregion
