"""Valuations for tree agents."""
import abc
from dataclasses import dataclass
from typing import Any, Literal

from typing_extensions import Self


@dataclass(frozen=True)
class Valuation(abc.ABC):
    """Base class for all valuations."""

    def __lt__(self, other: Any) -> bool:
        """Less than comparison operator.

        Args:
            other: Other object to compare to

        Returns:
            True if the other object is a valuation and is less than the other, False otherwise

        """
        if not isinstance(other, Valuation):
            return False
        comp = self.compare(other)
        return comp == "<"

    def __le__(self, other: Any) -> bool:
        """Less than or equal to comparison operator.

        Args:
            other: Other object to compare to

        Returns:
            True if the other object is a valuation and is less than or equal to the other, False otherwise

        """
        if not isinstance(other, Valuation):
            return False
        comp = self.compare(other)
        return comp == "<" or comp == "=="

    def __gt__(self, other: Any) -> bool:
        """Greater than comparison operator.

        Args:
            other: Other object to compare to

        Returns:
            True if the other object is not a valuation or is greater than the other, False otherwise

        """
        if not isinstance(other, Valuation):
            return True
        comp = self.compare(other)
        return comp == ">"

    def __ge__(self, other: Any) -> bool:
        """Greater than or equal to comparison operator.

        Args:
            other: Other object to compare to

        Returns:
            True if the other object is not a valuation or is greater than or equal to the other, False otherwise

        """
        if not isinstance(other, Valuation):
            return True
        comp = self.compare(other)
        return comp == ">" or comp == "=="

    def __rich__(self) -> str:
        """Rich representation of the valuation.

        Returns:
            Rich representation of the valuation

        """
        if hasattr(self, "__str__"):
            return self.__str__()
        return self.__repr__()

    @abc.abstractmethod
    def compare(self, other: Self) -> Literal["<", "==", ">"]:
        """Compares this valuation to another.

        Args:
            other: Other valuation to compare to

        Returns:
            "<", "==", or ">" if this valuation is less than, equal to, or greater than the other

        """
        raise NotImplementedError

    @abc.abstractmethod
    def propagate(self, other: Self) -> Self:
        """Combines the information from this valuation with another.

        Args:
            other: Other valuation to combine with

        Returns:
            New valuation that combines the information from this valuation with the other

        """
        raise NotImplementedError
