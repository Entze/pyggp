# pylint: disable=missing-docstring,invalid-name,import-outside-toplevel
import unittest
from unittest import TestCase

from pyggp.gdl import Relation, Sentence, Literal, Sign, Variable, argument_signatures_match


class TestVariable__str__(TestCase):
    def test_var(self):
        variable = Variable("X")
        actual = str(variable)
        expected = "X"
        self.assertEqual(actual, expected)

    def test_wildcard(self):
        variable = Variable("_")
        actual = str(variable)
        expected = "_"
        self.assertEqual(actual, expected)

    def test_named_wildcard(self):
        variable = Variable("_X")
        actual = str(variable)
        expected = "_X"
        self.assertEqual(actual, expected)


class TestRelation__str__(TestCase):
    def test_atom(self):
        relation = Relation("test", ())
        actual = str(relation)
        expected = "test"
        self.assertEqual(actual, expected)

    def test_empty_tuple(self):
        relation = Relation()
        actual = str(relation)
        expected = "()"
        self.assertEqual(actual, expected)

    def test_2tuple(self):
        relation = Relation(arguments=(1, 2))
        actual = str(relation)
        expected = "(1, 2)"
        self.assertEqual(actual, expected)

    def test_nested(self):
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
            Relation.to_infix_str(None)  # type: ignore


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
        from pyggp.games import tic_tac_toe_ruleset

        actual = tic_tac_toe_ruleset.role_rules
        expected = (
            Sentence.fact(Relation.role(Relation("x"))),
            Sentence.fact(Relation.role(Relation("o"))),
        )
        self.assertSequenceEqual(actual, expected)


class TestRulesetInitRules(unittest.TestCase):
    def test_tic_tac_toe(self) -> None:
        from pyggp.games import tic_tac_toe_ruleset

        actual = tic_tac_toe_ruleset.init_rules
        expected = (Sentence.fact(Relation.init(Relation.control(Relation("x")))),)
        self.assertSequenceEqual(actual, expected)


class TestRulesetNextRules(unittest.TestCase):
    def test_rock_paper_scissors(self) -> None:
        from pyggp.games import rock_paper_scissors_ruleset

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
        from pyggp.games import tic_tac_toe_ruleset

        actual = tic_tac_toe_ruleset.sees_rules
        expected = ()
        self.assertSequenceEqual(actual, expected)


class TestRulesetLegalRules(unittest.TestCase):
    def test_rock_paper_scissors(self) -> None:
        from pyggp.games import rock_paper_scissors_ruleset

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
        from pyggp.games import tic_tac_toe_ruleset

        actual = tic_tac_toe_ruleset.goal_rules
        P1 = Variable("P1")
        P2 = Variable("P2")
        P = Variable("P")
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
            *(
                Sentence.rule(
                    Relation("diagonal", (P,)),
                    (
                        Literal(Relation.role(P)),
                        *(Literal(Relation.true(Relation("cell", (abs(c - m), m, P)))) for m in range(1, 4)),
                    ),
                )
                for c in (0, 3)
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
                    Literal(Relation("cell", (_M, _N))),
                    -Literal(Relation.true(Relation("cell", (_M, _N, P1)))),
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
        from pyggp.games import rock_paper_scissors_ruleset

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
