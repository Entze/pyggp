import pyggp.game_description_language as gdl
from pyggp.agents.tree_agents.nodes import HiddenInformationSetNode, VisibleInformationSetNode
from pyggp.engine_primitives import Move, Turn

from prof.prof_common_phantom_connect_5_6_4 import (
    phantom_connect_5_6_4_init_state,
    phantom_connect_5_6_4_interpreter,
    phantom_connect_5_6_4_role_o,
    phantom_connect_5_6_4_role_x,
)

state_0 = phantom_connect_5_6_4_init_state
x = phantom_connect_5_6_4_role_x
o = phantom_connect_5_6_4_role_o
interpreter = phantom_connect_5_6_4_interpreter

tree_x = VisibleInformationSetNode(
    possible_states={state_0},
    role=x,
)
tree_o = HiddenInformationSetNode(
    possible_states={state_0},
    role=o,
)

view_0 = interpreter.get_sees_by_role(state_0, x)

print("Step 0")

tree_x = tree_x.develop(interpreter, 0, view_0)

cell_3_3 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(3)), gdl.Subrelation(gdl.Number(3))))))
state_1 = interpreter.get_next_state(state_0, *Turn({x: cell_3_3}).as_plays())
view_1 = interpreter.get_sees_by_role(state_1, o)
tree_x.move = cell_3_3

print("Step 1")

tree_o = tree_o.develop(interpreter, 1, view_1)

cell_2_1 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(2)), gdl.Subrelation(gdl.Number(1))))))
state_2 = interpreter.get_next_state(
    state_1,
    *Turn({o: cell_2_1}).as_plays(),
)
view_2 = interpreter.get_sees_by_role(state_2, x)
tree_o.move = cell_2_1

print("Step 2")

tree_x = tree_x.develop(interpreter, 2, view_2)

cell_2_5 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(2)), gdl.Subrelation(gdl.Number(5))))))
state_3 = interpreter.get_next_state(
    state_2,
    *Turn({x: cell_2_5}).as_plays(),
)
view_3 = interpreter.get_sees_by_role(state_3, o)
tree_x.move = cell_2_5

print("Step 3")

tree_o = tree_o.develop(interpreter, 3, view_3)

cell_3_6 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(3)), gdl.Subrelation(gdl.Number(6))))))
state_4 = interpreter.get_next_state(
    state_3,
    *Turn({o: cell_3_6}).as_plays(),
)
view_4 = interpreter.get_sees_by_role(state_4, x)
tree_o.move = cell_3_6

print("Step 4")

tree_x.develop(interpreter, 4, view_4)

cell_1_3 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(1)), gdl.Subrelation(gdl.Number(3))))))
state_5 = interpreter.get_next_state(
    state_4,
    *Turn({x: cell_1_3}).as_plays(),
)
view_5 = interpreter.get_sees_by_role(state_5, o)
tree_x.move = cell_1_3

print("Step 5")

tree_o = tree_o.develop(interpreter, 5, view_5)
