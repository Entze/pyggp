"""Provides all subrelations of GDL."""
from dataclasses import dataclass, field
from typing import ClassVar, NamedTuple, Optional, Sequence, Union

import clingo
import clingo.ast as clingo_ast
import lark
import lark.exceptions
from typing_extensions import Self

from pyggp._clingo import create_function, create_symbolic_term, create_variable
from pyggp.exceptions.subrelation_exceptions import MalformedTreeSubrelationError, ParsingSubrelationError

grammar = r"""
    subrelation: relation | primitive
    relation: empty_tuple
        | tuple
        | atom
        | atom "(" ")"
        | atom tuple
    empty_tuple: "(" ")"
    tuple: "(" _seperated{subrelation, ","} ")"
    atom: ATOMID
    primitive: number | string | variable
    number: INT | SIGNED_INT
    string: ESCAPED_STRING
    variable: wildcard
        | named_variable
    named_variable: UCID

    wildcard: anonymous_wildcard | named_wildcard
    anonymous_wildcard.1: "_"
    named_wildcard.1: "_"+ UCID

    LCID: LCASE_LETTER ("_" | LETTER | DIGIT)*
    UCID: UCASE_LETTER ("_" | LETTER | DIGIT)*
    ATOMID: ("_" | LCASE_LETTER) ("_" | LETTER | DIGIT)*

    _seperated{x, sep}: x (sep x)*

    %import common (INT, SIGNED_INT, ESCAPED_STRING, CNAME, UCASE_LETTER, LCASE_LETTER, LETTER, DIGIT, WS)
    %ignore WS

    """


@dataclass(frozen=True, order=True)
class Primitive:
    """Base class of primitives.

    Primitives include variables, numbers, and strings.

    """

    # region Attributes and Properties

    parser: ClassVar[lark.Lark] = lark.Lark(grammar=grammar, start="primitive")

    @property
    def infix_str(self) -> str:
        """Infix string representation of the primitive."""
        raise NotImplementedError

    # endregion

    # region Constructors

    @classmethod
    def from_clingo_symbol(cls, symbol: clingo.Symbol) -> Self:
        """Create primitive from clingo symbol.

        Args:
            symbol: Symbol to create primitive from

        Returns:
            Primitive created from symbol

        """
        if symbol.type == clingo.SymbolType.Function:
            message = "Cannot create primitive from function symbol"
            raise TypeError(message)
        if symbol.type == clingo.SymbolType.Number:
            number = Number.from_clingo_symbol(symbol)
            assert isinstance(
                number,
                Primitive,
            ), "Assumption: Subclass did not violate the liskov substitution principle"
            # Disable mypy. Because number is a Number, but mypy wants a Primitive (its baseclass).
            return number  # type: ignore[return-value]
        if symbol.type == clingo.SymbolType.String:
            string = String.from_clingo_symbol(symbol)
            assert isinstance(
                string,
                Primitive,
            ), "Assumption: Subclass did not violate the liskov substitution principle"
            # Disable mypy. Because number is a Number, but mypy wants a Primitive (its baseclass).
            return string  # type: ignore[return-value]
        message = f"Assumption: There are only 3 types of clingo symbols. Unknown symbol type: {symbol.type}"
        raise AssertionError(message)

    @classmethod
    def from_tree(cls, tree: lark.Tree[lark.Token]) -> Self:
        """Create primitive from lark tree.

        Args:
            tree: Tree to transform

        Returns:
            Corresponding primitive

        Raises:
            MalformedTreeSubrelationError: Tree is malformed

        """
        if tree.data != "primitive":
            raise MalformedTreeSubrelationError
        if not isinstance(tree.children[0], lark.Tree):
            raise MalformedTreeSubrelationError
        if tree.children[0].data == "number":
            number = Number.from_tree(tree.children[0])
            assert isinstance(number, cls), "Assumption: Subclass did not violate the liskov substitution principle."
            return number
        if tree.children[0].data == "string":
            string = String.from_tree(tree.children[0])
            assert isinstance(string, cls), "Assumption: Subclass did not violate the liskov substitution principle."
            return string
        if tree.children[0].data == "variable":
            variable = Variable.from_tree(tree.children[0])
            assert isinstance(variable, cls), "Assumption: Subclass did not violate the liskov substitution principle."
            return variable
        raise MalformedTreeSubrelationError

    @classmethod
    def from_str(cls, string: str) -> Self:
        """Create primitive from string.

        Args:
            string: String to create primitive from

        Returns:
            Primitive created from string

        Raises:
            ParsingSubrelationError: String could not be parsed

        """
        try:
            tree = cls.parser.parse(string)
        except (lark.exceptions.ParseError, lark.exceptions.LexError) as error:
            raise ParsingSubrelationError(string) from error
        return cls.from_tree(tree)

    # endregion

    # region Magic Methods

    def __rich__(self) -> str:
        """Stub implementation for rich method.

        This should be overwritten by subclasses.

        Returns:
            String representation of the primitive

        """
        return str(self)  # pragma: no cover

    # endregion

    # region Methods

    def unifies(self, other: "Symbol") -> bool:
        """Check whether the primitive unifies with another symbol.

        Args:
            other: Primitive to unify with

        Returns:
            Whether the primitives unify

        """
        return self == other or isinstance(self, Variable) or isinstance(other, Variable)

    def as_clingo_symbol(self) -> clingo.Symbol:
        """Convert to semantically equivalent clingo symbol.

        Returns:
            Semantically equivalent clingo symbol

        """
        raise NotImplementedError

    def as_clingo_ast(self) -> clingo_ast.AST:
        """Convert to semantically equivalent clingo AST.

        Returns:
            Semantically equivalent clingo ast

        """
        return create_symbolic_term(self.as_clingo_symbol())

    # endregion


@dataclass(frozen=True, order=True)
class Variable(Primitive):
    """Representation of a variable."""

    # region Attributes and Properties
    name: str
    "Name of the variable."

    @property
    def infix_str(self) -> str:
        """Infix string representation of the variable."""
        return self.name

    @property
    def is_wildcard(self) -> bool:
        """Whether the variable is a wildcard variable."""
        return self.name.startswith("_")

    # endregion

    # region Constructors

    @classmethod
    # Disable ARG003 (Unused class method argument). Because it overrides the base class method.
    def from_clingo_symbol(cls, symbol: clingo.Symbol) -> Self:  # noqa: ARG003
        """Variables cannot be created from clingo symbols, always raises an error.

        Args:
            symbol: Symbol to create variable from

        Raises:
            ValueError: Always

        """
        message = "Variables cannot be created from clingo symbols."
        raise TypeError(message)

    @classmethod
    def from_tree(cls, tree: lark.Tree[lark.Token]) -> Self:
        """Create variable from lark tree.

        Args:
            tree: Tree to transform

        """
        if tree.data != "variable":
            raise MalformedTreeSubrelationError
        if not isinstance(tree.children[0], lark.Tree):
            raise MalformedTreeSubrelationError
        if tree.children[0].data == "named_variable":
            name = tree.children[0].children[0]
            return cls(str(name))
        if tree.children[0].data == "wildcard":
            if not isinstance(tree.children[0].children[0], lark.Tree):
                raise MalformedTreeSubrelationError
            if tree.children[0].children[0].data == "anonymous_wildcard":
                return cls("_")
            if tree.children[0].children[0].data == "named_wildcard":
                name = tree.children[0].children[0].children[0]
                return cls(f"_{name}")
        raise MalformedTreeSubrelationError

    # endregion

    # region Magic Methods

    def __str__(self) -> str:
        """Return the infix string representation of the variable.

        Returns:
            Infix string representation of the variable

        See Also:
            :attr:`infix_str`

        """
        return self.infix_str

    def __rich__(self) -> str:
        """Return the rich enhanced infix string representation of the variable.

        Returns:
            Rich enhanced infix string representation of the variable

        See Also:
            :attr:`infix_str`

        """
        return f"[italic yellow]{self.infix_str}[/italic yellow]"

    # endregion

    # region Methods

    # Disables ARG002 (Unused method argument). Because overriding a method.
    def unifies(self, other: "Symbol") -> bool:  # noqa: ARG002
        """Check whether the variable unifies with another variable.

        Args:
            other: Symbol to unify with

        Returns:
            Whether the variable unifies with the primitive

        """
        return True

    def as_clingo_symbol(self) -> clingo.Symbol:
        """Cannot convert variable to clingo symbol.

        Raises:
            ValueError: Always

        """
        raise ValueError

    def as_clingo_ast(self) -> clingo_ast.AST:
        """Convert to semantically equivalent clingo AST.

        Converts the variable to a clingo AST variable. The name of the variable is changed in case of wildcard.

        Returns:
            The clingo AST variable

        """
        if self.is_wildcard:
            return create_variable("_")
        return create_variable(self.name)

    # end region


@dataclass(frozen=True, order=True)
class Number(Primitive):
    """Representation of a (whole) number."""

    # region Attributes and Properties

    number: int
    "Numeric value of the number."

    @property
    def infix_str(self) -> str:
        """Infix string representation of the number."""
        return str(self.number)

    # endregion

    # region Constructors

    @classmethod
    def from_clingo_symbol(cls, symbol: clingo.Symbol) -> Self:
        """Create number from clingo symbol.

        Args:
            symbol: Symbol to create number from

        Returns:
            Corresponding number

        Raises:
            TypeError: Symbol is not a number

        """
        if symbol.type != clingo.SymbolType.Number:
            message = "Symbol is not a number"
            raise TypeError(message)
        return cls(symbol.number)

    @classmethod
    def from_tree(cls, tree: lark.Tree[lark.Token]) -> Self:
        """Create number from lark tree.

        Args:
            tree: Tree to transform

        Returns:
            Corresponding number

        Raises:
            MalformedTreeSubrelationError: Tree is malformed

        """
        if tree.data != "number":
            raise MalformedTreeSubrelationError
        if not isinstance(tree.children[0], lark.Token):
            raise MalformedTreeSubrelationError
        return cls(int(tree.children[0]))

    # endregion

    # region Magic Methods

    def __str__(self) -> str:
        """Return the infix string representation of the number.

        Returns:
            Infix string representation of the number.

        """
        return self.infix_str

    def __rich__(self) -> str:
        """Return the rich enhanced infix string representation of the number.

        Returns:
            Rich enhanced infix string representation of the number.

        """
        return f"[blue]{self.infix_str}[/blue]"

    # endregion

    # region Methods

    def as_clingo_symbol(self) -> clingo.Symbol:
        """Convert to semantically equivalent clingo symbol.

        Returns:
            Semantically equivalent clingo symbol

        """
        return clingo.Number(self.number)

    # endregion


@dataclass(frozen=True, order=True)
class String(Primitive):
    """Representation of a string."""

    # region Attributes and Properties

    string: str
    "String value of the string."

    @property
    def infix_str(self) -> str:
        """Infix string representation of the string."""
        return f'"{self.string}"'

    # endregion

    # region Constructors

    @classmethod
    def from_clingo_symbol(cls, symbol: clingo.Symbol) -> Self:
        """Create string from clingo symbol.

        Args:
            symbol: Symbol to create string from

        Returns:
            Corresponding string

        Raises:
            TypeError: Symbol is not a string

        """
        if symbol.type != clingo.SymbolType.String:
            message = "Symbol is not a string"
            raise TypeError(message)
        return cls(symbol.string)

    @classmethod
    def from_tree(cls, tree: lark.Tree[lark.Token]) -> Self:
        """Create string from lark tree.

        Args:
            tree: Tree to transform

        Returns:
            Corresponding string

        Raises:
            MalformedTreeSubrelationError: Tree is malformed

        """
        if tree.data != "string":
            raise MalformedTreeSubrelationError
        if not isinstance(tree.children[0], lark.Token):
            raise MalformedTreeSubrelationError
        return cls(str(tree.children[0][1:-1]))

    # endregion

    # region Magic Methods

    def __str__(self) -> str:
        """Return the infix string representation of the string.

        Returns:
            Infix string representation of the string.

        """
        return self.infix_str

    def __rich__(self) -> str:
        """Return the rich enhanced infix string representation of the string.

        Returns:
            Rich enhanced infix string representation of the string.

        """
        return f"[green]{self.infix_str}[/green]"

    # endregion

    # region Methods

    def as_clingo_symbol(self) -> clingo.Symbol:
        """Convert to semantically equivalent clingo symbol.

        Returns:
            Semantically equivalent clingo symbol

        """
        return clingo.String(self.string)

    # endregion


@dataclass(frozen=True, order=True)
class Relation:
    """Representation of a relation."""

    # region Inner Classes

    class Signature(NamedTuple):
        """Signature of a relation.

        Attributes:
            name: Name of the relation
            arity: Arity of the relation

        """

        name: Optional[str]
        """Name of the relation."""
        arity: int
        """Arity of the relation."""

        def __str__(self) -> str:
            """Return the string representation of the relations' signature.

            Returns:
                String representation of the relations' signature.

            """
            if self.name is None:
                return f"({self.arity})"
            return f"{self.name}/{self.arity}"

        def __rich__(self) -> str:
            """Return the rich enhanced string representation of the relations' signature.

            Returns:
                Rich enhanced string representation of the relations' signature.

            """
            if self.name is None:
                return f"[italic]({self.arity})[/italic]"
            return f"[italic][purple]{self.name}[/purple]/{self.arity}[/italic]"

    # endregion

    # region Attributes and Properties

    name: Optional[str] = None
    "Name of the relation."
    arguments: Sequence["Subrelation"] = field(default_factory=tuple)
    "Arguments of the relation."

    parser: ClassVar[lark.Lark] = lark.Lark(grammar=grammar, start="relation")
    "Parser starting at the relation rule."

    @property
    def arity(self) -> int:
        """Arity of the relation."""
        return len(self.arguments)

    @property
    def signature(self) -> Signature:
        """Signature of the relation."""
        return self.Signature(self.name, self.arity)

    @property
    def infix_str(self) -> str:
        """Infix string representation of the relation."""
        if self.name is None:
            return f"({','.join(arg.infix_str for arg in self.arguments)})"
        if not self.arguments:
            return self.name
        return f"{self.name}({','.join(arg.infix_str for arg in self.arguments)})"

    # endregion

    # region Constructors

    @classmethod
    def from_symbols(cls, name: Optional[str] = None, *arguments: "Symbol") -> Self:
        """Create a relation from symbols.

        Convenience method to not have to call Subrelation for each symbol.

        Args:
            name: Name of the relation
            arguments: Symbols to use as arguments

        See Also:
            :meth:`tuple` for creating a tuple of symbols

        """
        return cls(name=name, arguments=tuple(Subrelation(symbol) for symbol in arguments))

    @classmethod
    def get_tuple(cls, *arguments: "Symbol") -> Self:
        """Create a tuple of symbols.

        Returns:
            A relation without name and the given symbols as arguments

        """
        return cls.from_symbols(None, *arguments)

    @classmethod
    def from_clingo_symbol(cls, symbol: clingo.Symbol) -> Self:
        """Create a relation from a clingo symbol.

        Args:
            symbol: Symbol to transform

        Returns:
            Corresponding relation

        Raises:
            TypeError: Symbol is not a function

        """
        if symbol.type != clingo.SymbolType.Function:
            message = "Symbol is not a function"
            raise TypeError(message)
        return cls(name=symbol.name, arguments=tuple(Subrelation.from_clingo_symbol(arg) for arg in symbol.arguments))

    @classmethod
    def from_tree(cls, tree: lark.Tree[lark.Token]) -> Self:
        """Create a relation from a tree.

        Args:
            tree: Tree to transform

        Returns:
            Corresponding relation

        Raises:
            MalformedTreeSubrelationError: Tree is malformed

        """
        if tree.data != "relation":
            raise MalformedTreeSubrelationError
        if not isinstance(tree.children[0], lark.Tree):
            raise MalformedTreeSubrelationError
        if tree.children[0].data == "empty_tuple":
            return cls()
        if tree.children[0].data == "tuple":
            return cls._from_tree_tuple(tree.children[0])
        # Disables PLR2004 (Magic value used in comparison). Because the tree may only have 1 or 2 children.
        if not (0 < len(tree.children) < 3):  # noqa: PLR2004
            raise MalformedTreeSubrelationError
        # Disables PLR2004 (Magic value used in comparison). Because 1 can only be accessed if the tree has at least 2
        # children.
        tuple_child = tree.children[1] if len(tree.children) == 2 else None  # noqa: PLR2004
        if tree.children[0].data != "atom" or (
            tuple_child is not None and (not isinstance(tuple_child, lark.Tree) or tuple_child.data != "tuple")
        ):
            raise MalformedTreeSubrelationError
        if tuple_child is None:
            return cls._from_tree_atom(tree)

        return cls._from_tree_relation(tree, tuple_child.children)

    @classmethod
    def _from_tree_tuple(cls, tree: lark.Tree[lark.Token]) -> Self:
        children = tree.children
        if any(not isinstance(child, lark.Tree) for child in children):
            raise MalformedTreeSubrelationError
        return cls(
            name=None,
            arguments=tuple(Subrelation.from_tree(child) for child in children if isinstance(child, lark.Tree)),
        )

    @classmethod
    def _from_tree_atom(cls, tree: lark.Tree[lark.Token]) -> Self:
        if not isinstance(tree.children[0], lark.Tree):
            raise MalformedTreeSubrelationError  # pragma: no cover (cannot happen unless called directly)
        return cls(name=str(tree.children[0].children[0]))

    @classmethod
    def _from_tree_relation(
        cls,
        tree: lark.Tree[lark.Token],
        children: Sequence[Union[lark.Token, lark.Tree[lark.Token]]],
    ) -> Self:
        if not isinstance(tree.children[0], lark.Tree):
            raise MalformedTreeSubrelationError  # pragma: no cover (cannot happen unless called directly)
        if any(not isinstance(child, lark.Tree) for child in children):
            raise MalformedTreeSubrelationError
        return cls(
            name=str(tree.children[0].children[0]),
            arguments=tuple(Subrelation.from_tree(child) for child in children if isinstance(child, lark.Tree)),
        )

    @classmethod
    def from_str(cls, string: str) -> Self:
        """Parse a relation from a string.

        Args:
            string: String to parse

        Returns:
            Corresponding relation

        Raises:
            ParsingSubrelationError: String cannot be parsed

        """
        try:
            tree = cls.parser.parse(string)
        except (lark.exceptions.ParseError, lark.exceptions.LexError) as error:
            raise ParsingSubrelationError(string) from error
        return cls.from_tree(tree)

    # endregion

    # region Magic Methods

    def __str__(self) -> str:
        """Return the string representation of the relation.

        Returns:
            String representation of the relation.

        """
        return self.infix_str

    def __rich__(self) -> str:
        """Return the rich enhanced infix string representation of the relation."""
        if self.name is None:
            return f"({','.join(subrelation.__rich__() for subrelation in self.arguments)})"
        return f"[purple]{self.name}[/purple]({', '.join(subrelation.__rich__() for subrelation in self.arguments)})"

    # endregion

    # region Methods

    def matches_signature(self, name: Optional[str] = None, arity: int = 0) -> bool:
        """Check if a signature matches the relation.

        Args:
            name: Name of the relation
            arity: Arity of the relation

        Returns:
            True if the signature matches the relation, False otherwise

        Examples:
            >>> r = Relation.from_str("r(a,b)")
            >>> r.matches_signature("r", 2)
            True
            >>> sig = Relation.Signature(name="s", arity=0)
            >>> r.matches_signature(*sig)
            False

        """
        return self.name == name and self.arity == arity

    def unifies(self, other: "Symbol") -> bool:
        """Check if two relations unify.

        Args:
            other: Relation to check against

        Returns:
            True if the relations unify, False otherwise

        """
        if isinstance(other, Relation):
            if self.name != other.name or self.arity != other.arity:
                return False
            return all(
                subrelation.unifies(other_subrelation)
                for subrelation, other_subrelation in zip(self.arguments, other.arguments)
            )

        return isinstance(other, Variable)

    def as_clingo_symbol(self) -> clingo.Symbol:
        """Convert to semantically equivalent clingo symbol.

        Returns:
            Semantically equivalent clingo symbol representation of the relation

        """
        return clingo.Function(self.name or "", tuple(subrelation.as_clingo_symbol() for subrelation in self.arguments))

    def as_clingo_ast(self) -> clingo_ast.AST:
        """Convert to semantically equivalent clingo AST.

        Returns:
            Semantically equivalent clingo AST representation of the relation

        """
        return create_function(
            name=self.name or "",
            arguments=tuple(subrelation.as_clingo_ast() for subrelation in self.arguments),
        )

    # endregion


Symbol = Union[Relation, Primitive]
"""Symbols describe either relations or primitives.

Symbols should almost never be used on their own. Use Subrelations instead.

See Also:
    :class:`Subrelation` for a description of subrelations

"""


@dataclass(frozen=True)
class Subrelation:
    """Representation of a subrelation.

    A subrelation is either a primitive or a relation.

    """

    # region Attributes and Properties

    symbol: Symbol = field(default_factory=Relation)
    "Symbol of the subrelation."

    parser: ClassVar[lark.Lark] = lark.Lark(grammar=grammar, start="subrelation")
    "Parser starting at the subrelation rule."

    @property
    def infix_str(self) -> str:
        """Return the infix string representation of the subrelation.

        Returns:
            Infix string representation of the subrelation.

        """
        return self.symbol.infix_str

    @property
    def is_relation(self) -> bool:
        """Whether the subrelation is a relation."""
        return isinstance(self.symbol, Relation)

    @property
    def is_number(self) -> bool:
        """Whether the subrelation is a number."""
        return isinstance(self.symbol, Number)

    @property
    def is_string(self) -> bool:
        """Whether the subrelation is a string."""
        return isinstance(self.symbol, String)

    @property
    def is_variable(self) -> bool:
        """Whether the subrelation is a variable."""
        return isinstance(self.symbol, Variable)

    # endregion

    # region Constructors

    @classmethod
    def from_clingo_symbol(cls, symbol: clingo.Symbol) -> Self:
        """Create a subrelation from a clingo symbol.

        Args:
            symbol: Symbol to transform

        Returns:
            Corresponding subrelation

        """
        if symbol.type == clingo.SymbolType.Function:
            return cls(Relation.from_clingo_symbol(symbol))
        assert (
            symbol.type == clingo.SymbolType.Number or symbol.type == clingo.SymbolType.String
        ), f"Assumption: There are only 3 symbol types. Unknown symbol type {symbol.type}."
        return cls(Primitive.from_clingo_symbol(symbol))

    @classmethod
    def from_tree(cls, tree: lark.Tree[lark.Token]) -> Self:
        """Create a subrelation from a lark tree.

        Args:
            tree: Tree to transform

        Returns:
            Corresponding subrelation

        Raises:
            MalformedTreeSubrelationError: Tree is malformed

        """
        if tree.data != "subrelation":
            raise MalformedTreeSubrelationError
        if not isinstance(tree.children[0], lark.Tree):
            raise MalformedTreeSubrelationError
        if tree.children[0].data == "primitive":
            return cls(Primitive.from_tree(tree.children[0]))
        if tree.children[0].data == "relation":
            return cls(Relation.from_tree(tree.children[0]))
        raise MalformedTreeSubrelationError

    @classmethod
    def from_str(cls, string: str) -> Self:
        """Parse a subrelation from a string.

        Args:
            string: String to parse

        Returns:
            Corresponding subrelation

        Raises:
            ParsingSubrelationError: String cannot be parsed

        """
        try:
            tree = cls.parser.parse(string)
        except (lark.exceptions.ParseError, lark.exceptions.LexError) as error:
            raise ParsingSubrelationError(string) from error
        return cls.from_tree(tree)

    # endregion

    # region Magic Methods

    def __str__(self) -> str:
        """Return the string representation of the subrelation.

        Returns:
            String representation of the subrelation.

        """
        return self.infix_str

    def __rich__(self) -> str:
        """Return the rich enhanced infix string representation of the subrelation.

        Returns:
            Rich enhanced infix string representation of the subrelation.

        """
        return self.symbol.__rich__()

    def __lt__(self, other: Self) -> bool:
        """Check if a subrelation is less than another subrelation.

        Args:
            other: Subrelation to compare against

        Returns:
            True if the subrelation is less than the other subrelation, False otherwise

        """
        self_rank = _type_ranking[type(self.symbol)]
        other_rank = _type_ranking[type(other.symbol)]
        if self_rank != other_rank:
            return self_rank < other_rank
        assert isinstance(self, type(other)), (
            "Assumption: If the ranks are equal, the types must be equal. "
            f"{type(self).__name__}({self_rank}) != {type(other).__name__}({other_rank})"
        )
        assert isinstance(other, type(self)), (
            "Assumption: If the ranks are equal, the types must be equal. "
            f"{type(self).__name__}({self_rank}) != {type(other).__name__}({other_rank})"
        )
        # Disables mypy operator (Unsupported operand types). Because of the assumption that the types are equal.
        return self.symbol < other.symbol  # type: ignore[operator]

    def __gt__(self, other: Self) -> bool:
        """Check if a subrelation is greater than another subrelation.

        Args:
            other: Subrelation to compare against

        Returns:
            True if the subrelation is greater than the other subrelation, False otherwise

        """
        self_rank = _type_ranking[type(self.symbol)]
        other_rank = _type_ranking[type(other.symbol)]
        if self_rank != other_rank:
            return self_rank > other_rank
        assert isinstance(self, type(other)), (
            "Assumption: If the ranks are equal, the types must be equal. "
            f"{type(self).__name__}({self_rank}) != {type(other).__name__}({other_rank})"
        )
        assert isinstance(other, type(self)), (
            "Assumption: If the ranks are equal, the types must be equal. "
            f"{type(self).__name__}({self_rank}) != {type(other).__name__}({other_rank})"
        )
        # Disables mypy operator (Unsupported operand types). Because of the assumption that the types are equal.
        return self.symbol > other.symbol  # type: ignore[operator]

    # endregion

    # region Methods

    def unifies(self, other: Self) -> bool:
        """Check if two subrelations unify.

        Args:
            other: Subrelation to check against

        Returns:
            True if the subrelations unify, False otherwise

        """
        return self.symbol.unifies(other.symbol)

    def matches_signature(self, name: Optional[str] = None, arity: int = 0) -> bool:
        """Check if the subrelation is a relation with the given name and arity.

        Args:
            name: Name of the relation
            arity: Arity of the relation

        Returns:
            True if the subrelation is a relation with the given name and arity, False otherwise

        """
        return isinstance(self.symbol, Relation) and self.symbol.matches_signature(name, arity)

    def as_clingo_symbol(self) -> clingo.Symbol:
        """Convert to semantically equivalent clingo symbol.

        Returns:
            Semantically equivalent clingo symbol

        """
        return self.symbol.as_clingo_symbol()

    def as_clingo_ast(self) -> clingo.ast.AST:
        """Convert to semantically equivalent clingo ast.

        Returns:
            Semantically equivalent clingo ast

        """
        return self.symbol.as_clingo_ast()

    # endregion


_type_ranking = {
    Relation: 0,
    Number: 1,
    String: 2,
    Variable: 3,
    Primitive: 4,
    Subrelation: 5,
}
