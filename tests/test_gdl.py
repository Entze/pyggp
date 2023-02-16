# pylint: disable=missing-docstring,invalid-name
import unittest

from pyggp.gdl import Relation


class TestRelationMatch(unittest.TestCase):
    def test_atom(self) -> None:
        relation = Relation("test", ())
        actual = relation.match("test", 0)
        expected = True
        self.assertIs(actual, expected)

    def test_empty_tuple(self) -> None:
        relation = Relation()
        actual = relation.match()
        expected = True
        self.assertIs(actual, expected)

    def test_2tuple(self) -> None:
        relation = Relation(arguments=(1, 2))
        actual = relation.match(arity=2)
        expected = True
        self.assertIs(actual, expected)

    def test_wrong_arity(self) -> None:
        relation = Relation("test", ())
        actual = relation.match("test", 1)
        expected = False
        self.assertIs(actual, expected)

    def test_wrong_name(self) -> None:
        relation = Relation("test", (1, 2))
        actual = relation.match("different", 2)
        expected = False
        self.assertIs(actual, expected)
