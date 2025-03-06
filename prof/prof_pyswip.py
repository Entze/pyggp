import collections
import contextlib
import pathlib
import tempfile

import pyswip
import tqdm

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Move, Role, State

rules = r"""role(x).
role(o).

init(control(x)).

cell(1, 1). cell(2, 1). cell(3, 1).
cell(1, 2). cell(2, 2). cell(3, 2).
cell(1, 3). cell(2, 3). cell(3, 3).

row(M, P) :-
    role(P), cell(M, 1), cell(M, 2), cell(M, 3),
    true(cell(M, 1, P)), true(cell(M, 2, P)), true(cell(M, 3, P)).
column(N, P) :-
    role(P), cell(1, N), cell(2, N), cell(3, N),
    true(cell(1, N, P)), true(cell(2, N, P)), true(cell(3, N, P)).
diagonal(P) :-
    role(P), cell(1, 1), cell(2, 2), cell(3, 3),
    true(cell(1, 1, P)), true(cell(2, 2, P)), true(cell(3, 3, P)).
diagonal(P) :-
    role(P), cell(1, 3), cell(2, 2), cell(3, 1),
    true(cell(1, 3, P)), true(cell(2, 2, P)), true(cell(3, 1, P)).
line(P) :-
    role(P),
    row(_M, P).
line(P) :-
    role(P),
    column(_N, P).
line(P) :-
    role(P),
    diagonal(P).

open :-
    cell(M, N),
    \+ true(cell(M, N, _P)).

next(cell(M, N, P)) :-
    role(P), cell(M, N),
    does(P, cell(M, N)).

next(cell(M, N, P)) :-
    role(P), cell(M, N),
    true(cell(M, N, P)).

next(control(P1)) :-
    role(P1), role(P2), P1 \= P2,
    open, true(control(P2)).

legal(P, cell(M, N)) :-
    role(P), cell(M, N),
    \+ true(cell(M, N, _P)).


goal(P1, 0) :-
    role(P1), role(P2), P1 \= P2,
    line(P2).

goal(P1, 50) :-
    role(P1), role(P2), P1 \= P2,
    \+ line(P1), \+ line(P2), \+ open.

goal(P, 100) :-
    role(P),
    line(P).

terminal :-
    role(P),
    line(P).
terminal :- \+ open.

"""


def result_to_gdl(__res, varname: str = "T"):
    yield from (gdl.parse_subrelation(solution[varname]) for solution in result)


@contextlib.contextmanager
def assert_state(knowledgebase: pyswip.Prolog, state: State) -> None:
    try:
        for subrelation in state:
            assert_subrelation(knowledgebase, subrelation, functor="true")
        yield
    finally:
        retract_subrelations(knowledgebase, functor="true", arity=1)


@contextlib.contextmanager
def assert_move(knowledgebase: pyswip.Prolog, role: Role, move: Move) -> None:
    try:
        assert_subrelation(knowledgebase, role, move, functor="does")
        yield
    finally:
        retract_subrelations(knowledgebase, functor="does", arity=2)


def assert_subrelation(knowledgedb: pyswip.Prolog, *subrelations: gdl.Subrelation, functor: str = "true") -> None:
    assert_statement = f"{functor}({','.join(str(subrelation) for subrelation in subrelations)})"
    knowledgedb.assertz(assert_statement)


def retract_subrelations(knowledgedb: pyswip.Prolog, *, functor: str = "true", arity: int = 1) -> None:
    if arity == 0:
        knowledgedb.retract(f"{functor}")
    knowledgedb.retractall(f"{functor}({','.join('_' for _ in range(arity))})")


with tempfile.TemporaryDirectory() as td:
    file = pathlib.Path(td).joinpath("prolog.pl")
    with open(file, "w") as fp:
        fp.write(rules)
    prolog = pyswip.Prolog()
    prolog.consult(str(file))

query = "init(T)."
result = prolog.query(query)
init_state = State(frozenset(result_to_gdl(result)))

states = collections.deque((init_state,))

searched = 0
max_search = 10_000

with tqdm.tqdm(total=max_search) as pbar:
    while states and searched < max_search:
        searched += 1
        pbar.update(1)
        current = states.popleft()
        with assert_state(prolog, current):
            query = "terminal."
            result = prolog.query(query)
            if any(result):
                continue
            query = "true(control(T))."
            result = prolog.query(query)
            roles_in_control = frozenset(Role(role) for role in result_to_gdl(result))
            in_control = next(iter(roles_in_control))
            query = f"legal({in_control},T)."
            result = prolog.query(query)
            legal_moves = frozenset(Move(move) for move in result_to_gdl(result))
            for move in legal_moves:
                with assert_move(prolog, in_control, move):
                    query = "next(T)."
                    result = prolog.query(query)
                    next_state = State(frozenset(result_to_gdl(result)))
                    states.append(next_state)
