"""Provides the `Literal` class and supporting classes and functions."""

from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Type

import clingo.ast as clingo_ast
from typing_extensions import Self

import pyggp._clingo as clingo_helper
from pyggp.game_description_language.subrelations import Relation


@dataclass(frozen=True)
class Literal:
    """Representation of a literal."""

    # region Inner Classes

    class Sign(IntEnum):
        """Sign of a literal."""

        NOSIGN = auto()
        "No sign, corresponds to `atom`."
        NEGATIVE = auto()
        "Negative, corresponds to `not atom`."

        def as_clingo_ast(self) -> clingo_ast.Sign:
            """Convert to semantically equivalent clingo AST.

            Returns:
                The clingo AST

            """
            if self == Literal.Sign.NOSIGN:
                return clingo_ast.Sign.NoSign
            if self == Literal.Sign.NEGATIVE:
                return clingo_ast.Sign.Negation
            message = f"Assumption: All cases are covered. {self} is not covered."
            raise AssertionError(message)

    # endregion

    # region Attributes and Properties

    atom: Relation
    "Atom of the literal."
    sign: Sign = Sign.NOSIGN
    "Sign of the literal."

    @property
    def is_comparison(self) -> bool:
        """Whether the literal is a comparison."""
        return self.atom.name is not None and self.atom.name.startswith("__comp_")

    @property
    def is_not_equal(self) -> bool:
        """Whether the literal is a not equal relation.

        Returns:
            Whether the literal is a not equal relation

        """
        return self.atom.name == "__comp_not_equal" and len(self.atom.arguments) > 1

    @property
    def infix_str(self) -> str:
        """Infix string representation of the literal.

        Returns:
            The infix string representation

        """
        if self.is_comparison:
            if self.is_not_equal:
                return self._infix_str__comp_not_equal()
            message = "Assumption: All __comp_ atoms are covered."
            raise AssertionError(message)
        if self.sign == Literal.Sign.NOSIGN:
            return self.atom.infix_str
        return f"not {self.atom.infix_str}"

    # endregion

    # region Magic Methods

    def __neg__(self) -> Self:
        """Negates the literal.

        Returns:
            A literal with negated sign

        """
        cls: Type[Self] = type(self)
        # Disables PyCharm inspection. This seems to be a false positive
        # noinspection PyArgumentList
        return cls(
            atom=self.atom,
            sign=Literal.Sign.NEGATIVE if self.sign == Literal.Sign.NOSIGN else Literal.Sign.NOSIGN,
        )

    def __str__(self) -> str:
        """Return the infix string representation of the literal.

        Returns:
            The string representation

        """
        return self.infix_str

    def __repr__(self) -> str:
        """Return the infix string representation of the literal.

        Returns:
            The string representation

        """
        return self.infix_str

    def __rich__(self) -> str:
        """Return the rich enhanced infix string representation of the literal.

        Returns:
            Rich enhanced infix string representation

        """
        if self.sign == Literal.Sign.NOSIGN:
            return self.atom.__rich__()
        return f"[italic]not[/italic] {self.atom.__rich__()}"

    # endregion

    # region Methods

    def as_clingo_ast(self) -> clingo_ast.AST:
        """Convert to semantically equivalent clingo AST.

        Returns:
            The clingo AST

        """
        if self.atom.name is not None and self.atom.name.startswith("__comp_"):
            if self.atom.name == "__comp_not_equal" and len(self.atom.arguments) > 1:
                return clingo_helper.create_literal(
                    atom=self._as_clingo_ast__comp_not_equal(),
                    sign=clingo_ast.Sign.NoSign,
                )
            message = f"Assumption: All __comp_ atoms are covered. {self.atom.name} is not covered."
            raise AssertionError(message)

        return clingo_helper.create_literal(
            sign=self.sign.as_clingo_ast(),
            atom=clingo_helper.create_atom(self.atom.as_clingo_ast()),
        )

    def _infix_str__comp_not_equal(self) -> str:
        operator = " != "
        if self.sign == Literal.Sign.NEGATIVE:
            operator = " = "
        return operator.join(argument.infix_str for argument in self.atom.arguments)

    def _as_clingo_ast__comp_not_equal(self) -> clingo_ast.AST:
        operator = clingo_ast.ComparisonOperator.NotEqual
        if self.sign == Literal.Sign.NEGATIVE:
            operator = clingo_ast.ComparisonOperator.Equal
        term = self.atom.arguments[0].as_clingo_ast()
        guards = tuple(
            clingo_helper.create_guard(comparison=operator, term=argument.as_clingo_ast())
            for argument in self.atom.arguments[1:]
        )
        return clingo_helper.create_comparison(term=term, guards=guards)

    # endregion
