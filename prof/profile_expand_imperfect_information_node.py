import pyggp.game_description_language as gdl
from pyggp.agents.tree_agents.nodes import PerfectInformationNode, VisibleInformationSetNode
from pyggp.engine_primitives import Role, View
from pyggp.interpreters import ClingoInterpreter
from tqdm import tqdm

tic_tac_toe_rules_str = """
role(x). role(o).

init(control(x)).

cell(1, 1). cell(2, 1). cell(3, 1).
cell(1, 2). cell(2, 2). cell(3, 2).
cell(1, 3). cell(2, 3). cell(3, 3).

row(M, P) :-
    role(P),
    cell(M, 1), cell(M, 2), cell(M, 3),
    true(cell(M, 1, P)),
    true(cell(M, 2, P)),
    true(cell(M, 3, P)).

column(N, P) :-
    role(P),
    cell(1, N), cell(2, N), cell(3, N),
    true(cell(1, N, P)),
    true(cell(2, N, P)),
    true(cell(3, N, P)).

diagonal(P) :-
    role(P),
    cell(1, 1), cell(2, 2), cell(3, 3),
    true(cell(1, 1, P)),
    true(cell(2, 2, P)),
    true(cell(3, 3, P)).

diagonal(P) :-
    role(P),
    cell(1, 3), cell(2, 2), cell(3, 1),
    true(cell(1, 3, P)),
    true(cell(2, 2, P)),
    true(cell(3, 1, P)).

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
    not true(cell(M, N, _P)).

next(cell(M, N, P)) :-
    role(P),
    cell(M, N),
    does(P, cell(M, N)).

next(cell(M, N, P)) :-
    role(P),
    cell(M, N),
    true(cell(M, N, P)).

next(control(P1)) :-
    role(P1), role(P2),
    distinct(P1, P2),
    open,
    true(control(P2)).

legal(P, cell(M, N)) :-
    role(P),
    cell(M, N),
    not true(cell(M, N, _P)).

goal(P1, 0) :-
    role(P1), role(P2), distinct(P1, P2),
    line(P2).

goal(P1, 50) :-
    role(P1), role(P2), distinct(P1, P2),
    not line(P1), not line(P2),
    not open.

goal(P, 100) :-
    role(P), line(P).

terminal :-
    role(P),
    line(P).

terminal :-
    not open.
"""

tic_tac_toe_ruleset = gdl.transformer.transform(gdl.parser.parse(tic_tac_toe_rules_str))

interpreter = ClingoInterpreter.from_ruleset(tic_tac_toe_ruleset)

init_state = interpreter.get_init_state()
init_view = View(init_state)

role = Role(gdl.Subrelation(gdl.Relation("x")))

tree = VisibleInformationSetNode(
    role=role,
    possible_states={init_state},
    view=init_view,
)

stack = [tree]

with tqdm() as pbar:
    while stack:
        node = stack.pop()
        node.expand(interpreter)
        if node.depth < 5:
            stack.extend(node.unique_children)
        pbar.update(1)
