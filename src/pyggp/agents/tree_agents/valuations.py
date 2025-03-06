"""Valuations for tree agents."""

from typing import Any, Protocol, TypeVar

from typing_extensions import Self

_U = TypeVar("_U")


class Valuation(Protocol[_U]):
    """Protocol for valuations."""

    utility: _U

    @classmethod
    def from_utility(cls, utility: _U) -> Self:
        """Constructs a valuation from a utility.

        Args:
            utility: Utility

        Returns:
            Valuation

        """

    def __lt__(self, other: Any) -> bool:
        """Less than comparison operator.

        Args:
            other: Other object to compare to

        Returns:
            True if the other object is a valuation and is less than the other, False otherwise

        """

    def __le__(self, other: Any) -> bool:
        """Less than or equal to comparison operator.

        Args:
            other: Other object to compare to

        Returns:
            True if the other object is a valuation and is less than or equal to the other, False otherwise

        """

    def __gt__(self, other: Any) -> bool:
        """Greater than comparison operator.

        Args:
            other: Other object to compare to

        Returns:
            True if the other object is not a valuation or is greater than the other, False otherwise

        """

    def __ge__(self, other: Any) -> bool:
        """Greater than or equal to comparison operator.

        Args:
            other: Other object to compare to

        Returns:
            True if the other object is not a valuation or is greater than or equal to the other, False otherwise

        """

    def propagate(self, utility: _U) -> Self:
        """Combines the information from this valuation with a utility.

        Args:
            utility: Immediate utility of a node or state

        Returns:
            Updated valuation

        """
