"""Provides the `Literal` class and supporting classes and functions."""
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Type

from typing_extensions import Self

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

    # endregion

    # region Attributes and Properties

    atom: Relation
    "Atom of the literal."
    sign: Sign = Sign.NOSIGN
    "Sign of the literal."

    @property
    def infix_str(self) -> str:
        """Infix string representation of the literal.

        Returns:
            The infix string representation

        """
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

    def __rich__(self) -> str:
        """Return the rich enhanced infix string representation of the literal.

        Returns:
            Rich enhanced infix string representation

        """
        if self.sign == Literal.Sign.NOSIGN:
            return self.atom.__rich__()
        return f"[italic]not[/italic] {self.atom.__rich__()}"

    # endregion
