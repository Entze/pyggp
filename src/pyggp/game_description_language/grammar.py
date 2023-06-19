"""Parsing GDL.

Defines a parser and a transformer to get rulesets from strings.

Examples:
    >>> import pyggp.game_description_language as gdl
    >>> tree = gdl.parser.parse("a :- b.")
    >>> ruleset = gdl.transformer.transform(tree)

"""
from typing import Any, Iterable, Sequence, Tuple, Union

import lark

from pyggp.game_description_language.literals import Literal
from pyggp.game_description_language.rulesets import Ruleset
from pyggp.game_description_language.sentences import Sentence
from pyggp.game_description_language.subrelations import (
    Number,
    Relation,
    String,
    Subrelation,
    Symbol,
    Variable,
)

infix_grammar = r"""
    ruleset: (sentence)*
    sentence: head ":-"? "."      -> fact
            | head ":-" body "."  -> rule
    ?head: relation
    body: _seperated{literal, ","}
    literal: sign? term
    sign: "not"  -> not
    ?term: relation | comparison
    ?comparison.1: not_equal
    not_equal: "distinct" "(" arguments ")"
    relation: name ("(" ")")?         -> atom
            | name "(" arguments ")"  -> function
            | "(" ")"                 -> empty_tuple
            | "(" arguments ")"       -> tuple_
    ?name: ATOMNAME
    arguments: _seperated{argument, ","}
    ?argument: subrelation
    subrelation: relation | primitive
    ?primitive: number | string | variable
    number: INT | SIGNED_INT
    string: ESCAPED_STRING
    variable: "_"          -> anonymous_wildcard
            | "_" VARNAME  -> named_wildcard
            | VARNAME

    ATOMNAME: "_"* LCASE_LETTER (LETTER | DIGIT | "_")*
    VARNAME: UCASE_LETTER (LETTER | DIGIT | "_")*

    _seperated{x, sep}: x (sep x)*

    %import common (INT, SIGNED_INT, ESCAPED_STRING, UCASE_LETTER, LCASE_LETTER, LETTER, DIGIT, WS)
    %ignore WS

    """

GDL = Union[Relation, String, Number, Variable, Subrelation, Literal, Ruleset]

parser = lark.Lark(grammar=infix_grammar, start="ruleset", parser="lalr")
ruleset_parser = parser
subrelation_parser = lark.Lark(grammar=infix_grammar, start="subrelation", parser="lalr")


class TreeToGDLTransformer(lark.Transformer[lark.Token, GDL]):
    """Transforms a tree to the corresponding gdl object."""

    def ruleset(self, children: Sequence[Sentence]) -> Ruleset:
        return Ruleset.from_rules(children)

    def rule(self, children: Tuple[Relation, Sequence[Literal]]) -> Sentence:
        head, body = children
        return Sentence(head, tuple(body))

    def body(self, children: Sequence[Literal]) -> Sequence[Literal]:
        return children

    def fact(self, children: Sequence[Relation]) -> Sentence:
        (head,) = children
        return Sentence(head)

    def literal(self, children: Union[Tuple[lark.Token, Relation], Tuple[Relation]]) -> Literal:
        # Disables PLR2004. Because: Not a magic value, but either a tuple of one or two elements.
        if len(children) == 2:  # noqa: PLR2004
            # Disables mypy. Because: False positive
            (_sign, relation) = children  # type: ignore[misc]
            return Literal(relation, Literal.Sign.NEGATIVE)
        # Disables mypy. Because: False positive
        (relation,) = children  # type: ignore[misc]
        return Literal(relation)

    def not_equal(self, children: Sequence[Iterable[Subrelation]]) -> Relation:
        (arguments,) = children
        return Relation("__comp_not_equal", tuple(arguments))

    def tuple_(self, children: Sequence[Iterable[Subrelation]]) -> Relation:
        (arguments,) = children
        return Relation(arguments=tuple(arguments))

    def empty_tuple(self, children: Sequence[Any]) -> Relation:  # noqa: ARG002
        return Relation()

    def function(self, children: Tuple[lark.Token, Iterable[Subrelation]]) -> Relation:
        name, arguments = children
        return Relation(str(name), tuple(arguments))

    def arguments(self, children: Sequence[Subrelation]) -> Sequence[Subrelation]:
        return children

    def subrelation(self, children: Sequence[Symbol]) -> Subrelation:
        (symbol,) = children
        return Subrelation(symbol)

    def atom(self, children: Sequence[lark.Token]) -> Relation:
        (name,) = children
        return Relation(str(name))

    def string(self, children: Sequence[lark.Token]) -> String:
        (escaped_string,) = children
        return String(str(escaped_string[1:-1]))

    def number(self, children: Sequence[lark.Token]) -> Number:
        (number,) = children
        return Number(int(number))

    def variable(self, children: Sequence[lark.Token]) -> Variable:
        (varname,) = children
        return Variable(str(varname))

    def anonymous_wildcard(self, children: Sequence[Any]) -> Variable:  # noqa: ARG002
        return Variable("_")

    def named_wildcard(self, children: Sequence[lark.Token]) -> Variable:
        (varname,) = children
        return Variable("_" + str(varname))


transformer = TreeToGDLTransformer()


def parse(string: str) -> Ruleset:
    """Parse a string into a ruleset.

    Args:
        string: string to parse

    Returns:
        Ruleset representing string

    """
    tree = parser.parse(string)
    return transformer.transform(tree)
