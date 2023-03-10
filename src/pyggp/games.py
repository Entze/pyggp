"""Definitions of basic games."""
from typing import Union

from pyggp.gdl import Literal, Relation, Ruleset, Sentence, Subrelation, Variable

_R = Variable("R")
_R1 = Variable("R1")
_R2 = Variable("R2")
_S = Variable("S")
_S1 = Variable("S1")
_S2 = Variable("S2")

nim_ruleset: Ruleset = Ruleset(
    (
        # Role
        Sentence.fact(Relation.role(Relation("first"))),
        Sentence.fact(Relation.role(Relation("second"))),
        # Init
        Sentence.fact(Relation.init(Relation.control(Relation("first")))),
        Sentence.fact(Relation.init(Relation("pile", (Relation("size", (7,)),)))),
        # Helpers
        *(Sentence.fact(Relation.gt(n, m)) for n in range(-1, 8) for m in range(-1, 8) if n > m),
        *(
            Sentence.fact(Relation.plus(n, m, o))
            for n in range(-1, 8)
            for m in range(-1, 8)
            for o in range(-1, 8)
            if n + m == o
        ),
        # Next
        Sentence.rule(
            Relation.next(Relation.control(_R1)),
            (
                Literal(Relation.role(_R1)),
                Literal(Relation.role(_R2)),
                Literal(Relation.distinct(_R1, _R2)),
                Literal(Relation.true(Relation.control(_R2))),
                Literal(Relation.true(Relation("pile", (Relation("size", (_S2,)),)))),
                Literal(Relation.plus(_S1, _S, _S2)),
                Literal(Relation.does(_R2, Relation("take", (_S,)))),
                Literal(Relation.gt(_S1, 0)),
            ),
        ),
        Sentence.rule(
            Relation.next(Relation.control(_R)),
            (
                Literal(Relation.role(_R)),
                Literal(Relation.true(Relation.control(_R))),
                Literal(Relation.true(Relation("pile", (Relation("size", (_S,)),)))),
                Literal(Relation.does(_R, Relation("take", (_S,)))),
            ),
        ),
        Sentence.rule(
            Relation.next(Relation("pile", (Relation("size", (_S1,)),))),
            (
                Literal(Relation.role(_R)),
                Literal(Relation.true(Relation("pile", (Relation("size", (_S2,)),)))),
                Literal(Relation.does(_R, Relation("take", (_S,)))),
                Literal(Relation.plus(_S1, _S, _S2)),
            ),
        ),
        # Sees
        # Legal
        Sentence.rule(
            Relation.legal(_R, Relation("take", (_S,))),
            (
                Literal(Relation.role(_R)),
                Literal(Relation.true(Relation("pile", (Relation("size", (_S2,)),)))),
                Literal(Relation.plus(_S1, _S, _S2)),
                Literal(Relation.gt(_S, 0)),
                Literal(Relation.gt(4, _S)),
                Literal(Relation.gt(_S1, -1)),
            ),
        ),
        # Goal
        Sentence.rule(
            Relation.goal(_R, 0),
            (
                Literal(Relation.role(_R)),
                Literal(Relation.true(Relation("pile", (Relation("size", (0,)),)))),
                -Literal(Relation.true(Relation.control(_R))),
            ),
        ),
        Sentence.rule(
            Relation.goal(_R, 1),
            (
                Literal(Relation.role(_R)),
                Literal(Relation.true(Relation("pile", (Relation("size", (0,)),)))),
                Literal(Relation.true(Relation.control(_R))),
            ),
        ),
        # Terminal
        Sentence.rule(
            Relation.terminal(),
            (Literal(Relation.true(Relation("pile", (Relation("size", (0,)),)))),),
        ),
    )
)

_x = Relation("x")
_o = Relation("o")


def _cell(*args: Subrelation) -> Relation:
    return Relation("cell", args)


# pylint: disable=invalid-name
def _row(m: Union[int, Variable], p: Subrelation) -> Relation:
    return Relation("row", (m, p))


# pylint: disable=invalid-name
def _column(n: Union[int, Variable], p: Subrelation) -> Relation:
    return Relation("column", (n, p))


# pylint: disable=invalid-name
def _diagonal(p: Subrelation) -> Relation:
    return Relation("diagonal", (p,))


# pylint: disable=invalid-name
def _line(p: Subrelation) -> Relation:
    return Relation("line", (p,))


_open = Relation("open")

_M = Variable("M")
__M = Variable("_M")
_N = Variable("N")
__N = Variable("_N")
_P = Variable("P")
__P = Variable("_P")
_P1 = Variable("P1")
_P2 = Variable("P2")

tic_tac_toe_ruleset: Ruleset = Ruleset(
    (
        # Role
        Sentence.fact(Relation.role(_x)),
        Sentence.fact(Relation.role(_o)),
        # Init
        Sentence.fact(Relation.init(Relation.control(_x))),
        # Helpers
        *(Sentence.fact(_cell(m, n)) for n in range(1, 4) for m in range(1, 4)),
        Sentence.rule(
            _row(_M, _P),
            (
                Literal(Relation.role(_P)),
                *(Literal(_cell(_M, n)) for n in range(1, 4)),
                *(Literal(Relation.true(_cell(_M, n, _P))) for n in range(1, 4)),
            ),
        ),
        Sentence.rule(
            _column(_N, _P),
            (
                Literal(Relation.role(_P)),
                *(Literal(_cell(m, _N)) for m in range(1, 4)),
                *(Literal(Relation.true(_cell(m, _N, _P))) for m in range(1, 4)),
            ),
        ),
        Sentence.rule(
            _diagonal(_P),
            (
                Literal(Relation.role(_P)),
                Literal(_cell(1, 1)),
                Literal(_cell(2, 2)),
                Literal(_cell(3, 3)),
                Literal(Relation.true(_cell(1, 1, _P))),
                Literal(Relation.true(_cell(2, 2, _P))),
                Literal(Relation.true(_cell(3, 3, _P))),
            ),
        ),
        Sentence.rule(
            _diagonal(_P),
            (
                Literal(Relation.role(_P)),
                Literal(_cell(1, 3)),
                Literal(_cell(2, 2)),
                Literal(_cell(3, 1)),
                Literal(Relation.true(_cell(1, 3, _P))),
                Literal(Relation.true(_cell(2, 2, _P))),
                Literal(Relation.true(_cell(3, 1, _P))),
            ),
        ),
        Sentence.rule(
            _line(_P),
            (
                Literal(Relation.role(_P)),
                Literal(_row(__M, _P)),
            ),
        ),
        Sentence.rule(
            _line(_P),
            (
                Literal(Relation.role(_P)),
                Literal(_column(__N, _P)),
            ),
        ),
        Sentence.rule(
            _line(_P),
            (
                Literal(Relation.role(_P)),
                Literal(_diagonal(_P)),
            ),
        ),
        Sentence.rule(
            _open,
            (
                Literal(_cell(_M, _N)),
                -Literal(Relation.true(_cell(_M, _N, __P))),
            ),
        ),
        # Next
        Sentence.rule(
            Relation.next(_cell(_M, _N, _P)),
            (Literal(Relation.role(_P)), Literal(_cell(_M, _N)), Literal(Relation.does(_P, _cell(_M, _N)))),
        ),
        Sentence.rule(
            Relation.next(_cell(_M, _N, _P)),
            (Literal(Relation.role(_P)), Literal(_cell(_M, _N)), Literal(Relation.true(_cell(_M, _N, _P)))),
        ),
        Sentence.rule(
            Relation.next(Relation.control(_P1)),
            (
                Literal(Relation.role(_P1)),
                Literal(Relation.role(_P2)),
                Literal(Relation.distinct(_P1, _P2)),
                Literal(_open),
                Literal(Relation.true(Relation.control(_P2))),
            ),
        ),
        # Legal
        Sentence.rule(
            Relation.legal(_P, _cell(_M, _N)),
            (Literal(Relation.role(_P)), Literal(_cell(_M, _N)), -Literal(Relation.true(_cell(_M, _N, __P)))),
        ),
        # Goal
        Sentence.rule(
            Relation.goal(_P1, 0),
            (
                Literal(Relation.role(_P1)),
                Literal(Relation.role(_P2)),
                Literal(Relation.distinct(_P1, _P2)),
                Literal(_line(_P2)),
            ),
        ),
        Sentence.rule(
            Relation.goal(_P1, 50),
            (
                Literal(Relation.role(_P1)),
                Literal(Relation.role(_P2)),
                Literal(Relation.distinct(_P1, _P2)),
                -Literal(_line(_P1)),
                -Literal(_line(_P2)),
                -Literal(_open),
            ),
        ),
        Sentence.rule(
            Relation.goal(_P, 100),
            (
                Literal(Relation.role(_P)),
                Literal(_line(_P)),
            ),
        ),
        # Terminal
        Sentence.rule(
            Relation.terminal(),
            (Literal(Relation.role(_P)), Literal(_line(_P))),
        ),
        Sentence.rule(
            Relation.terminal(),
            (-Literal(_open),),
        ),
    )
)

_C = Variable("C")
_C1 = Variable("C1")
_C2 = Variable("C2")
__C1 = Variable("_C1")
__C2 = Variable("_C2")

rock_paper_scissors_ruleset: Ruleset = Ruleset(
    (
        # Role
        Sentence.fact(
            Relation.role(Relation("left")),
        ),
        Sentence.fact(
            Relation.role(Relation("right")),
        ),
        # Init
        Sentence.fact(Relation.init(Relation.control(Relation("left")))),
        Sentence.fact(Relation.init(Relation.control(Relation("right")))),
        # Helpers
        *(
            Sentence.fact(
                Relation("choice", (Relation(face),)),
            )
            for face in ("rock", "paper", "scissors")
        ),
        Sentence.fact(Relation("beats", (Relation("rock"), Relation("scissors")))),
        Sentence.fact(Relation("beats", (Relation("paper"), Relation("rock")))),
        Sentence.fact(Relation("beats", (Relation("scissors"), Relation("paper")))),
        # Next
        Sentence.rule(
            Relation.next(Relation("chose", (_R, _C))),
            (Literal(Relation.role(_R)), Literal(Relation("choice", (_C,))), Literal(Relation.does(_R, _C))),
        ),
        Sentence.rule(
            Relation.next(Relation("chose", (_R, _C))),
            (
                Literal(Relation.role(_R)),
                Literal(Relation("choice", (_C,))),
                Literal(Relation.true(Relation("chose", (_R, _C)))),
            ),
        ),
        # Legal
        Sentence.rule(Relation.legal(_R, _C), (Literal(Relation.role(_R)), Literal(Relation("choice", (_C,))))),
        # Goal
        Sentence.rule(
            Relation.goal(_R1, 0),
            (
                Literal(Relation.role(_R1)),
                Literal(Relation.role(_R2)),
                Literal(Relation("choice", (_C1,))),
                Literal(Relation("choice", (_C2,))),
                Literal(Relation.distinct(_R1, _R2)),
                Literal(Relation.distinct(_C1, _C2)),
                Literal(Relation.true(Relation("chose", (_R1, _C1)))),
                Literal(Relation.true(Relation("chose", (_R2, _C2)))),
                -Literal(Relation("beats", (_C1, _C2))),
            ),
        ),
        Sentence.rule(
            Relation.goal(_R1, 50),
            (
                Literal(Relation.role(_R1)),
                Literal(Relation.role(_R2)),
                Literal(Relation("choice", (_C,))),
                Literal(Relation.distinct(_R1, _R2)),
                Literal(Relation.true(Relation("chose", (_R1, _C)))),
                Literal(Relation.true(Relation("chose", (_R2, _C)))),
            ),
        ),
        Sentence.rule(
            Relation.goal(_R1, 100),
            (
                Literal(Relation.role(_R1)),
                Literal(Relation.role(_R2)),
                Literal(Relation("choice", (_C1,))),
                Literal(Relation("choice", (_C2,))),
                Literal(Relation.distinct(_R1, _R2)),
                Literal(Relation.distinct(_C1, _C2)),
                Literal(Relation.true(Relation("chose", (_R1, _C1)))),
                Literal(Relation.true(Relation("chose", (_R2, _C2)))),
                Literal(Relation("beats", (_C1, _C2))),
            ),
        ),
        # Terminal
        Sentence.rule(
            Relation.terminal(),
            (
                Literal(Relation.role(_R1)),
                Literal(Relation.role(_R2)),
                Literal(Relation.distinct(_R1, _R2)),
                Literal(Relation.true(Relation("chose", (_R1, __C1)))),
                Literal(Relation.true(Relation("chose", (_R2, __C2)))),
            ),
        ),
    )
)

_X = Variable("X")
__C = Variable("_C")
_Everyone = Variable("Everyone")

minipoker_ruleset: Ruleset = Ruleset(
    (
        # Role
        Sentence.fact(
            Relation.role(Relation("bluffer")),
        ),
        Sentence.fact(
            Relation.role(Relation("caller")),
        ),
        Sentence.fact(
            Relation.role(Relation.random()),
        ),
        # Init
        Sentence.fact(Relation.init(Relation.control(Relation.random()))),
        # Helpers
        Sentence.fact(Relation("colour", (Relation("red"),))),
        Sentence.fact(Relation("colour", (Relation("black"),))),
        # Next
        Sentence.rule(
            Relation.next(Relation("dealt")), (Literal(Relation.does(Relation.random(), Relation("deal", (__C,)))),)
        ),
        Sentence.rule(Relation.next(Relation("dealt")), (Literal(Relation.true(Relation("dealt"))),)),
        Sentence.rule(
            Relation.next(Relation("dealt", (_C,))),
            (
                Literal(Relation("colour", (_C,))),
                Literal(Relation.does(Relation.random(), Relation("deal", (_C,)))),
            ),
        ),
        Sentence.rule(
            Relation.next(Relation("dealt", (_C,))),
            (
                Literal(Relation("colour", (_C,))),
                Literal(Relation.true(Relation("dealt", (_C,)))),
            ),
        ),
        Sentence.rule(
            Relation.next(Relation.control(Relation("bluffer"))),
            (Literal(Relation.does(Relation.random(), Relation("deal", (__C,)))),),
        ),
        Sentence.rule(
            Relation.next(Relation("resigned", (Relation("bluffer"),))),
            (Literal(Relation.does(Relation("bluffer"), Relation("resign"))),),
        ),
        Sentence.rule(
            Relation.next(Relation("resigned", (Relation("bluffer"),))),
            (Literal(Relation.true(Relation("resigned", (Relation("bluffer"),)))),),
        ),
        Sentence.rule(
            Relation.next(Relation("held", (Relation("bluffer"),))),
            (Literal(Relation.does(Relation("bluffer"), Relation("hold"))),),
        ),
        Sentence.rule(
            Relation.next(Relation("held", (Relation("bluffer"),))),
            (Literal(Relation.true(Relation("held", (Relation("bluffer"),)))),),
        ),
        Sentence.rule(
            Relation.next(Relation.control(Relation("caller"))),
            (Literal(Relation.does(Relation("bluffer"), Relation("hold"))),),
        ),
        Sentence.rule(
            Relation.next(Relation("resigned", (Relation("caller"),))),
            (Literal(Relation.does(Relation("caller"), Relation("resign"))),),
        ),
        Sentence.rule(
            Relation.next(Relation("resigned", (Relation("caller"),))),
            (Literal(Relation.true(Relation("resigned", (Relation("caller"),)))),),
        ),
        Sentence.rule(
            Relation.next(Relation("called", (Relation("caller"),))),
            (Literal(Relation.does(Relation("caller"), Relation("call"))),),
        ),
        Sentence.rule(
            Relation.next(Relation("called", (Relation("caller"),))),
            (Literal(Relation.true(Relation("called", (Relation("caller"),)))),),
        ),
        # Sees
        Sentence.rule(
            Relation.sees(Relation.random(), _X),
            (Literal(Relation.true(_X)),),
        ),
        Sentence.rule(
            Relation.sees(_Everyone, Relation.control(_R)),
            (
                Literal(Relation.role(_Everyone)),
                Literal(Relation.role(_R)),
                Literal(Relation.true(Relation.control(_R))),
            ),
        ),
        Sentence.rule(
            Relation.sees(_Everyone, Relation("dealt")),
            (Literal(Relation.role(_Everyone)), Literal(Relation.true(Relation("dealt")))),
        ),
        Sentence.rule(
            Relation.sees(_Everyone, Relation("resigned", (_R,))),
            (
                Literal(Relation.role(_Everyone)),
                Literal(Relation.role(_R)),
                Literal(Relation.true(Relation("resigned", (_R,)))),
            ),
        ),
        Sentence.rule(
            Relation.sees(_Everyone, Relation("held", (_R,))),
            (
                Literal(Relation.role(_Everyone)),
                Literal(Relation.role(_R)),
                Literal(Relation.true(Relation("held", (_R,)))),
            ),
        ),
        Sentence.rule(
            Relation.sees(_Everyone, Relation("called", (_R,))),
            (
                Literal(Relation.role(_Everyone)),
                Literal(Relation.role(_R)),
                Literal(Relation.true(Relation("called", (_R,)))),
            ),
        ),
        Sentence.rule(
            Relation.sees(_Everyone, Relation("dealt", (_C,))),
            (
                Literal(Relation.role(_Everyone)),
                Literal(Relation("colour", (_C,))),
                Literal(Relation.true(Relation("dealt", (_C,)))),
                Literal(Relation.true(Relation("called", (Relation("caller"),)))),
            ),
        ),
        Sentence.rule(
            Relation.sees(Relation("bluffer"), Relation("dealt", (_C,))),
            (
                Literal(Relation("colour", (_C,))),
                Literal(Relation.true(Relation("dealt", (_C,)))),
            ),
        ),
        # Legal
        Sentence.rule(
            Relation.legal(Relation.random(), Relation("deal", (_C,))),
            (Literal(Relation("colour", (_C,))),),
        ),
        Sentence.rule(
            Relation.legal(Relation("bluffer"), Relation("resign")),
            (Literal(Relation.true(Relation("dealt", (Relation("red"),)))),),
        ),
        Sentence.fact(
            Relation.legal(Relation("bluffer"), Relation("hold")),
        ),
        Sentence.fact(
            Relation.legal(Relation("caller"), Relation("resign")),
        ),
        Sentence.fact(
            Relation.legal(Relation("caller"), Relation("call")),
        ),
        # Goal
        Sentence.rule(
            Relation.goal(Relation("bluffer"), -10),
            (Literal(Relation.true(Relation("resigned", (Relation("bluffer"),)))),),
        ),
        Sentence.rule(
            Relation.goal(Relation("caller"), 10),
            (Literal(Relation.true(Relation("resigned", (Relation("bluffer"),)))),),
        ),
        Sentence.rule(
            Relation.goal(Relation("bluffer"), 4),
            (Literal(Relation.true(Relation("resigned", (Relation("caller"),)))),),
        ),
        Sentence.rule(
            Relation.goal(Relation("caller"), -4),
            (Literal(Relation.true(Relation("resigned", (Relation("caller"),)))),),
        ),
        Sentence.rule(
            Relation.goal(Relation("bluffer"), 16),
            (
                Literal(Relation.true(Relation("dealt", (Relation("black"),)))),
                Literal(Relation.true(Relation("held", (Relation("bluffer"),)))),
                Literal(Relation.true(Relation("called", (Relation("caller"),)))),
            ),
        ),
        Sentence.rule(
            Relation.goal(Relation("caller"), -16),
            (
                Literal(Relation.true(Relation("dealt", (Relation("black"),)))),
                Literal(Relation.true(Relation("held", (Relation("bluffer"),)))),
                Literal(Relation.true(Relation("called", (Relation("caller"),)))),
            ),
        ),
        Sentence.rule(
            Relation.goal(Relation("bluffer"), -20),
            (
                Literal(Relation.true(Relation("dealt", (Relation("red"),)))),
                Literal(Relation.true(Relation("held", (Relation("bluffer"),)))),
                Literal(Relation.true(Relation("called", (Relation("caller"),)))),
            ),
        ),
        Sentence.rule(
            Relation.goal(Relation("caller"), 20),
            (
                Literal(Relation.true(Relation("dealt", (Relation("red"),)))),
                Literal(Relation.true(Relation("held", (Relation("bluffer"),)))),
                Literal(Relation.true(Relation("called", (Relation("caller"),)))),
            ),
        ),
        # Terminal
        Sentence.rule(
            Relation.terminal(),
            (Literal(Relation.true(Relation("resigned", (Relation("bluffer"),)))),),
        ),
        Sentence.rule(
            Relation.terminal(),
            (Literal(Relation.true(Relation("resigned", (Relation("caller"),)))),),
        ),
        Sentence.rule(
            Relation.terminal(),
            (
                Literal(Relation.true(Relation("held", (Relation("bluffer"),)))),
                Literal(Relation.true(Relation("called", (Relation("caller"),)))),
            ),
        ),
    )
)
