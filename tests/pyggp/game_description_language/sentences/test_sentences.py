import pytest
from pyggp.game_description_language.literals import Literal
from pyggp.game_description_language.sentences import Sentence
from pyggp.game_description_language.subrelations import Relation


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        (Sentence(Relation()), "()."),
        (Sentence(Relation(name="atom")), "atom."),
        (Sentence(Relation(name="atom"), (Literal(Relation()),)), "atom :- ()."),
        (Sentence(Relation(name="atom"), (Literal(Relation(name="atom")),)), "atom :- atom."),
        (
            Sentence(Relation(name="atom"), (Literal(Relation(name="atom")), Literal(Relation(name="atom")))),
            "atom :- atom, atom.",
        ),
        (
            Sentence(Relation(name="atom"), (Literal(Relation(name="atom"), sign=Literal.Sign.NEGATIVE),)),
            "atom :- not atom.",
        ),
        (
            Sentence(
                Relation(name="atom"),
                (Literal(Relation(name="atom"), sign=Literal.Sign.NEGATIVE), Literal(Relation(name="atom"))),
            ),
            "atom :- not atom, atom.",
        ),
        (
            Sentence(
                Relation(name="atom"),
                (Literal(Relation(name="atom")), Literal(Relation(name="atom"), sign=Literal.Sign.NEGATIVE)),
            ),
            "atom :- atom, not atom.",
        ),
    ],
)
def test_infix_str(sentence: Sentence, expected: str) -> None:
    actual = sentence.infix_str
    assert actual == expected


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        (Sentence(Relation()), "()."),
        (Sentence(Relation(name="atom")), "atom."),
        (Sentence(Relation(name="atom"), (Literal(Relation()),)), "atom :- ()."),
        (Sentence(Relation(name="atom"), (Literal(Relation(name="atom")),)), "atom :- atom."),
        (
            Sentence(Relation(name="atom"), (Literal(Relation(name="atom")), Literal(Relation(name="atom")))),
            "atom :- atom, atom.",
        ),
        (
            Sentence(Relation(name="atom"), (Literal(Relation(name="atom"), sign=Literal.Sign.NEGATIVE),)),
            "atom :- not atom.",
        ),
        (
            Sentence(
                Relation(name="atom"),
                (Literal(Relation(name="atom"), sign=Literal.Sign.NEGATIVE), Literal(Relation(name="atom"))),
            ),
            "atom :- not atom, atom.",
        ),
        (
            Sentence(
                Relation(name="atom"),
                (Literal(Relation(name="atom")), Literal(Relation(name="atom"), sign=Literal.Sign.NEGATIVE)),
            ),
            "atom :- atom, not atom.",
        ),
    ],
)
def test_dunder_str(sentence: Sentence, expected: str) -> None:
    actual = str(sentence)
    assert actual == expected


@pytest.mark.parametrize(
    # Disables PT006 (Wrong name(s) type in @pytest.mark.parametrize). This seems to be a bug in ruff.
    ("sentence",),  # noqa: PT006
    [
        (Sentence(Relation(name="head")),),
        (Sentence(Relation(name="head"), (Literal(Relation(name="pos")),)),),
        (
            Sentence(
                Relation(name="head"),
                (Literal(Relation(name="pos")), Literal(Relation(name="neg"), sign=Literal.Sign.NEGATIVE)),
            ),
        ),
    ],
)
def test_dunder_rich(sentence: Sentence) -> None:
    actual = sentence.__rich__()
    assert "head" in actual
    assert len(sentence.body) < 1 or "pos" in actual
    assert len(sentence.body) < 2 or "neg" in actual
    assert len(sentence.body) < 2 or "not" in actual
