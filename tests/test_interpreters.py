# pylint: disable=missing-docstring,invalid-name,unused-argument
from unittest import TestCase

import pyggp.games
import pytest
from pyggp.exceptions.interpreter_exceptions import (
    MoreThanOneModelInterpreterError,
    MultipleGoalsInterpreterError,
    UnexpectedRoleInterpreterError,
)
from pyggp.gdl import Literal, Relation, Ruleset, Sentence, State
from pyggp.interpreters import ClingoInterpreter, get_roles_in_control


@pytest.mark.skip
class TestGetRolesInControl(TestCase):
    def test_empty(self) -> None:
        state: State = frozenset()
        actual = get_roles_in_control(state)
        expected: State = frozenset()
        self.assertSetEqual(actual, expected)

    def test_single(self) -> None:
        r = Relation("r")
        state = frozenset({Relation.control(r)})
        actual = get_roles_in_control(state)
        expected = frozenset({r})
        self.assertSetEqual(actual, expected)


@pytest.mark.skip
class TestClingoInterpreterGetRoles(TestCase):
    def test_tic_tac_toe(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        actual = interpreter.get_roles()
        expected = {Relation("x"), Relation("o")}
        self.assertSetEqual(actual, expected)

    def test_nim(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        actual = interpreter.get_roles()
        expected = {Relation("first"), Relation("second")}
        self.assertSetEqual(actual, expected)

    def test_rock_paper_scissors(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        actual = interpreter.get_roles()
        expected = {Relation("left"), Relation("right")}
        self.assertSetEqual(actual, expected)

    def test_minipoker(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        actual = interpreter.get_roles()
        expected = {Relation("bluffer"), Relation("caller"), Relation("random")}
        self.assertSetEqual(actual, expected)


@pytest.mark.skip
class TestClingoInterpreterGetInitState(TestCase):
    def test_tic_tac_toe(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        actual = interpreter.get_init_state()
        expected = {
            Relation.control(Relation("x")),
        }
        self.assertSetEqual(actual, expected)

    def test_nim(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        actual = interpreter.get_init_state()
        expected = {
            Relation.control(Relation("first")),
            Relation("pile", (Relation("size", (7,)),)),
        }
        self.assertSetEqual(actual, expected)

    def test_rock_paper_scissors(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        actual = interpreter.get_init_state()
        expected = {
            Relation.control(Relation("left")),
            Relation.control(Relation("right")),
        }
        self.assertSetEqual(actual, expected)

    def test_minipoker(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        actual = interpreter.get_init_state()
        expected = {
            Relation.control(Relation("random")),
        }
        self.assertSetEqual(actual, expected)

    def test_invalid_gdl(self) -> None:
        ruleset = Ruleset(
            (
                Sentence.rule(
                    Relation.init(Relation("paradox", (1,))), (-Literal(Relation.init(Relation("paradox", (2,)))),)
                ),
                Sentence.rule(
                    Relation.init(Relation("paradox", (2,))), (-Literal(Relation.init(Relation("paradox", (1,)))),)
                ),
            )
        )

        interpreter = ClingoInterpreter(ruleset)
        with self.assertRaises(MoreThanOneModelInterpreterError):
            interpreter.get_init_state()


@pytest.mark.skip
class TestClingoInterpreterGetNextState(TestCase):
    def test_tic_tac_toe(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("o")), Relation("cell", (2, 2, Relation("x")))))
        move = Relation("cell", (1, 1))
        play = Relation("does", (Relation("o"), move))
        actual = interpreter.get_next_state(state, play)
        expected = {
            Relation.control(Relation("x")),
            Relation("cell", (1, 1, Relation("o"))),
            Relation("cell", (2, 2, Relation("x"))),
        }
        self.assertSetEqual(actual, expected)

    def test_nim(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("first")), Relation("pile", (Relation("size", (2,)),))))
        move = Relation("take", (2,))
        play = Relation("does", (Relation("first"), move))
        actual = interpreter.get_next_state(state, play)
        expected = {
            Relation.control(Relation("first")),
            Relation("pile", (Relation("size", (0,)),)),
        }
        self.assertSetEqual(actual, expected)

    def test_rock_paper_scissors(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("left")), Relation.control(Relation("right"))))
        move_left = Relation("rock")
        move_right = Relation("paper")
        play_left = Relation("does", (Relation("left"), move_left))
        play_right = Relation("does", (Relation("right"), move_right))
        actual = interpreter.get_next_state(state, play_left, play_right)
        expected = {
            Relation("chose", (Relation("left"), Relation("rock"))),
            Relation("chose", (Relation("right"), Relation("paper"))),
        }
        self.assertSetEqual(actual, expected)

    def test_minipoker(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation.control(Relation("caller")),
                Relation("dealt"),
                Relation("dealt", (Relation("red"),)),
                Relation("held", (Relation("bluffer"),)),
            )
        )
        move = Relation("call")
        play = Relation("does", (Relation("caller"), move))
        actual = interpreter.get_next_state(state, play)
        expected = {
            Relation("dealt"),
            Relation("dealt", (Relation("red"),)),
            Relation("held", (Relation("bluffer"),)),
            Relation("called", (Relation("caller"),)),
        }
        self.assertSetEqual(actual, expected)


@pytest.mark.skip
class TestClingoGetSees(TestCase):
    def test_tic_tac_toe(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("o")), Relation("cell", (2, 2, Relation("x")))))
        actual = interpreter.get_sees(state)
        expected = {
            Relation("x"): state,
            Relation("o"): state,
        }
        self.assertDictEqual(actual, expected)

    def test_nim(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("first")), Relation("pile", (Relation("size", (2,)),))))
        actual = interpreter.get_sees(state)
        expected = {
            Relation("first"): state,
            Relation("second"): state,
        }
        self.assertDictEqual(actual, expected)

    def test_rock_paper_scissors(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("left")), Relation.control(Relation("right"))))
        actual = interpreter.get_sees(state)
        expected = {
            Relation("left"): state,
            Relation("right"): state,
        }
        self.assertDictEqual(actual, expected)

    def test_minipoker(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (Relation.control(Relation("bluffer")), Relation("dealt"), Relation("dealt", (Relation("red"),)))
        )
        caller_view = frozenset((Relation.control(Relation("bluffer")), Relation("dealt")))
        actual = interpreter.get_sees(state)
        expected = {
            Relation("bluffer"): state,
            Relation("caller"): caller_view,
            Relation.random(): state,
        }
        self.assertDictEqual(actual, expected)


@pytest.mark.skip
class TestClingoGetSeesByRole(TestCase):
    def test_tic_tac_toe(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("o")), Relation("cell", (2, 2, Relation("x")))))
        actual = interpreter.get_sees_by_role(state, Relation("o"))
        expected = state
        self.assertSetEqual(actual, expected)

    def test_nim(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("first")), Relation("pile", (Relation("size", (2,)),))))
        actual = interpreter.get_sees_by_role(state, Relation("first"))
        expected = state
        self.assertSetEqual(actual, expected)

    def test_rock_paper_scissors(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("left")), Relation.control(Relation("right"))))
        actual = interpreter.get_sees_by_role(state, Relation("left"))
        expected = state
        self.assertSetEqual(actual, expected)

    def test_minipoker(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (Relation.control(Relation("bluffer")), Relation("dealt"), Relation("dealt", (Relation("red"),)))
        )
        caller_view = frozenset((Relation.control(Relation("bluffer")), Relation("dealt")))
        actual = interpreter.get_sees_by_role(state, Relation("caller"))
        expected = caller_view
        self.assertSetEqual(actual, expected)

    def test_invalid_gdl(self) -> None:
        ruleset = Ruleset(
            (Sentence.fact(Relation.role(Relation("x"))), Sentence.fact(Relation.sees(Relation("y"), Relation("z"))))
        )
        interpreter = ClingoInterpreter(ruleset)
        state: State = frozenset()
        with self.assertRaises(UnexpectedRoleInterpreterError):
            interpreter.get_sees_by_role(state, Relation("x"))


@pytest.mark.skip
class TestClingoInterpreterGetLegalMoves(TestCase):
    def test_tic_tac_toe(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("o")), Relation("cell", (2, 2, Relation("x")))))
        actual = interpreter.get_legal_moves(state)
        expected = {
            Relation("o"): frozenset(
                {Relation("cell", (n, m)) for n in range(1, 4) for m in range(1, 4) if n != 2 or m != 2}
            )
        }
        self.assertGreaterEqual(frozenset(actual.keys()), frozenset(expected.keys()))
        for role in expected:  # pylint: disable=consider-using-dict-items
            self.assertSetEqual(actual[role], expected[role])

    def test_nim(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("first")), Relation("pile", (Relation("size", (2,)),))))
        actual = interpreter.get_legal_moves(state)
        expected = {Relation("first"): frozenset({Relation("take", (1,)), Relation("take", (2,))})}
        self.assertGreaterEqual(frozenset(actual.keys()), frozenset(expected.keys()))
        for role in expected:  # pylint: disable=consider-using-dict-items
            self.assertSetEqual(actual[role], expected[role])

    def test_rock_paper_scissors(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("left")), Relation.control(Relation("right"))))
        actual = interpreter.get_legal_moves(state)
        expected = {
            Relation("left"): frozenset({Relation("rock"), Relation("paper"), Relation("scissors")}),
            Relation("right"): frozenset({Relation("rock"), Relation("paper"), Relation("scissors")}),
        }
        self.assertGreaterEqual(frozenset(actual.keys()), frozenset(expected.keys()))
        for role in expected:  # pylint: disable=consider-using-dict-items
            self.assertSetEqual(actual[role], expected[role])

    def test_minipoker(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation.random()),))
        actual = interpreter.get_legal_moves(state)
        expected = {
            Relation.random(): frozenset(
                {
                    Relation("deal", (Relation("red"),)),
                    Relation("deal", (Relation("black"),)),
                }
            )
        }
        self.assertGreaterEqual(frozenset(actual.keys()), frozenset(expected.keys()))
        for role in expected:  # pylint: disable=consider-using-dict-items
            self.assertSetEqual(actual[role], expected[role])

    def test_invalid_gdl(self) -> None:
        ruleset = Ruleset(
            (Sentence.fact(Relation.role(Relation("x"))), Sentence.fact(Relation.legal(Relation("y"), Relation("z"))))
        )
        interpreter = ClingoInterpreter(ruleset)
        state: State = frozenset()
        with self.assertRaises(UnexpectedRoleInterpreterError):
            interpreter.get_legal_moves(state)


@pytest.mark.skip
class TestClingoInterpreterIsLegal(TestCase):
    def test_tic_tac_toe_legal(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("o")), Relation("cell", (2, 2, Relation("x")))))
        actual = interpreter.is_legal(state, Relation("o"), Relation("cell", (1, 1)))
        expected = True
        self.assertEqual(actual, expected)

    def test_tic_tac_toe_illegal(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("o")), Relation("cell", (2, 2, Relation("x")))))
        actual = interpreter.is_legal(state, Relation("o"), Relation("cell", (2, 2)))
        expected = False
        self.assertEqual(actual, expected)

    def test_nim_legal(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("first")), Relation("pile", (Relation("size", (2,)),))))
        actual = interpreter.is_legal(state, Relation("first"), Relation("take", (1,)))
        expected = True
        self.assertEqual(actual, expected)

    def test_nim_illegal(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("first")), Relation("pile", (Relation("size", (2,)),))))
        actual = interpreter.is_legal(state, Relation("first"), Relation("take", (3,)))
        expected = False
        self.assertEqual(actual, expected)

    def test_rock_paper_scissors_legal(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("left")), Relation.control(Relation("right"))))
        actual = interpreter.is_legal(state, Relation("left"), Relation("rock"))
        expected = True
        self.assertEqual(actual, expected)

    def test_rock_paper_scissors_illegal(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("left")), Relation.control(Relation("right"))))
        actual = interpreter.is_legal(state, Relation("left"), Relation("left"))
        expected = False
        self.assertEqual(actual, expected)

    def test_minipoker_legal(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation.random()),))
        actual = interpreter.is_legal(state, Relation.random(), Relation("deal", (Relation("red"),)))
        expected = True
        self.assertEqual(actual, expected)

    def test_minipoker_illegal(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (Relation.control(Relation("bluffer")), Relation("dealt"), Relation("dealt", (Relation("black"),)))
        )
        actual = interpreter.is_legal(state, Relation("bluffer"), Relation("resign"))
        expected = False
        self.assertEqual(actual, expected)


@pytest.mark.skip
class TestClingoInterpreterGetGoals(TestCase):
    def test_tic_tac_toe_during_game(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("o")), Relation("cell", (2, 2, Relation("x")))))
        actual = interpreter.get_goals(state)
        expected = {Relation("o"): None, Relation("x"): None}
        self.assertDictEqual(actual, expected)

    def test_tic_tac_toe_tie(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation("cell", (1, 1, Relation("o"))),
                Relation("cell", (1, 2, Relation("x"))),
                Relation("cell", (1, 3, Relation("o"))),
                Relation("cell", (2, 1, Relation("x"))),
                Relation("cell", (2, 2, Relation("o"))),
                Relation("cell", (2, 3, Relation("x"))),
                Relation("cell", (3, 1, Relation("x"))),
                Relation("cell", (3, 2, Relation("o"))),
                Relation("cell", (3, 3, Relation("x"))),
            )
        )
        actual = interpreter.get_goals(state)
        expected = {Relation("o"): 50, Relation("x"): 50}
        self.assertDictEqual(actual, expected)

    def test_tic_tac_toe_x_wins(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation("cell", (1, 1, Relation("x"))),
                Relation("cell", (1, 2, Relation("x"))),
                Relation("cell", (1, 3, Relation("o"))),
                Relation("cell", (2, 1, Relation("x"))),
                Relation("cell", (2, 2, Relation("o"))),
                Relation("cell", (2, 3, Relation("x"))),
                Relation("cell", (3, 1, Relation("x"))),
                Relation("cell", (3, 2, Relation("o"))),
                Relation("cell", (3, 3, Relation("o"))),
            )
        )
        actual = interpreter.get_goals(state)
        expected = {Relation("o"): 0, Relation("x"): 100}
        self.assertDictEqual(actual, expected)

    def test_tic_tac_toe_o_wins(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation("cell", (1, 1, Relation("o"))),
                Relation("cell", (1, 2, Relation("x"))),
                Relation("cell", (1, 3, Relation("o"))),
                Relation("cell", (2, 1, Relation("x"))),
                Relation("cell", (2, 2, Relation("o"))),
                Relation("cell", (2, 3, Relation("x"))),
                Relation("cell", (3, 1, Relation("o"))),
                Relation("cell", (3, 2, Relation("x"))),
                Relation("cell", (3, 3, Relation("o"))),
            )
        )
        actual = interpreter.get_goals(state)
        expected = {Relation("o"): 100, Relation("x"): 0}
        self.assertDictEqual(actual, expected)

    def test_nim_during_game(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("first")), Relation("pile", (Relation("size", (2,)),))))
        actual = interpreter.get_goals(state)
        expected = {Relation("first"): None, Relation("second"): None}
        self.assertDictEqual(actual, expected)

    def test_nim_first_wins(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("first")), Relation("pile", (Relation("size", (0,)),))))
        actual = interpreter.get_goals(state)
        expected = {Relation("first"): 1, Relation("second"): 0}
        self.assertDictEqual(actual, expected)

    def test_nim_second_wins(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("second")), Relation("pile", (Relation("size", (0,)),))))
        actual = interpreter.get_goals(state)
        expected = {Relation("first"): 0, Relation("second"): 1}
        self.assertDictEqual(actual, expected)

    def test_rock_paper_scissors_during_game(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("left")), Relation.control(Relation("right"))))
        actual = interpreter.get_goals(state)
        expected = {Relation("left"): None, Relation("right"): None}
        self.assertDictEqual(actual, expected)

    def test_rock_paper_scissors_tie(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation(
                    "chose",
                    (
                        Relation("left"),
                        Relation("rock"),
                    ),
                ),
                Relation(
                    "chose",
                    (
                        Relation("right"),
                        Relation("rock"),
                    ),
                ),
            )
        )

        actual = interpreter.get_goals(state)
        expected = {Relation("left"): 50, Relation("right"): 50}
        self.assertDictEqual(actual, expected)

    def test_rock_paper_scissors_left_wins(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation(
                    "chose",
                    (
                        Relation("left"),
                        Relation("rock"),
                    ),
                ),
                Relation(
                    "chose",
                    (
                        Relation("right"),
                        Relation("scissors"),
                    ),
                ),
            )
        )

        actual = interpreter.get_goals(state)
        expected = {Relation("left"): 100, Relation("right"): 0}
        self.assertDictEqual(actual, expected)

    def test_rock_paper_scissors_right_wins(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation(
                    "chose",
                    (
                        Relation("left"),
                        Relation("rock"),
                    ),
                ),
                Relation(
                    "chose",
                    (
                        Relation("right"),
                        Relation("paper"),
                    ),
                ),
            )
        )

        actual = interpreter.get_goals(state)
        expected = {Relation("left"): 0, Relation("right"): 100}
        self.assertDictEqual(actual, expected)

    def test_minipoker_during_game(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation.random()),))
        actual = interpreter.get_goals(state)
        expected = {Relation.random(): None, Relation("bluffer"): None, Relation("caller"): None}
        self.assertDictEqual(actual, expected)

    def test_minipoker_bluffer_resigns(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (Relation("dealt"), Relation("dealt", (Relation("red"),)), Relation("resigned", (Relation("bluffer"),)))
        )
        actual = interpreter.get_goals(state)
        expected = {Relation.random(): None, Relation("bluffer"): -10, Relation("caller"): 10}
        self.assertDictEqual(actual, expected)

    def test_minipoker_caller_resigns_on_red(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation("dealt"),
                Relation("dealt", (Relation("red"),)),
                Relation("held", (Relation("bluffer"),)),
                Relation("resigned", (Relation("caller"),)),
            )
        )
        actual = interpreter.get_goals(state)
        expected = {Relation.random(): None, Relation("bluffer"): 4, Relation("caller"): -4}
        self.assertDictEqual(actual, expected)

    def test_minipoker_caller_calls_on_red(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation("dealt"),
                Relation("dealt", (Relation("red"),)),
                Relation("held", (Relation("bluffer"),)),
                Relation("called", (Relation("caller"),)),
            )
        )
        actual = interpreter.get_goals(state)
        expected = {Relation.random(): None, Relation("bluffer"): -20, Relation("caller"): 20}
        self.assertDictEqual(actual, expected)

    def test_invalid_gdl_unexpected_role(self) -> None:
        ruleset = Ruleset((Sentence.fact(Relation.role(Relation("x"))), Sentence.fact(Relation.goal(Relation("y"), 0))))
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("x")),))
        with self.assertRaises(UnexpectedRoleInterpreterError):
            interpreter.get_goals(state)

    def test_invalid_gdl_multiple_goals(self) -> None:
        ruleset = Ruleset(
            (
                Sentence.fact(Relation.role(Relation("x"))),
                Sentence.fact(Relation.goal(Relation("x"), 0)),
                Sentence.fact(Relation.goal(Relation("x"), 1)),
            )
        )
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("x")),))
        with self.assertRaises(MultipleGoalsInterpreterError):
            interpreter.get_goals(state)


@pytest.mark.skip
class TestClingoInterpreterGetGoalByRole(TestCase):
    def test_tic_tac_toe_during_game(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("x")),))
        actual = interpreter.get_goal_by_role(state, "x")
        expected = None
        self.assertEqual(actual, expected)


@pytest.mark.skip
class TestClingoInterpreterGetTerminal(TestCase):
    def test_tic_tac_toe_non_terminal(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("x")),))
        actual = interpreter.is_terminal(state)
        expected = False
        self.assertEqual(actual, expected)

    def test_tic_tac_toe_terminal_win(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation("cell", (1, 1, Relation("x"))),
                Relation("cell", (1, 2, Relation("o"))),
                Relation("cell", (1, 3, Relation("x"))),
                Relation("cell", (2, 1, Relation("o"))),
                Relation("cell", (2, 2, Relation("x"))),
                Relation("cell", (3, 1, Relation("x"))),
                Relation("cell", (3, 3, Relation("o"))),
            )
        )
        actual = interpreter.is_terminal(state)
        expected = True
        self.assertEqual(actual, expected)

    def test_tic_tac_toe_terminal_tie(self) -> None:
        ruleset = pyggp.games.tic_tac_toe_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation("cell", (1, 1, Relation("o"))),
                Relation("cell", (1, 2, Relation("o"))),
                Relation("cell", (1, 3, Relation("x"))),
                Relation("cell", (2, 1, Relation("x"))),
                Relation("cell", (2, 2, Relation("x"))),
                Relation("cell", (2, 3, Relation("o"))),
                Relation("cell", (3, 1, Relation("o"))),
                Relation("cell", (3, 2, Relation("x"))),
                Relation("cell", (3, 3, Relation("x"))),
            )
        )
        actual = interpreter.is_terminal(state)
        expected = True
        self.assertEqual(actual, expected)

    def test_nim_non_terminal(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("first")), Relation("pile", (Relation("size", (7,)),))))
        actual = interpreter.is_terminal(state)
        expected = False
        self.assertEqual(actual, expected)

    def test_nim_terminal(self) -> None:
        ruleset = pyggp.games.nim_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("first")), Relation("pile", (Relation("size", (0,)),))))
        actual = interpreter.is_terminal(state)
        expected = True
        self.assertEqual(actual, expected)

    def test_rock_paper_scissors_non_terminal(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation("left")), Relation.control(Relation("right"))))
        actual = interpreter.is_terminal(state)
        expected = False
        self.assertEqual(actual, expected)

    def test_rock_paper_scissors_terminal(self) -> None:
        ruleset = pyggp.games.rock_paper_scissors_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (
                Relation("chose", (Relation("left"), Relation("rock"))),
                Relation("chose", (Relation("right"), Relation("rock"))),
            )
        )
        actual = interpreter.is_terminal(state)
        expected = True
        self.assertEqual(actual, expected)

    def test_minipoker_non_terminal(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset((Relation.control(Relation.random()),))
        actual = interpreter.is_terminal(state)
        expected = False
        self.assertEqual(actual, expected)

    def test_minipoker_terminal(self) -> None:
        ruleset = pyggp.games.minipoker_ruleset
        interpreter = ClingoInterpreter(ruleset)
        state = frozenset(
            (Relation("dealt"), Relation("dealt", (Relation("red"),)), Relation("resigned", (Relation("bluffer"),)))
        )
        actual = interpreter.is_terminal(state)
        expected = True
        self.assertEqual(actual, expected)
