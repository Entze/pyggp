"""Classes and functions for working with GDL.

This includes the necessary classes and functions for representing GDL programs.

"""
from dataclasses import dataclass, field
from typing import Sequence, Self


@dataclass(frozen=True)
class Variable:
    r"""Representation of a variable."""

    name: str
    "Name of the variable."


@dataclass(frozen=True)
class Relation:
    """Representation of a relation.

    Relations are the basic building blocks of GDL. They are used to represent atoms (relations without arguments) and
    n-ary relations. They are self-referential --- they can contain other relations as arguments.
    """

    name: str | None = None
    "Name of the relation. If None, the relation is an atom."
    arguments: Sequence[Self | int | str | Variable] = field(default_factory=tuple)
    "Arguments of the relation."

    @property
    def arity(self) -> int:
        """Arity of the relation."""
        return len(self.arguments)

    def match(self, name: str | None = None, arity: int = 0) -> bool:
        """Check if the relation matches the given signature.

        Args:
            name: The name of the signature.
            arity: The arity of the signature.

        Returns:
            True if the relation matches the given signature exactly, False otherwise.
        """
        return name == self.name and arity == self.arity
