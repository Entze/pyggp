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
    sentence: head ":-"? "."                          -> fact
            | head ":-" body "."  -> rule
    ?head: relation
    body: _seperated{literal, ","}
    literal: sign? term
    ?term: relation
    sign: "not"  -> not
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

parser = lark.Lark(grammar=infix_grammar, start="ruleset")
ruleset_parser = parser
subrelation_parser = lark.Lark(grammar=infix_grammar, start="subrelation")


class TreeToGDLTransformer(lark.Transformer[lark.Token, GDL]):
    """Transforms a tree to the corresponding gdl object."""

    def ruleset(self, children: Sequence[Sentence]) -> Ruleset:  # noqa: D102
        return Ruleset.from_rules(children)

    def rule(self, children: Tuple[Relation, Sequence[Literal]]) -> Sentence:  # noqa: D102
        head, body = children
        return Sentence(head, tuple(body))

    def body(self, children: Sequence[Literal]) -> Sequence[Literal]:  # noqa: D102
        return children

    def fact(self, children: Sequence[Relation]) -> Sentence:  # noqa: D102
        (head,) = children
        return Sentence(head)

    def literal(self, children: Union[Tuple[lark.Token, Relation], Tuple[Relation]]) -> Literal:  # noqa: D102
        # Disables PLR2004. Because: Not a magic value, but either a tuple of one or two elements.
        if len(children) == 2:  # noqa: PLR2004
            # Disables mypy. Because: False positive
            (_sign, relation) = children  # type: ignore[misc]
            return Literal(relation, Literal.Sign.NEGATIVE)
        # Disables mypy. Because: False positive
        (relation,) = children  # type: ignore[misc]
        return Literal(relation)

    def tuple_(self, children: Sequence[Iterable[Subrelation]]) -> Relation:  # noqa: D102
        (arguments,) = children
        return Relation(arguments=tuple(arguments))

    def empty_tuple(self, children: Sequence[Any]) -> Relation:  # noqa: D102, ARG002
        return Relation()

    def function(self, children: Tuple[lark.Token, Iterable[Subrelation]]) -> Relation:  # noqa: D102
        name, arguments = children
        return Relation(str(name), tuple(arguments))

    def arguments(self, children: Sequence[Subrelation]) -> Sequence[Subrelation]:  # noqa: D102
        return children

    def subrelation(self, children: Sequence[Symbol]) -> Subrelation:  # noqa: D102
        (symbol,) = children
        return Subrelation(symbol)

    def atom(self, children: Sequence[lark.Token]) -> Relation:  # noqa: D102
        (name,) = children
        return Relation(str(name))

    def string(self, children: Sequence[lark.Token]) -> String:  # noqa: D102
        (escaped_string,) = children
        return String(str(escaped_string[1:-1]))

    def number(self, children: Sequence[lark.Token]) -> Number:  # noqa: D102
        (number,) = children
        return Number(int(number))

    def variable(self, children: Sequence[lark.Token]) -> Variable:  # noqa: D102
        (varname,) = children
        return Variable(str(varname))

    def anonymous_wildcard(self, children: Sequence[Any]) -> Variable:  # noqa: D102, ARG002
        return Variable("_")

    def named_wildcard(self, children: Sequence[lark.Token]) -> Variable:  # noqa: D102
        (varname,) = children
        return Variable("_" + str(varname))


transformer = TreeToGDLTransformer()
