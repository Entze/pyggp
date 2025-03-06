import lark
import pytest

from pyggp.game_description_language import Literal, Number, Relation, Ruleset, Sentence, String, Subrelation, Variable
from pyggp.game_description_language.grammar import TreeToGDLTransformer, infix_grammar


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ('"a"', String("a")),
        ('"a b"', String("a b")),
        ('"1"', String("1")),
        ('"_"', String("_")),
        ('"_VAR"', String("_VAR")),
    ],
)
def test_string(parse: str, expected: String) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="string")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("1", Number(1)),
        ("-1", Number(-1)),
        ("0", Number(0)),
        ("+1", Number(1)),
        ("239042903", Number(239042903)),
    ],
)
def test_number(parse: str, expected: Number) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="number")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("A", Variable("A")),
        ("Variable", Variable("Variable")),
        ("Everyone", Variable("Everyone")),
        ("_", Variable("_")),
        ("_Any", Variable("_Any")),
    ],
)
def test_variable(parse: str, expected: Variable) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="variable")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("a", Relation("a")),
        ("a()", Relation("a")),
        ("__time", Relation("__time")),
    ],
)
def test_atom(parse: str, expected: Relation) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="relation")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("a", Subrelation(Relation("a"))),
        ('"a"', Subrelation(String("a"))),
        ("1", Subrelation(Number(1))),
        ("A", Subrelation(Variable("A"))),
        ('"1"', Subrelation(String("1"))),
        ("a()", Subrelation(Relation("a"))),
        ("__time", Subrelation(Relation("__time"))),
        ("_", Subrelation(Variable("_"))),
        ("_Any", Subrelation(Variable("_Any"))),
    ],
)
def test_subrelation_non_recursive(parse: str, expected: Subrelation) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="subrelation")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("a(1)", Relation("a", (Subrelation(Number(1)),))),
        ("a(1, 2)", Relation("a", (Subrelation(Number(1)), Subrelation(Number(2))))),
        (
            'a(one(1), two("2"), three(three))',
            Relation(
                "a",
                (
                    Subrelation(Relation("one", (Subrelation(Number(1)),))),
                    Subrelation(Relation("two", (Subrelation(String("2")),))),
                    Subrelation(Relation("three", (Subrelation(Relation("three")),))),
                ),
            ),
        ),
    ],
)
def test_function(parse: str, expected: Relation) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="relation")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("()", Relation()),
        ("(a)", Relation(arguments=(Subrelation(Relation("a")),))),
        (
            '(one, 2, "three")',
            Relation(arguments=(Subrelation(Relation("one")), Subrelation(Number(2)), Subrelation(String("three")))),
        ),
    ],
)
def test_tuple(parse: str, expected: Relation) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="relation")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("a(1)", Subrelation(Relation("a", (Subrelation(Number(1)),)))),
        (
            "a((1,2), b)",
            Subrelation(
                Relation(
                    "a",
                    (
                        Subrelation(Relation(arguments=(Subrelation(Number(1)), Subrelation(Number(2))))),
                        Subrelation(Relation("b")),
                    ),
                ),
            ),
        ),
        ("a(V, 2)", Subrelation(Relation("a", (Subrelation(Variable("V")), Subrelation(Number(2)))))),
    ],
)
def test_subrelation_recursive(parse: str, expected: Subrelation) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="subrelation")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("a", Literal(Relation("a"), sign=Literal.Sign.NOSIGN)),
        ("not a", Literal(Relation("a"), sign=Literal.Sign.NEGATIVE)),
    ],
)
def test_literal(parse: str, expected: Literal) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="literal")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("a.", Sentence(Relation("a"))),
        ("b.", Sentence(Relation("b"))),
        ("b :-.", Sentence(Relation("b"))),
    ],
)
def test_fact(parse: str, expected: Literal) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="sentence")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("a :- b.", Sentence(Relation("a"), (Literal(Relation("b")),))),
        ("a :- b, c.", Sentence(Relation("a"), (Literal(Relation("b")), Literal(Relation("c"))))),
        (
            "a :- b, not c.",
            Sentence(Relation("a"), (Literal(Relation("b")), Literal(Relation("c"), sign=Literal.Sign.NEGATIVE))),
        ),
        (
            "a :- b, not c, d.",
            Sentence(
                Relation("a"),
                (Literal(Relation("b")), Literal(Relation("c"), sign=Literal.Sign.NEGATIVE), Literal(Relation("d"))),
            ),
        ),
    ],
)
def test_rule(parse: str, expected: Sentence) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="sentence")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("a :- b.", Ruleset.from_rules([Sentence(Relation("a"), (Literal(Relation("b")),))])),
        (
            "a. b :- c.",
            Ruleset.from_rules([Sentence(Relation("a")), Sentence(Relation("b"), (Literal(Relation("c")),))]),
        ),
    ],
)
def test_ruleset(parse: str, expected: Ruleset) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="ruleset")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected


@pytest.mark.parametrize(
    ("parse", "expected"),
    [
        ("distinct(a, b)", Relation("__comp_not_equal", (Subrelation(Relation("a")), Subrelation(Relation("b"))))),
        (
            "distinct(a, b, c)",
            Relation(
                "__comp_not_equal",
                (Subrelation(Relation("a")), Subrelation(Relation("b")), Subrelation(Relation("c"))),
            ),
        ),
    ],
)
def test_comparison(parse: str, expected: Relation) -> None:
    parser = lark.Lark(grammar=infix_grammar, start="comparison")
    parsed = parser.parse(parse)
    actual = TreeToGDLTransformer().transform(parsed)
    assert actual == expected
