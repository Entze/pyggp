import pyggp.game_description_language as gdl
from prof.prof_common_phantom_connect_5_6_4 import (
    phantom_connect_5_6_4_init_state,
    phantom_connect_5_6_4_interpreter,
    phantom_connect_5_6_4_role_o,
    phantom_connect_5_6_4_role_x,
)
from pyggp.agents.tree_agents.nodes import HiddenInformationSetNode, VisibleInformationSetNode
from pyggp.engine_primitives import Move, Turn

cell_1_3 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(1)), gdl.Subrelation(gdl.Number(3))))))
cell_2_2 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(2)), gdl.Subrelation(gdl.Number(2))))))
cell_2_6 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(2)), gdl.Subrelation(gdl.Number(6))))))
cell_3_1 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(3)), gdl.Subrelation(gdl.Number(1))))))
cell_3_2 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(3)), gdl.Subrelation(gdl.Number(2))))))
cell_3_3 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(3)), gdl.Subrelation(gdl.Number(3))))))
cell_3_4 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(3)), gdl.Subrelation(gdl.Number(4))))))
cell_3_5 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(3)), gdl.Subrelation(gdl.Number(5))))))
cell_3_6 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(3)), gdl.Subrelation(gdl.Number(6))))))
cell_5_5 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(5)), gdl.Subrelation(gdl.Number(5))))))
cell_5_1 = Move(gdl.Subrelation(gdl.Relation("cell", (gdl.Subrelation(gdl.Number(5)), gdl.Subrelation(gdl.Number(1))))))

move_0 = cell_3_4
move_1 = cell_5_5
move_2 = cell_3_2
move_3 = cell_5_1
move_4 = cell_2_2
move_5 = cell_3_6
move_6 = cell_3_5
move_7 = cell_1_3
move_8 = cell_5_1

state_0 = phantom_connect_5_6_4_init_state
x = phantom_connect_5_6_4_role_x
o = phantom_connect_5_6_4_role_o
interpreter = phantom_connect_5_6_4_interpreter

tree_x = VisibleInformationSetNode(
    possible_states={state_0},
    role=x,
    fully_enumerated=True,
)
tree_o = HiddenInformationSetNode(
    possible_states={state_0},
    role=o,
    fully_enumerated=True,
)

view_0 = interpreter.get_sees_by_role(state_0, x)

print(f"Step 0 {len(tree_x.possible_states)}")

tree_x = tree_x.develop(interpreter, 0, view_0)


state_1 = interpreter.get_next_state(state_0, Turn({x: move_0}))
view_1 = interpreter.get_sees_by_role(state_1, o)
tree_x.move = move_0

print(f"Step 1 {len(tree_o.possible_states)}")

tree_o = tree_o.develop(interpreter, 1, view_1)

state_2 = interpreter.get_next_state(
    state_1,
    Turn({o: move_1}),
)
view_2 = interpreter.get_sees_by_role(state_2, x)
tree_o.move = move_1

print(f"Step 2 {len(tree_x.possible_states)}")

tree_x = tree_x.develop(interpreter, 2, view_2)

state_3 = interpreter.get_next_state(
    state_2,
    Turn({x: move_2}),
)
view_3 = interpreter.get_sees_by_role(state_3, o)
tree_x.move = move_2

print(f"Step 3 {len(tree_o.possible_states)}")

tree_o = tree_o.develop(interpreter, 3, view_3)

state_4 = interpreter.get_next_state(
    state_3,
    Turn({o: move_3}),
)
view_4 = interpreter.get_sees_by_role(state_4, x)
tree_o.move = move_3

print(f"Step 4 { len(tree_x.possible_states)}")

tree_x = tree_x.develop(interpreter, 4, view_4)

state_5 = interpreter.get_next_state(
    state_4,
    Turn({x: move_4}),
)
view_5 = interpreter.get_sees_by_role(state_5, o)
tree_x.move = move_4

print(f"Step 5 {len(tree_o.possible_states)}")

tree_o = tree_o.develop(interpreter, 5, view_5)

state_6 = interpreter.get_next_state(state_5, Turn({o: move_5}))
view_6 = interpreter.get_sees_by_role(state_6, x)
tree_o.move = move_5

print(f"Step 6 {len(tree_x.possible_states)}")

tree_x = tree_x.develop(interpreter, 6, view_6)

state_7 = interpreter.get_next_state(
    state_6,
    Turn({x: move_6}),
)
view_7 = interpreter.get_sees_by_role(state_7, o)
tree_x.move = move_6

print(f"Step 7 {len(tree_o.possible_states)}")

tree_o = tree_o.develop(interpreter, 7, view_7)

state_8 = interpreter.get_next_state(
    state_7,
    Turn({o: move_7}),
)
view_8 = interpreter.get_sees_by_role(state_8, x)
tree_o.move = move_7

print(f"Step 8 {len(tree_x.possible_states)}")

tree_x = tree_x.develop(interpreter, 8, view_8)

state_9 = interpreter.get_next_state(
    state_8,
    Turn({x: move_8}),
)
view_9 = interpreter.get_sees_by_role(state_9, x)
tree_x.move = move_8

print(f"Step 9 {len(tree_x.possible_states)}")

tree_x = tree_x.develop(interpreter, 9, view_9)

print(f"Step 10 {len(tree_x.possible_states)}")
