# pylint: disable=missing-docstring,invalid-name,unused-argument
import unittest
from unittest import TestCase

import clingo.ast
import pytest

from pyggp.games import rock_paper_scissors_ruleset, tic_tac_toe_ruleset
from pyggp.gdl import (
    Literal,
    Relation,
    Sentence,
    Sign,
    Subrelation,
    Variable,
    argument_signatures_match,
    from_clingo_symbol,
)

_pos = clingo.ast.Position("<string>", 0, 0)
_loc = clingo.ast.Location(_pos, _pos)


class TestVariable__str__(TestCase):
    def test_var(self) -> None:
        variable = Variable("X")
        actual = str(variable)
        expected = "X"
        self.assertEqual(actual, expected)

    def test_wildcard(self) -> None:
        variable = Variable("_")
        actual = str(variable)
        expected = "_"
        self.assertEqual(actual, expected)

    def test_named_wildcard(self) -> None:
        variable = Variable("_X")
        actual = str(variable)
        expected = "_X"
        self.assertEqual(actual, expected)


class TestVariableToClingoAST(TestCase):
    def test_var(self) -> None:
        variable = Variable("X")
        actual = variable.to_clingo_ast()
        expected = clingo.ast.Variable(_loc, "X")
        self.assertEqual(actual, expected)

    def test_wildcard(self) -> None:
        variable = Variable("_")
        actual = variable.to_clingo_ast()
        expected = clingo.ast.Variable(_loc, "_")
        self.assertEqual(actual, expected)

    def test_named_wildcard(self) -> None:
        variable = Variable("_X")
        actual = variable.to_clingo_ast()
        expected = clingo.ast.Variable(_loc, "_")
        self.assertEqual(actual, expected)


class TestRelation__str__(TestCase):
    def test_atom(self) -> None:
        relation = Relation("test", ())
        actual = str(relation)
        expected = "test"
        self.assertEqual(actual, expected)

    def test_empty_tuple(self) -> None:
        relation = Relation()
        actual = str(relation)
        expected = "()"
        self.assertEqual(actual, expected)

    def test_2tuple(self) -> None:
        relation = Relation(arguments=(1, 2))
        actual = str(relation)
        expected = "(1, 2)"
        self.assertEqual(actual, expected)

    def test_nested(self) -> None:
        relation = Relation(name="outer", arguments=(1, Relation("test", ())))
        actual = str(relation)
        expected = "outer(1, test)"
        self.assertEqual(actual, expected)


class TestRelationMatch(unittest.TestCase):
    def test_atom(self) -> None:
        relation = Relation("test", ())
        actual = relation.match("test", 0)
        expected = True
        self.assertEqual(actual, expected)

    def test_empty_tuple(self) -> None:
        relation = Relation()
        actual = relation.match()
        expected = True
        self.assertEqual(actual, expected)

    def test_2tuple(self) -> None:
        relation = Relation(arguments=(1, 2))
        actual = relation.match(arity=2)
        expected = True
        self.assertEqual(actual, expected)

    def test_wrong_arity(self) -> None:
        relation = Relation("test", ())
        actual = relation.match("test", 1)
        expected = False
        self.assertEqual(actual, expected)

    def test_wrong_name(self) -> None:
        relation = Relation("test", (1, 2))
        actual = relation.match("different", 2)
        expected = False
        self.assertEqual(actual, expected)


class TestRelationArgumentsSignature(unittest.TestCase):
    def test_atom(self) -> None:
        relation = Relation("test", ())
        actual = relation.arguments_signature
        expected = ()
        self.assertEqual(actual, expected)

    def test_2tuple(self) -> None:
        relation = Relation(arguments=(1, 2))
        actual = relation.arguments_signature
        expected = (1, 2)
        self.assertEqual(actual, expected)

    def test_nested(self) -> None:
        relation = Relation(name="outer", arguments=(1, Relation("test", ())))
        actual = relation.arguments_signature
        expected = (1, ("test", ()))
        self.assertEqual(actual, expected)

    def test_variable(self) -> None:
        relation = Relation(name="test", arguments=(1, Variable("X")))
        actual = relation.arguments_signature
        expected = (1, None)
        self.assertEqual(actual, expected)

    def test_nested_variable(self) -> None:
        relation = Relation(name="outer", arguments=(1, Relation("test", (Variable("X"), 2))))
        actual = relation.arguments_signature
        expected = (1, ("test", (None, 2)))
        self.assertEqual(actual, expected)


class TestRelationInfixStr(unittest.TestCase):
    def test_atom(self) -> None:
        relation = Relation("test", ())
        actual = relation.infix_str
        expected = "test"
        self.assertEqual(actual, expected)

    def test_empty_tuple(self) -> None:
        relation = Relation()
        actual = relation.infix_str
        expected = "()"
        self.assertEqual(actual, expected)

    def test_2tuple(self) -> None:
        relation = Relation(arguments=(1, 2))
        actual = relation.infix_str
        expected = "(1, 2)"
        self.assertEqual(actual, expected)

    def test_relation_depth1(self) -> None:
        relation = Relation(name="outer", arguments=(1,))
        actual = relation.infix_str
        expected = "outer(1)"
        self.assertEqual(actual, expected)

    def test_relation_depth2(self) -> None:
        relation = Relation(name="outer", arguments=(1, Relation("inner", ())))
        actual = relation.infix_str
        expected = "outer(1, inner)"
        self.assertEqual(actual, expected)

    def test_relation_variable(self) -> None:
        relation = Relation(name="outer", arguments=(1, Variable("X")))
        actual = relation.infix_str
        expected = "outer(1, X)"
        self.assertEqual(actual, expected)

    def test_relation_wildcard(self) -> None:
        relation = Relation(name="outer", arguments=(1, Variable("_Wildcard")))
        actual = relation.infix_str
        expected = "outer(1, _Wildcard)"
        self.assertEqual(actual, expected)


class TestRelationToInfixStr(unittest.TestCase):
    def test_int(self) -> None:
        actual = Relation.to_infix_str(1)
        expected = "1"
        self.assertEqual(actual, expected)

    def test_str(self) -> None:
        actual = Relation.to_infix_str("test")
        expected = "test"
        self.assertEqual(actual, expected)

    def test_variable(self) -> None:
        actual = Relation.to_infix_str(Variable("X"))
        expected = "X"
        self.assertEqual(actual, expected)

    def test_wildcard(self) -> None:
        actual = Relation.to_infix_str(Variable("_Wildcard"))
        expected = "_Wildcard"
        self.assertEqual(actual, expected)

    def test_atom(self) -> None:
        relation = Relation("test", ())
        actual = Relation.to_infix_str(relation)
        expected = "test"
        self.assertEqual(actual, expected)

    def test_empty_tuple(self) -> None:
        relation = Relation()
        actual = Relation.to_infix_str(relation)
        expected = "()"
        self.assertEqual(actual, expected)

    def test_2tuple(self) -> None:
        relation = Relation(arguments=(1, 2))
        actual = Relation.to_infix_str(relation)
        expected = "(1, 2)"
        self.assertEqual(actual, expected)

    def test_relation_depth1(self) -> None:
        relation = Relation(name="outer", arguments=(1,))
        actual = Relation.to_infix_str(relation)
        expected = "outer(1)"
        self.assertEqual(actual, expected)

    def test_invalid_type(self) -> None:
        with self.assertRaises(TypeError):
            Relation.to_infix_str(None)


class TestRelationToClingoAST(unittest.TestCase):
    def test_atom(self) -> None:
        relation = Relation("test", ())
        actual = relation.to_clingo_ast()
        expected = clingo.ast.Function(_loc, name="test", arguments=(), external=False)
        self.assertEqual(actual, expected)

    def test_empty_tuple(self) -> None:
        relation = Relation()
        actual = relation.to_clingo_ast()
        expected = clingo.ast.Function(_loc, name="", arguments=(), external=False)
        self.assertEqual(actual, expected)

    def test_nested(self) -> None:
        relation = Relation(name="nested", arguments=(1, "two", Relation("three"), Variable("Four")))
        actual = relation.to_clingo_ast()
        expected = clingo.ast.Function(
            _loc,
            name="nested",
            arguments=(
                clingo.ast.SymbolicTerm(_loc, clingo.Number(1)),
                clingo.ast.SymbolicTerm(_loc, clingo.String("two")),
                clingo.ast.Function(_loc, name="three", arguments=(), external=False),
                clingo.ast.Variable(_loc, name="Four"),
            ),
            external=False,
        )
        self.assertEqual(actual, expected)

    def test_invalid_type(self) -> None:
        with self.assertRaises(TypeError):
            relation = Relation("test", (None,))
            relation.to_clingo_ast()


class TestRelationToClingoSymbol(TestCase):
    def test_atom(self) -> None:
        relation = Relation("test", ())
        actual = relation.to_clingo_symbol()
        expected = clingo.Function("test")
        self.assertEqual(actual, expected)

    def test_empty_tuple(self) -> None:
        relation = Relation()
        actual = relation.to_clingo_symbol()
        expected = clingo.Function("")
        self.assertEqual(actual, expected)

    def test_nested(self) -> None:
        relation = Relation(name="nested", arguments=(1, "two", Relation("three")))
        actual = relation.to_clingo_symbol()
        expected = clingo.Function("nested", [clingo.Number(1), clingo.String("two"), clingo.Function("three")])
        self.assertEqual(actual, expected)

    def test_with_variable(self) -> None:
        relation = Relation(name="nested", arguments=(Variable("x"),))
        with self.assertRaises(ValueError):
            relation.to_clingo_symbol()

    def test_invalid_type(self) -> None:
        relation = Relation("test", (None,))
        with self.assertRaises(TypeError):
            relation.to_clingo_symbol()


class TestArgumentSignaturesMatch(unittest.TestCase):
    def test_same(self) -> None:
        arg_sig1 = (1, 2)
        arg_sig2 = (1, 2)
        actual = argument_signatures_match(arg_sig1, arg_sig2)
        expected = True
        self.assertEqual(actual, expected)

    def test_same_with_var(self) -> None:
        arg_sig1 = (1, 2)
        arg_sig2 = (1, None)
        actual = argument_signatures_match(arg_sig1, arg_sig2)
        expected = True
        self.assertEqual(actual, expected)

    def test_different(self) -> None:
        arg_sig1 = (1, 2)
        arg_sig2 = (2, 1)
        actual = argument_signatures_match(arg_sig1, arg_sig2)
        expected = False
        self.assertEqual(actual, expected)

    def test_different_with_var(self) -> None:
        arg_sig1 = (1, 2)
        arg_sig2 = (2, None)
        actual = argument_signatures_match(arg_sig1, arg_sig2)
        expected = False
        self.assertEqual(actual, expected)

    def test_empty(self) -> None:
        arg_sig1 = ()
        arg_sig2 = ()
        actual = argument_signatures_match(arg_sig1, arg_sig2)
        expected = True
        self.assertEqual(actual, expected)

    def test_different_length(self) -> None:
        arg_sig1 = (1,)
        arg_sig2 = (1, 2)
        actual = argument_signatures_match(arg_sig1, arg_sig2)
        expected = False
        self.assertEqual(actual, expected)


class TestFromClingoSymbol(TestCase):
    def test_atom(self) -> None:
        symbol = clingo.Function("test")
        actual = from_clingo_symbol(symbol)
        expected = Relation("test", ())
        self.assertEqual(actual, expected)

    def test_number(self) -> None:
        symbol = clingo.Number(1)
        actual = from_clingo_symbol(symbol)
        expected = 1
        self.assertEqual(actual, expected)

    def test_string(self) -> None:
        symbol = clingo.String("test")
        actual = from_clingo_symbol(symbol)
        expected = "test"
        self.assertEqual(actual, expected)

    def test_nested(self) -> None:
        symbol = clingo.Function("nested", [clingo.Number(1), clingo.String("two"), clingo.Function("three")])
        actual = from_clingo_symbol(symbol)
        expected = Relation("nested", (1, "two", Relation("three")))
        self.assertEqual(actual, expected)

    def test_empty_tuple(self) -> None:
        symbol = clingo.Function("")
        actual = from_clingo_symbol(symbol)
        expected = Relation()
        self.assertEqual(actual, expected)


class TestLiteralInfixStr(unittest.TestCase):
    def test_posatom(self) -> None:
        relation = Relation("test", ())
        literal = Literal(relation)
        actual = literal.infix_str
        expected = "test"
        self.assertEqual(actual, expected)

    def test_negatom(self) -> None:
        relation = Relation("test", ())
        literal = Literal(relation, sign=Sign.NEGATIVE)
        actual = literal.infix_str
        expected = "not test"
        self.assertEqual(actual, expected)


class TestLiteralToClingoAST(unittest.TestCase):
    def test_posatom(self) -> None:
        relation = Relation("test", ())
        literal = Literal(relation)
        actual = literal.to_clingo_ast()
        expected = clingo.ast.Literal(
            _loc,
            sign=clingo.ast.Sign.NoSign,
            atom=clingo.ast.SymbolicAtom(clingo.ast.Function(_loc, name="test", arguments=(), external=False)),
        )
        self.assertEqual(actual, expected)

    def test_negatom(self) -> None:
        relation = Relation("test", ())
        literal = Literal(relation, sign=Sign.NEGATIVE)
        actual = literal.to_clingo_ast()
        expected = clingo.ast.Literal(
            _loc,
            sign=clingo.ast.Sign.Negation,
            atom=clingo.ast.SymbolicAtom(clingo.ast.Function(_loc, name="test", arguments=(), external=False)),
        )
        self.assertEqual(actual, expected)

    def test_distinct(self) -> None:
        relation = Relation("distinct", (1, 2))
        literal = Literal(relation)
        actual = literal.to_clingo_ast()
        expected = clingo.ast.Literal(
            _loc,
            sign=clingo.ast.Sign.NoSign,
            atom=clingo.ast.Comparison(
                clingo.ast.SymbolicTerm(_loc, clingo.Number(1)),
                (
                    clingo.ast.Guard(
                        clingo.ast.ComparisonOperator.NotEqual, clingo.ast.SymbolicTerm(_loc, clingo.Number(2))
                    ),
                ),
            ),
        )
        self.assertEqual(actual, expected)

    def test_equal(self) -> None:
        relation = Relation("distinct", (1, 2))
        literal = -Literal(relation)
        actual = literal.to_clingo_ast()
        expected = clingo.ast.Literal(
            _loc,
            sign=clingo.ast.Sign.NoSign,
            atom=clingo.ast.Comparison(
                clingo.ast.SymbolicTerm(_loc, clingo.Number(1)),
                (
                    clingo.ast.Guard(
                        clingo.ast.ComparisonOperator.Equal, clingo.ast.SymbolicTerm(_loc, clingo.Number(2))
                    ),
                ),
            ),
        )
        self.assertEqual(actual, expected)

    def test_invalid_type(self) -> None:
        relation = Relation("test")
        literal = Literal(relation, sign=None)
        with self.assertRaises(TypeError):
            literal.to_clingo_ast()


class TestLiteral__neg__(unittest.TestCase):
    def test_atom(self) -> None:
        relation = Literal(Relation("test", ()))
        actual = -relation
        expected = Literal(Relation("test", ()), sign=Sign.NEGATIVE)
        self.assertEqual(actual, expected)


class TestLiteral__str__(unittest.TestCase):
    def test_posatom(self) -> None:
        relation = Relation("test", ())
        literal = Literal(relation)
        actual = str(literal)
        expected = "test"
        self.assertEqual(actual, expected)

    def test_negatom(self) -> None:
        relation = Relation("test", ())
        literal = Literal(relation, sign=Sign.NEGATIVE)
        actual = str(literal)
        expected = "not test"
        self.assertEqual(actual, expected)


class TestSentence__str__(unittest.TestCase):
    # Should be the same as ToInfixStr

    def test_fact(self) -> None:
        sentence = Sentence.fact(Relation("test", ()))
        actual = str(sentence)
        expected = "test."
        self.assertEqual(actual, expected)


class TestSentenceToClingoAST(unittest.TestCase):
    def test_fact(self) -> None:
        sentence = Sentence.fact(Relation("test", ()))
        actual = sentence.to_clingo_ast()
        expected = clingo.ast.Rule(
            _loc,
            head=clingo.ast.Literal(
                _loc,
                sign=clingo.ast.Sign.NoSign,
                atom=clingo.ast.SymbolicAtom(clingo.ast.Function(_loc, name="test", arguments=(), external=False)),
            ),
            body=(),
        )
        self.assertEqual(actual, expected)

    def test_rule_one_pos(self) -> None:
        sentence = Sentence.rule(Relation("test", ()), (Literal(Relation("pos_atom", ())),))
        actual = sentence.to_clingo_ast()
        expected = clingo.ast.Rule(
            _loc,
            head=clingo.ast.Literal(
                _loc,
                sign=clingo.ast.Sign.NoSign,
                atom=clingo.ast.SymbolicAtom(clingo.ast.Function(_loc, name="test", arguments=(), external=False)),
            ),
            body=(
                clingo.ast.Literal(
                    _loc,
                    sign=clingo.ast.Sign.NoSign,
                    atom=clingo.ast.SymbolicAtom(
                        clingo.ast.Function(_loc, name="pos_atom", arguments=(), external=False)
                    ),
                ),
            ),
        )
        self.assertEqual(actual, expected)

    def test_rule_one_neg(self) -> None:
        sentence = Sentence.rule(Relation("test", ()), (Literal(Relation("neg_atom", ()), sign=Sign.NEGATIVE),))
        actual = sentence.to_clingo_ast()
        expected = clingo.ast.Rule(
            _loc,
            head=clingo.ast.Literal(
                _loc,
                sign=clingo.ast.Sign.NoSign,
                atom=clingo.ast.SymbolicAtom(clingo.ast.Function(_loc, name="test", arguments=(), external=False)),
            ),
            body=(
                clingo.ast.Literal(
                    _loc,
                    sign=clingo.ast.Sign.Negation,
                    atom=clingo.ast.SymbolicAtom(
                        clingo.ast.Function(_loc, name="neg_atom", arguments=(), external=False)
                    ),
                ),
            ),
        )
        self.assertEqual(actual, expected)


class TestSentenceToInfixStr(TestCase):
    def test_fact(self) -> None:
        sentence = Sentence.fact(Relation("test", ()))
        actual = sentence.to_infix_str()
        expected = "test."
        self.assertEqual(actual, expected)

    def test_rule_one_pos(self) -> None:
        sentence = Sentence.rule(Relation("test", ()), (Literal(Relation("pos_atom", ())),))
        actual = sentence.to_infix_str()
        expected = "test :- pos_atom."
        self.assertEqual(actual, expected)

    def test_rule_one_neg(self) -> None:
        sentence = Sentence.rule(Relation("test", ()), (Literal(Relation("neg_atom", ()), sign=Sign.NEGATIVE),))
        actual = sentence.to_infix_str()
        expected = "test :- not neg_atom."
        self.assertEqual(actual, expected)

    def test_rule_mixed(self) -> None:
        sentence = Sentence.rule(
            Relation("test", ()),
            (Literal(Relation("pos_atom", ())), Literal(Relation("neg_atom", ()), sign=Sign.NEGATIVE)),
        )
        actual = sentence.to_infix_str()
        expected = "test :- pos_atom, not neg_atom."
        self.assertEqual(actual, expected)


class TestRulesetRoleRules(unittest.TestCase):
    def test_tic_tac_toe(self) -> None:
        actual = tic_tac_toe_ruleset.role_rules
        expected = (
            Sentence.fact(Relation.role(Relation("x"))),
            Sentence.fact(Relation.role(Relation("o"))),
        )
        self.assertSequenceEqual(actual, expected)


class TestRulesetInitRules(unittest.TestCase):
    def test_tic_tac_toe(self) -> None:
        actual = tic_tac_toe_ruleset.init_rules
        expected = (Sentence.fact(Relation.init(Relation.control(Relation("x")))),)
        self.assertSequenceEqual(actual, expected)


class TestRulesetNextRules(unittest.TestCase):
    def test_rock_paper_scissors(self) -> None:
        actual = rock_paper_scissors_ruleset.next_rules
        R = Variable("R")
        C = Variable("C")
        expected = (
            Sentence.fact(
                Relation.role(Relation("left")),
            ),
            Sentence.fact(
                Relation.role(Relation("right")),
            ),
            *(
                Sentence.fact(
                    Relation("choice", (Relation(face),)),
                )
                for face in ("rock", "paper", "scissors")
            ),
            Sentence.rule(
                Relation.next(Relation("chose", (R, C))),
                (
                    Literal(Relation.role(R)),
                    Literal(Relation("choice", (C,))),
                    Literal(Relation.does(R, C)),
                ),
            ),
            Sentence.rule(
                Relation.next(Relation("chose", (R, C))),
                (
                    Literal(Relation.role(R)),
                    Literal(Relation("choice", (C,))),
                    Literal(Relation.true(Relation("chose", (R, C)))),
                ),
            ),
        )
        self.assertSequenceEqual(actual, expected)


class TestRulesetSeesRules(unittest.TestCase):
    def test_tic_tac_toe(self) -> None:
        actual = tic_tac_toe_ruleset.sees_rules
        expected = ()
        self.assertSequenceEqual(actual, expected)


class TestRulesetLegalRules(unittest.TestCase):
    def test_rock_paper_scissors(self) -> None:
        actual = rock_paper_scissors_ruleset.legal_rules
        R = Variable("R")
        C = Variable("C")
        expected = (
            Sentence.fact(
                Relation.role(Relation("left")),
            ),
            Sentence.fact(
                Relation.role(Relation("right")),
            ),
            *(
                Sentence.fact(
                    Relation("choice", (Relation(face),)),
                )
                for face in ("rock", "paper", "scissors")
            ),
            Sentence.rule(Relation.legal(R, C), (Literal(Relation.role(R)), Literal(Relation("choice", (C,))))),
        )
        self.assertSequenceEqual(actual, expected)


class TestRulesetGoalRules(unittest.TestCase):
    def test_tic_tac_toe(self) -> None:
        actual = tic_tac_toe_ruleset.goal_rules
        P1 = Variable("P1")
        P2 = Variable("P2")
        P = Variable("P")
        _P = Variable("_P")
        M = Variable("M")
        N = Variable("N")
        _M = Variable("_M")
        _N = Variable("_N")
        expected = (
            Sentence.fact(Relation.role(Relation("x"))),
            Sentence.fact(Relation.role(Relation("o"))),
            *(Sentence.fact(Relation("cell", (m, n))) for n in range(1, 4) for m in range(1, 4)),
            Sentence.rule(
                Relation("row", (M, P)),
                (
                    Literal(Relation.role(P)),
                    *(Literal(Relation("cell", (M, n))) for n in range(1, 4)),
                    *(Literal(Relation.true(Relation("cell", (M, n, P)))) for n in range(1, 4)),
                ),
            ),
            Sentence.rule(
                Relation("column", (N, P)),
                (
                    Literal(Relation.role(P)),
                    *(Literal(Relation("cell", (m, N))) for m in range(1, 4)),
                    *(Literal(Relation.true(Relation("cell", (m, N, P)))) for m in range(1, 4)),
                ),
            ),
            Sentence.rule(
                Relation("diagonal", (P,)),
                (
                    Literal(Relation.role(P)),
                    Literal(Relation("cell", (1, 1))),
                    Literal(Relation("cell", (2, 2))),
                    Literal(Relation("cell", (3, 3))),
                    Literal(Relation.true(Relation("cell", (1, 1, P)))),
                    Literal(Relation.true(Relation("cell", (2, 2, P)))),
                    Literal(Relation.true(Relation("cell", (3, 3, P)))),
                ),
            ),
            Sentence.rule(
                Relation("diagonal", (P,)),
                (
                    Literal(Relation.role(P)),
                    Literal(Relation("cell", (1, 3))),
                    Literal(Relation("cell", (2, 2))),
                    Literal(Relation("cell", (3, 1))),
                    Literal(Relation.true(Relation("cell", (1, 3, P)))),
                    Literal(Relation.true(Relation("cell", (2, 2, P)))),
                    Literal(Relation.true(Relation("cell", (3, 1, P)))),
                ),
            ),
            Sentence.rule(
                Relation("line", (P,)),
                (
                    Literal(Relation.role(P)),
                    Literal(Relation("row", (_M, P))),
                ),
            ),
            Sentence.rule(
                Relation("line", (P,)),
                (
                    Literal(Relation.role(P)),
                    Literal(Relation("column", (_N, P))),
                ),
            ),
            Sentence.rule(
                Relation("line", (P,)),
                (
                    Literal(Relation.role(P)),
                    Literal(Relation("diagonal", (P,))),
                ),
            ),
            Sentence.rule(
                Relation("open"),
                (
                    Literal(Relation("cell", (M, N))),
                    -Literal(Relation.true(Relation("cell", (M, N, _P)))),
                ),
            ),
            Sentence.rule(
                Relation.goal(P1, 0),
                (
                    Literal(Relation.role(P1)),
                    Literal(Relation.role(P2)),
                    Literal(Relation.distinct(P1, P2)),
                    Literal(Relation("line", (P2,))),
                ),
            ),
            Sentence.rule(
                Relation.goal(P1, 50),
                (
                    Literal(Relation.role(P1)),
                    Literal(Relation.role(P2)),
                    Literal(Relation.distinct(P1, P2)),
                    -Literal(Relation("line", (P1,))),
                    -Literal(Relation("line", (P2,))),
                    -Literal(Relation("open")),
                ),
            ),
            Sentence.rule(
                Relation.goal(P, 100),
                (
                    Literal(Relation.role(P)),
                    Literal(Relation("line", (P,))),
                ),
            ),
        )
        self.assertSequenceEqual(actual, expected)


class TestRulesetTerminalRules(unittest.TestCase):
    def test_rock_paper_scissors(self) -> None:
        actual = rock_paper_scissors_ruleset.terminal_rules
        R1 = Variable("R1")
        R2 = Variable("R2")
        _C1 = Variable("_C1")
        _C2 = Variable("_C2")
        expected = (
            Sentence.fact(
                Relation.role(Relation("left")),
            ),
            Sentence.fact(
                Relation.role(Relation("right")),
            ),
            Sentence.rule(
                Relation.terminal(),
                (
                    Literal(Relation.role(R1)),
                    Literal(Relation.role(R2)),
                    Literal(Relation.distinct(R1, R2)),
                    Literal(Relation.true(Relation("chose", (R1, _C1)))),
                    Literal(Relation.true(Relation("chose", (R2, _C2)))),
                ),
            ),
        )
        self.assertSequenceEqual(actual, expected)


@pytest.mark.parametrize(
    "arg1,arg2,expected",
    [
        (Relation("a"), Relation("a"), False),
        (Relation("a"), Relation("b"), True),
        (Relation("b"), Relation("a"), False),
        (Relation("a"), "b", True),
        ("a", Relation("b"), False),
        (1, 2, True),
        (1, Relation(arguments=(1,)), False),
        (Relation(arguments=(1,)), 1, True),
        (Relation("a", (1, 2, 3)), Relation("a", (1, 2, 3)), False),
        (Relation("a", (1, 2, 3)), Relation("a", (1, 2, 3, 4)), True),
        (Relation("a", (1, 2, 3)), Relation("a", (1, 2)), False),
        (Relation("a", (1, 2, 3)), Relation("a", (1, 2, 4)), True),
    ],
)
def test_relation_compare___lt___as_expected(arg1: Subrelation, arg2: Subrelation, expected: bool):
    arg1_compare = Relation.Compare.from_subrelation(arg1)
    arg2_compare = Relation.Compare.from_subrelation(arg2)
    assert (arg1_compare < arg2_compare) is expected
