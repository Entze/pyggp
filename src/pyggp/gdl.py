"""Classes and functions for working with GDL.

This includes the necessary classes and functions for representing GDL programs.

"""
from dataclasses import dataclass, field
from enum import auto, IntEnum
from typing import (
    Sequence,
    Self,
    TypeAlias,
    Type,
    NamedTuple,
    Tuple,
    MutableSequence,
    MutableMapping,
    Set,
    Union,
    FrozenSet,
    Mapping,
)

import clingo.ast

_pos = clingo.ast.Position("<string>", 0, 0)
_loc = clingo.ast.Location(_pos, _pos)


@dataclass(frozen=True)
class Variable:
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

    # region Magic Methods

    def __str__(self) -> str:
        """Return the infix string representation of the variable.

        Returns:
            The infix string representation of the variable.

        See Also:
            :attr:`infix_str`

        """
        return self.infix_str

    # endregion

    # region Methods

    def to_clingo_ast(self) -> clingo.ast.AST:
        if self.is_wildcard:
            return clingo.ast.Variable(_loc, "_")
        return clingo.ast.Variable(_loc, self.name)

    # end region


PrimitiveSubrelation: TypeAlias = int | str | Variable
"""Type alias for subrelations, that are not self-referential.

Primitive subrelations cannot contain other relations. They are either integers, strings, or variables.

See Also:
    :class:`Relation`

"""


class Signature(NamedTuple):
    """Representation of a signature.

    This is a named tuple, therefore it can be used like a tuple.

    """

    name: str | None
    """Name of the relation."""
    arity: int
    """Arity of the relation."""


_SubargumentsSignature: TypeAlias = Tuple[str | None, Tuple[Union[int, str, None, "_SubargumentsSignature"], ...]]

ArgumentsSignature: TypeAlias = Tuple[int | str | None | _SubargumentsSignature, ...]


@dataclass(frozen=True)
class Relation:
    """Representation of a relation.

    Sometimes also called "atom".

    Relations are the basic building blocks of GDL. They are self-referential --- they can contain other relations as
    arguments.

    """

    # region Attributes and Properties
    name: str | None = None
    "Name of the relation. If None, the relation is an atom."
    arguments: Sequence[Self | PrimitiveSubrelation] = field(default_factory=tuple)
    "Arguments of the relation."

    @property
    def arity(self) -> int:
        """Arity of the relation."""
        return len(self.arguments)

    @property
    def signature(self) -> Signature:
        """Signature of the relation as tuple."""
        return Signature(self.name, self.arity)

    @property
    def arguments_signature(self) -> ArgumentsSignature:
        """Signature of the arguments of the relation as tuple.

        Gives a tuple of the arguments, where variables are replaced by None. This is useful for checking if the head of
        a sentence is applicable for a given relation. Inner relations are expanded into a 2-tuple with the name and the

        Returns:
            A tuple of the arguments, where variables are replaced by None.

        Examples:
            >>> Relation(name="test", arguments=(1, 2)).arguments_signature
            (1, 2)
            >>> Relation(name="test", arguments=()).arguments_signature
            ()
            >>> Relation(name="test", arguments=(1, 2, Variable("X"))).arguments_signature
            (1, 2, None)
            >>> inner = Relation(name="inner")
            >>> inner.arguments_signature
            ()
            >>> outer = Relation(name="outer", arguments=(1, inner))
            >>> outer.arguments_signature
            (1, ('inner', ()))
            >>> inner = Relation(name="inner", arguments=(Variable("X"), 2))
            >>> inner.arguments_signature
            (None, 2)
            >>> outer = Relation(name="outer", arguments=(1, inner))
            >>> outer.arguments_signature
            (1, ('inner', (None, 2)))

        """
        arguments_signature: MutableSequence[int | str | None | _SubargumentsSignature] = []
        for argument in self.arguments:
            if isinstance(argument, Relation):
                arguments_signature.append((argument.name, argument.arguments_signature))
            elif isinstance(argument, Variable):
                arguments_signature.append(None)
            else:
                assert isinstance(argument, (int, str))
                arguments_signature.append(argument)
        return tuple(arguments_signature)

    @property
    def infix_str(self) -> str:
        """String representation of the relation in infix notation.

        Returns:
            The relation as string in infix notation.

        Examples:
            >>> Relation(name="test").infix_str
            'test'
            >>> Relation().infix_str
            '()'
            >>> Relation(arguments=(1, 2)).infix_str
            '(1, 2)'
            >>> Relation(name="test", arguments=(1, 2)).infix_str
            'test(1, 2)'
            >>> Relation(name="test", arguments=(1, Variable("X"))).infix_str
            'test(1, X)'
            >>> Relation(name="outer", arguments=(1, Relation(name="inner", arguments=(2,)))).infix_str
            'outer(1, inner(2))'
            >>> Relation(name="test", arguments=(Variable("_Wildcard"),)).infix_str
            'test(_Wildcard)'

        """
        if self.name is None:
            return f"({', '.join(Relation.to_infix_str(arg) for arg in self.arguments)})"
        if self.arity == 0:
            return self.name
        return f"{self.name}({', '.join(Relation.to_infix_str(arg) for arg in self.arguments)})"

    # endregion

    # region Magic Methods

    def __str__(self) -> str:
        """String representation of the relation in infix notation.

        Returns:
            The relation as string in infix notation.

        See Also:
            :attr:`infix_str`

        """
        return self.infix_str

    # endregion

    # region Methods

    def match(self, name: str | None = None, arity: int = 0) -> bool:
        """Check if the relation matches the given signature.

        Args:
            name: The name of the signature.
            arity: The arity of the signature.

        Returns:
            True if the relation matches the given signature exactly, False otherwise.

        """
        return name == self.name and arity == self.arity

    def to_clingo_ast(self) -> clingo.ast.AST:
        arguments = []
        for argument in self.arguments:
            match argument:
                case int():
                    arguments.append(clingo.ast.SymbolicTerm(_loc, clingo.Number(argument)))
                case str():
                    arguments.append(clingo.ast.SymbolicTerm(_loc, clingo.String(argument)))
                case Variable() | Relation():
                    arguments.append(argument.to_clingo_ast())
                case _:
                    raise TypeError(f"Invalid argument type: {type(argument).__name__}")
        if self.name is None:
            name = ""
        else:
            name = self.name
        return clingo.ast.Function(_loc, name, arguments, False)

    # endregion

    # region Alternative Constructors
    @classmethod
    def role(cls, role: Self | PrimitiveSubrelation) -> Self:
        """Create a `role` relation.

        Returns a relation with the name `role` and the given argument.

        Args:
            role: The role.

        Returns:
            A `role` relation.

        """
        return cls(name="role", arguments=(role,))

    @classmethod
    def init(cls, atom: Self) -> Self:
        """Create an `init` relation.

        Returns a relation with the name `init` and the given argument. Init relations are used to represent the initial
        state.

        Args:
            atom: A relation.

        Returns:
            An `init` relation.

        """
        return cls(name="init", arguments=(atom,))

    @classmethod
    def control(cls, role: Self | PrimitiveSubrelation) -> Self:
        """Create a `control` relation.

        Returns a relation with the name `control` and the given argument. Control relations signal which role is
        required to make a move in this turn. Usually argument of either `init/1`, `true/1`, or `next/1`.

        Args:
            role: The role.

        Returns:
            A `control` relation.

        """
        return cls(name="control", arguments=(role,))

    @classmethod
    def true(cls, atom: Self) -> Self:
        """Create a `true` relation.

        Returns a relation with the name `true` and the given argument. True relations are used to represent the current
        state.

        Args:
            atom: A relation.

        Returns:
            A `true` relation.

        """
        return cls(name="true", arguments=(atom,))

    @classmethod
    def next(cls, atom: Self) -> Self:
        """Create a `next` relation.

        Returns a relation with the name `next` and the given argument. Next relations are used to represent the next
        state.

        Args:
            atom: A relation.

        Returns:
            A `next` relation.

        """
        return cls(name="next", arguments=(atom,))

    @classmethod
    def does(cls, role: Self | PrimitiveSubrelation, move: Self | PrimitiveSubrelation) -> Self:
        """Create a `does` relation.

        Returns a relation with the name `does` and the given arguments. Does relations are used to represent moves.
        `does` relations are also called "plays".

        Args:
            role: The role.
            move: The move.

        Returns:
            A `does` relation.

        """
        return cls(name="does", arguments=(role, move))

    @classmethod
    def distinct(cls, arg1: Self | PrimitiveSubrelation, arg2: Self | PrimitiveSubrelation) -> Self:
        """Create a `distinct` relation.

        Returns a relation with the name `distinct` and the given arguments. Distinct relations are used to represent
        that two arguments are symbolically different.

        Args:
            arg1: The first argument.
            arg2: The second argument.

        Returns:
            A `distinct` relation.

        """
        return cls(name="distinct", arguments=(arg1, arg2))

    @classmethod
    def legal(cls, role: Self | PrimitiveSubrelation, move: Self | PrimitiveSubrelation) -> Self:
        """Create a `legal` relation.

        Returns a relation with the name `legal` and the given arguments. Legal relations are used to represent that a
        move is legal.

        Args:
            role: The role.
            move: The move.

        Returns:
            A `legal` relation.

        """
        return cls(name="legal", arguments=(role, move))

    @classmethod
    def goal(cls, role: Self | PrimitiveSubrelation, utility: int) -> Self:
        """Create a `goal` relation.

        Returns a relation with the name `goal` and the given arguments. Goal relations are used to represent the
        utility value respect to a role.

        Args:
            role: The role.
            utility: The utility.

        Returns:
            A `goal` relation.

        """
        return cls(name="goal", arguments=(role, utility))

    @classmethod
    def terminal(cls) -> Self:
        """Create a `terminal` relation.

        Returns a relation with the name `terminal` and no arguments. Terminal relations are used to represent that the
        state is terminal.

        Returns:
            A `terminal` relation.

        """
        return cls(name="terminal", arguments=())

    # pylint: disable=invalid-name
    @classmethod
    def gt(cls, arg1: Self | PrimitiveSubrelation, arg2: Self | PrimitiveSubrelation) -> Self:
        """Create a `gt` relation.

        Returns a relation with the name `gt` and the given arguments. Gt relations are used to represent that the first
        argument is greater than the second argument.

        Args:
            arg1: The first argument.
            arg2: The second argument.

        Returns:
            A `gt` relation.

        """
        return cls(name="gt", arguments=(arg1, arg2))

    @classmethod
    def plus(
        cls,
        summand1: Self | PrimitiveSubrelation,
        summand2: Self | PrimitiveSubrelation,
        sum_: Self | PrimitiveSubrelation,
    ) -> Self:
        """Create a `plus` relation.

        Returns a relation with the name `plus` and the given arguments. Plus relations are used to represent the
        addition of two arguments.

        Args:
            summand1: The first summand.
            summand2: The second summand.
            sum_: The sum.

        Returns:
            A `plus` relation.

        """
        return cls(name="plus", arguments=(summand1, summand2, sum_))

    # endregion

    # region Static Methods
    @staticmethod
    def to_infix_str(arg: Union["Relation", PrimitiveSubrelation]) -> str:
        """Convert a subrelation to an infix string.

        Args:
            arg: The relation.

        Returns:
            The infix string.

        Raises:
            TypeError: The argument is not a relation or a primitive subrelation.

        Examples:
            >>> Relation.to_infix_str(1)
            '1'
            >>> Relation.to_infix_str(Variable("X"))
            'X'
            >>> Relation.to_infix_str("s")
            's'
            >>> Relation.to_infix_str(Relation("test",))
            'test'
            >>> Relation.to_infix_str(Relation("test", (1,)))
            'test(1)'

        See Also:
            :class:`Subrelation`
            :fun:`Relation.to_infix_str`

        """
        match arg:
            case str():
                return arg
            case int():
                return str(arg)
            case Variable() | Relation():
                return arg.infix_str
            case _:
                raise TypeError(f"Cannot convert {arg} to infix string.")

    # endregion


def argument_signatures_match(argument_signature1: ArgumentsSignature, argument_signature2: ArgumentsSignature) -> bool:
    """Check if the argument signatures match.

    Two argument signatures match if they match exactly or if they differ, None is at least in one of the differing
    positions.

    Args:
        argument_signature1: The first argument signature.
        argument_signature2: The second argument signature.

    Returns:
        True if the argument signatures match, False otherwise.

    Examples:
        >>> argument_signatures_match((1, 2), (1, 2))
        True
        >>> argument_signatures_match((1, 2), (1, None))
        True
        >>> argument_signatures_match((1, 3), (1, 2))
        False
        >>> argument_signatures_match((1,), (1, 2))
        False
        >>> argument_signatures_match((1, 2), (2, None))
        False

    """
    if argument_signature1 == argument_signature2:
        return True
    if len(argument_signature1) != len(argument_signature2):
        return False
    for argument1, argument2 in zip(argument_signature1, argument_signature2):
        if argument1 != argument2 and argument1 is not None and argument2 is not None:
            return False
    return True


Subrelation: TypeAlias = Relation | PrimitiveSubrelation
"""Type alias for subrelations.

Either a relation or a primitive subrelation.

See Also:
    :class:`Relation`
    :class:`PrimitiveSubrelation`

"""
Role: TypeAlias = Subrelation
"""Role played in a game.

A role is a subrelation. It is the argument of the `role/1` relation and the first argument of the `does/2` and
`legal/2` relations.

"""
Move: TypeAlias = Subrelation
"""Move made in a game.

A move is a subrelation. It is the second argument of the `does/2` and `legal/2` relations.

"""
Play: TypeAlias = Relation
"""Play made in a game.

Plays are relations. They are `does/2` relations.

"""
State: TypeAlias = FrozenSet[Relation]
"""State of a game."""

PlayRecord: TypeAlias = Mapping[int, FrozenSet[Play]]
"""Record of plays made in each round."""
MutablePlayRecord = MutableMapping[int, Set[Play]]
"""Mutable record of plays made in each round."""


class Sign(IntEnum):
    """Sign of a literal."""

    NOSIGN = auto()
    "No sign, corresponds to `atom`."
    NEGATIVE = auto()
    "Negative, corresponds to `not atom`."


@dataclass(frozen=True)
class Literal:
    """Representation of a literal."""

    # region Attributes and Properties

    atom: Relation
    "Atom of the literal."
    sign: Sign = Sign.NOSIGN
    "Sign of the literal."

    @property
    def infix_str(self) -> str:
        """Infix string representation of the literal.

        Returns:
            The infix string representation.

        Examples:
            >>> Literal(atom=Relation(name="atom")).infix_str
            'atom'
            >>> (-Literal(atom=Relation(name="atom"))).infix_str
            'not atom'

        """
        if self.sign == Sign.NOSIGN:
            return self.atom.infix_str
        return f"not {self.atom.infix_str}"

    # endregion

    # region Magic Methods

    def __neg__(self) -> Self:
        """Negate the literal.

        Returns a literal with the same atom and the opposite sign.

        Returns:
            The negated literal.

        Examples:
            >>> atom = Literal(atom=Relation(name="atom"))
            >>> atom
            Literal(atom=Relation(name='atom', arguments=()), sign=<Sign.NOSIGN: 1>)
            >>> -atom
            Literal(atom=Relation(name='atom', arguments=()), sign=<Sign.NEGATIVE: 2>)
            >>> -(-atom)
            Literal(atom=Relation(name='atom', arguments=()), sign=<Sign.NOSIGN: 1>)

        """
        cls: Type[Self] = self.__class__
        return cls(atom=self.atom, sign=Sign.NEGATIVE if self.sign == Sign.NOSIGN else Sign.NOSIGN)

    def __str__(self):
        """String representation of the literal.

        Returns the infix representation of the literal.

        Returns:
            The string representation of the literal.

        """
        return self.infix_str

    # endregion

    # region Methods

    def to_clingo_ast(self) -> clingo.ast.AST:
        match self.sign:
            case Sign.NOSIGN:
                sign = clingo.ast.Sign.NoSign
                comparison = clingo.ast.ComparisonOperator.NotEqual
            case Sign.NEGATIVE:
                sign = clingo.ast.Sign.Negation
                comparison = clingo.ast.ComparisonOperator.Equal
            case _:
                raise TypeError(f"Invalid sign {self.sign}.")
        if self.atom.match("distinct", 2):
            term = self.atom.to_clingo_ast()
            arguments = term.arguments
            left = arguments[0]
            right = arguments[1]
            return clingo.ast.Literal(
                _loc,
                sign=clingo.ast.Sign.NoSign,
                atom=clingo.ast.Comparison(left, (clingo.ast.Guard(comparison, right),)),
            )

        return clingo.ast.Literal(_loc, sign=sign, atom=clingo.ast.SymbolicAtom(self.atom.to_clingo_ast()))

    # endregion


@dataclass(frozen=True)
class Sentence:
    """Representation of a sentence.

    Sentences are also called rules. They are used to represent facts (without body) and (proper) rules (with body).

    """

    # region Attributes and Properties

    head: Relation
    """Head of the sentence."""
    body: Sequence[Literal] = field(default_factory=tuple)
    """Body of the sentence."""

    # endregion

    # region Magic Methods

    def __str__(self) -> str:
        """String representation of the sentence.

        Returns the infix representation of the sentence, using `:-` as implication symbol.

        Returns:
            The string representation of the sentence.

        """
        return self.to_infix_str()

    # endregion

    # region Methods

    def to_infix_str(self, implies_symbol: str = ":-") -> str:
        """Convert the sentence to an infix string.

        Converts the sentence to a string representation in infix notation.

        Args:
            implies_symbol: The symbol to use to show implication. Default: `:-`.

        Returns:
            The infix string representation of the sentence.

        Examples:
            >>> fact = Sentence.fact(head=Relation(name="fact"))
            >>> fact.to_infix_str()
            'fact.'
            >>> head = Relation(name="rule")
            >>> pos_atom = Relation(name="pos_atom")
            >>> rule = Sentence.rule(head=head, body=(Literal(atom=pos_atom),))
            >>> rule.to_infix_str()
            'rule :- pos_atom.'
            >>> neg_atom = Relation(name="neg_atom")
            >>> body = (Literal(atom=pos_atom), -Literal(atom=neg_atom))
            >>> rule = Sentence.rule(head=head, body=body)
            >>> rule.to_infix_str()
            'rule :- pos_atom, not neg_atom.'
            >>> body = (Literal(atom=pos_atom), -Literal(atom=neg_atom), Literal(atom=pos_atom))
            >>> rule = Sentence.rule(head=head, body=body)
            >>> rule.to_infix_str()
            'rule :- pos_atom, not neg_atom, pos_atom.'

        """
        if self.body:
            return f"{self.head.infix_str} {implies_symbol} {', '.join(literal.infix_str for literal in self.body)}."
        return f"{self.head.infix_str}."

    def to_clingo_ast(self) -> clingo.ast.AST:
        return clingo.ast.Rule(
            _loc,
            head=clingo.ast.Literal(
                _loc, sign=clingo.ast.Sign.NoSign, atom=clingo.ast.SymbolicAtom(self.head.to_clingo_ast())
            ),
            body=tuple(literal.to_clingo_ast() for literal in self.body),
        )

    # endregion

    # region Alternative Constructors

    @classmethod
    def fact(cls, head: Relation) -> Self:
        """Create a fact.

        Returns a sentence with the given head and without body.

        Args:
            head: An atom.

        Returns:
            A fact.

        """
        return cls(head=head, body=())

    @classmethod
    def rule(cls, head: Relation, body: Sequence[Literal]) -> Self:
        """Create a rule.

        Returns a sentence with the given head and body.

        Args:
            head: An atom.
            body: A sequence of literals.

        Returns:
            A rule.

        """
        return cls(head=head, body=body)

    # endregion


_RuleSignatureMutableMapping: TypeAlias = MutableMapping[
    Tuple[str | None, int], MutableMapping[ArgumentsSignature, Set[Sentence]]
]


@dataclass(frozen=True)
class Ruleset:
    """Representation of a ruleset.

    Rulesets are an ordered collection of sentences. Rulesets are used to represent games in GDL.

    """

    # region Attributes and Properties

    rules: Sequence[Sentence]
    """Rules of the ruleset.

    Despite the name, this is not actually a set, as the order of the rules is important.

    """
    _rules_by_head_signature: _RuleSignatureMutableMapping = field(init=False, default_factory=dict)

    @property
    def role_rules(self) -> Sequence[Sentence]:
        """Rules used to define the roles.

        Gather all sentences whose head matches the signature `role/1`, and each required sentence who's head appears in
        the body of the returned sentences.

        Returns:
            A sequence of sentences, which heads are related to `role/1`. Sorted by the order of appearance.

        """
        role_rules = self._get_related_rules_by_signature(name="role", arity=1)
        return sorted(role_rules, key=self.rules.index)

    @property
    def init_rules(self) -> Sequence[Sentence]:
        """Rules used to define the initial state.

        Gather all sentences whose head matches the signature `init/1`, and each required sentence who's head appears in
        the body of the returned sentences.

        Returns:
            A sequence of sentences, which heads are related to `init/1`. Sorted by the order of appearance.

        """
        init_rules = self._get_related_rules_by_signature(name="init", arity=1)
        return sorted(init_rules, key=self.rules.index)

    @property
    def next_rules(self) -> Sequence[Sentence]:
        """Rules used to define the next state.

        Gather all sentences whose head matches the signature `next/1`, and each required sentence who's head appears in
        the body of the returned sentences.

        Returns:
            A sequence of sentences, which heads are related to `next/1`. Sorted by the order of appearance.

        """
        next_rules = self._get_related_rules_by_signature(name="next", arity=1)
        return sorted(next_rules, key=self.rules.index)

    @property
    def sees_rules(self) -> Sequence[Sentence]:
        """Rules used to define which role sees which fluents.

        Gather all sentences whose head matches the signature `sees/2`, and each required sentence who's head appears in
        the body of the returned sentences.

        Returns:
            A sequence of sentences, which heads are related to `sees/2`. Sorted by the order of appearance.

        """
        sees_rules = self._get_related_rules_by_signature(name="sees", arity=2)
        return sorted(sees_rules, key=self.rules.index)

    @property
    def legal_rules(self) -> Sequence[Sentence]:
        """Rules used to define the legal moves.

        Gather all sentences whose head matches the signature `legal/2`, and each required sentence who's head appears
        in the body of the returned sentences.

        Returns:
            A sequence of sentences, which heads are related to `legal/2`. Sorted by the order of appearance.

        """
        legal_rules = self._get_related_rules_by_signature(name="legal", arity=2)
        return sorted(legal_rules, key=self.rules.index)

    @property
    def goal_rules(self) -> Sequence[Sentence]:
        """Rules used to define the utility of each role.

        Gather all sentences whose head matches the signature `goal/2`, and each required sentence who's head appears in
        the body of the returned sentences.

        Returns:
            A sequence of sentences, which heads are related to `goal/2`. Sorted by the order of appearance.

        """
        goal_rules = self._get_related_rules_by_signature(name="goal", arity=2)
        return sorted(goal_rules, key=self.rules.index)

    @property
    def terminal_rules(self) -> Sequence[Sentence]:
        """Rules used to define if a state is terminal.

        Gather all sentences whose head matches the signature `terminal/0`, and each required sentence who's head
        appears in the body of the returned sentences.

        Returns:
            A sequence of sentences, which heads are related to `terminal/0`. Sorted by the order of appearance.

        """
        terminal_rules = self._get_related_rules_by_signature(name="terminal", arity=0)
        return sorted(terminal_rules, key=self.rules.index)

    # endregion

    # region Magic Methods

    def __post_init__(self) -> None:
        """Store rules in map by head signature."""
        for rule in self.rules:
            signature = rule.head.signature
            arguments_signature = rule.head.arguments_signature
            self._rules_by_head_signature.setdefault(signature, {}).setdefault(arguments_signature, set()).add(rule)

    # endregion

    # region Methods

    def _get_related_rules_by_relation(self, relation: Relation) -> set[Sentence]:
        signature = relation.signature
        arguments_signature = relation.arguments_signature
        related_rules = set()
        for arguments_signature_, rules in self._rules_by_head_signature.get(signature, {}).items():
            if argument_signatures_match(arguments_signature, arguments_signature_):
                related_rules.update(rules)
        return related_rules

    def _get_root_rules_by_signature(self, name: str | None = None, arity: int = 0) -> set[Sentence]:
        rules = self._rules_by_head_signature.get((name, arity), {})
        return set.union(*rules.values(), set())

    def _get_related_rules_by_signature(self, name: str | None = None, arity: int = 0) -> set[Sentence]:
        related_rules = set(self._get_root_rules_by_signature(name=name, arity=arity))
        changed = True
        while changed:
            size = len(related_rules)
            associated_rules = set()
            for rule in related_rules:
                for literal in rule.body:
                    associated_rules.update(self._get_related_rules_by_relation(literal.atom))
            related_rules.update(associated_rules)
            changed = len(related_rules) != size
        return related_rules

    # endregion
