import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Role, View
from pyggp.interpreters import ClingoInterpreter

gravity_connect_7_6_4_rules_str: str = """
role(red). role(yellow).

init(control(yellow)).

color(Color) :- role(Color).
row(1). row(2). row(3). row(4). row(5). row(6).
col(1). col(2). col(3). col(4). col(5). col(6). col(7).
win(4).

succ(0, 1). succ(1, 2). succ(2, 3). succ(3, 4). succ(4, 5). succ(5, 6). succ(6,7). succ(7,8).

next(control(R1)) :-
    role(R1), role(R2), distinct(R1,R2),
    true(control(R2)),
    does(R2, _Col).

next(cell(Row,Col,Role)) :-
    row(Row), col(Col), role(Role),
    true(cell(Row,Col,Role)).

next(cell(1,Col,Role)) :-
    col(Col), role(Role),
    not true(cell(1,Col,_)),
    does(Role,Col).

next(cell(Row2, Col, Role)) :-
    row(Row2), col(Col), role(Role),
    row(Row1),
    succ(Row1, Row2),
    true(cell(Row1,Col,Color)),
    not true(cell(Row2,Col,_)),
    does(Role, Col).

legal(Role, Col) :-
    role(Role), col(Col),
    row(Row1), succ(Row1, Row2), not row(Row2),
    not true(cell(Row1,Col,_)).

open :-
    row(Row), col(Col),
    not true(cell(Row,Col,_)).

connects(Role, Row1, Col, Row2, Col, 2) :-
    role(Role), row(Row1), row(Row2), col(Col),
    succ(Row1, Row2),
    true(cell(Row1,Col,Role)),
    true(cell(Row2,Col,Role)).

connects(Role, Row1, Col, Row2, Col, N) :-
    role(Role), row(Row1), row(Row2), col(Col),
    row(Row0),
    succ(M, N), succ(Row0, Row1), succ(Row1, Row2),
    true(cell(Row1,Col,Role)),
    true(cell(Row2,Col,Role)),
    connects(Role, Row0, Col, Row1, Col, M).


connects(Role, Row, Col1, Row, Col2, 2) :-
    role(Role), row(Row), col(Col1), col(Col2),
    succ(Col1, Col2),
    true(cell(Row,Col1,Role)),
    true(cell(Row,Col2,Role)).

connects(Role, Row, Col1, Row, Col2, N) :-
    role(Role), row(Row), col(Col1), col(Col2),
    col(Col0),
    succ(M, N), succ(Col0, Col1), succ(Col1, Col2),
    true(cell(Row,Col1,Role)),
    true(cell(Row,Col2,Role)),
    connects(Role, Row, Col0, Row, Col1, M).


connects(Role, Row1, Col1, Row2, Col2, 2) :-
    role(Role), row(Row1), row(Row2), col(Col1), col(Col2),
    succ(Row1, Row2), succ(Col1, Col2),
    true(cell(Row1,Col1,Role)),
    true(cell(Row2,Col2,Role)).

connects(Role, Row1, Col1, Row2, Col2, N) :-
    role(Role), row(Row1), row(Row2), col(Col1), col(Col2),
    row(Row0), col(Col0),
    succ(M, N),
    succ(Row0, Row1), succ(Row1, Row2),
    succ(Col0, Col1), succ(Col1, Col2),
    true(cell(Row1,Col1,Role)),
    true(cell(Row2,Col2,Role)),
    connects(Role, Row0, Col0, Row1, Col1, M).


connects(Role, Row2, Col1, Row1, Col2, 2) :-
    role(Role), row(Row1), row(Row2), col(Col1), col(Col2),
    succ(Row1, Row2), succ(Col1, Col2),
    true(cell(Row1,Col2,Role)),
    true(cell(Row2,Col1,Role)).

connects(Role, Row3, Col1, Row2, Col2, N) :-
    role(Role),
    row(Row1), row(Row2), row(Row3),
    col(Col1), col(Col2), col(Col3),
    succ(M, N),
    succ(Row1, Row2), succ(Row2, Row3),
    succ(Col1, Col2), succ(Col2, Col3),
    true(cell(Row3,Col1,Role)),
    true(cell(Row2,Col2,Role)),
    connects(Role, Row2, Col2, Row1, Col3, M).


line(Role) :-
    role(Role),
    connects(Role, _Row1, _Col1, _Row2, _Col2, N),
    win(N).

goal(Role1, 0) :-
    role(Role1), role(Role2), distinct(Role1, Role2),
    line(Role2).

goal(Role1, 50) :-
    role(Role1), role(Role2), distinct(Role1, Role2),
    not open,
    not line(Role1),
    not line(Role2).

goal(Role1, 100) :-
    role(Role1),
    line(Role1).

terminal :-
    not open.

terminal :-
    line(_Role).
"""

gravity_connect_7_6_4_ruleset = gdl.transformer.transform(gdl.parser.parse(gravity_connect_7_6_4_rules_str))

gravity_connect_7_6_4_interpreter = ClingoInterpreter.from_ruleset(gravity_connect_7_6_4_ruleset)

gravity_connect_7_6_4_init_state = gravity_connect_7_6_4_interpreter.get_init_state()
gravity_connect_7_6_4_init_view = View(gravity_connect_7_6_4_init_state)

gravity_connect_7_6_4_yellow = Role(gdl.Subrelation(gdl.Relation("yellow")))
