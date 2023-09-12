import pyggp.game_description_language as gdl
from pyggp._logging import rich
from pyggp.agents import MOISMCTSAgent
from pyggp.agents.tree_agents.agents import ONE_S_IN_NS
from pyggp.engine_primitives import Move
from pyggp.gameclocks import DEFAULT_NO_TIMEOUT_CONFIGURATION, DEFAULT_START_CLOCK_CONFIGURATION, GameClock
from pyggp.records import ImperfectInformationRecord, Record
from rich import print

from prof.prof_common_dark_split_corridor34 import (
    corridor_init_state,
    corridor_interpreter,
    corridor_left,
    corridor_right,
)

a3 = gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(3)))))
a4 = gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(4)))))
b2 = gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(2)))))
b3 = gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(3)))))
b4 = gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(4)))))
c2 = gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(2)))))
c3 = gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(3)))))
c4 = gdl.Subrelation(gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(4)))))
b2_b3 = gdl.Subrelation(gdl.Relation(None, (b2, b3)))
a3_a4 = gdl.Subrelation(gdl.Relation(None, (a3, a4)))
b3_b4 = gdl.Subrelation(gdl.Relation(None, (b3, b4)))
c2_c3 = gdl.Subrelation(gdl.Relation(None, (c2, c3)))
c3_c4 = gdl.Subrelation(gdl.Relation(None, (c3, c4)))
east = gdl.Subrelation(gdl.Relation("east"))
south = gdl.Subrelation(gdl.Relation("south"))

block_b2_b3 = Move(
    gdl.Subrelation(
        gdl.Relation(
            "block",
            (b2_b3,),
        )
    )
)
block_a3_a4 = Move(
    gdl.Subrelation(
        gdl.Relation(
            "block",
            (a3_a4,),
        )
    )
)
block_b3_b4 = Move(
    gdl.Subrelation(
        gdl.Relation(
            "block",
            (b3_b4,),
        )
    )
)
block_c2_c3 = Move(
    gdl.Subrelation(
        gdl.Relation(
            "block",
            (c2_c3,),
        )
    )
)
block_c3_c4 = Move(
    gdl.Subrelation(
        gdl.Relation(
            "block",
            (c3_c4,),
        )
    )
)
move_east = Move(
    gdl.Subrelation(
        gdl.Relation(
            "move",
            (east,),
        )
    )
)

move_south = Move(
    gdl.Subrelation(
        gdl.Relation(
            "move",
            (south,),
        )
    )
)


state_0 = corridor_init_state
view_left_0 = corridor_interpreter.get_sees_by_role(state_0, corridor_left)
view_right_0 = corridor_interpreter.get_sees_by_role(state_0, corridor_right)
move_0 = move_south

print("=" * 80)
print(rich(state_0))
print("left")
print(rich(view_left_0))
print("right")
print(rich(view_right_0))

state_1 = corridor_interpreter.get_next_state(state_0, {corridor_left: move_0})
view_left_1 = corridor_interpreter.get_sees_by_role(state_1, corridor_left)
view_right_1 = corridor_interpreter.get_sees_by_role(state_1, corridor_right)
move_1 = block_b2_b3

print("=" * 80)
print(rich(state_1))
print("left")
print(rich(view_left_1))
print("right")
print(rich(view_right_1))

state_2 = corridor_interpreter.get_next_state(state_1, {corridor_right: move_1})
view_left_2 = corridor_interpreter.get_sees_by_role(state_2, corridor_left)
view_right_2 = corridor_interpreter.get_sees_by_role(state_2, corridor_right)
move_2 = move_south

print("=" * 80)
print(rich(state_2))
print("left")
print(rich(view_left_2))
print("right")
print(rich(view_right_2))

state_3 = corridor_interpreter.get_next_state(state_2, {corridor_left: move_2})
view_left_3 = corridor_interpreter.get_sees_by_role(state_3, corridor_left)
view_right_3 = corridor_interpreter.get_sees_by_role(state_3, corridor_right)
move_3 = block_c2_c3

print("=" * 80)
print(rich(state_3))
print("left")
print(rich(view_left_3))
print("right")
print(rich(view_right_3))

state_4 = corridor_interpreter.get_next_state(state_3, {corridor_right: move_3})
view_left_4 = corridor_interpreter.get_sees_by_role(state_4, corridor_left)
view_right_4 = corridor_interpreter.get_sees_by_role(state_4, corridor_right)
move_4 = move_east

print("=" * 80)
print(rich(state_4))
print("left")
print(rich(view_left_4))
print("right")
print(rich(view_right_4))

state_5 = corridor_interpreter.get_next_state(state_4, {corridor_left: move_4})
view_left_5 = corridor_interpreter.get_sees_by_role(state_5, corridor_left)
view_right_5 = corridor_interpreter.get_sees_by_role(state_5, corridor_right)

print("=" * 80)
print(rich(state_5))
print("left")
print(rich(view_left_5))
print("right")
print(rich(view_right_5))

print("#" * 80)

agent1 = MOISMCTSAgent(interpreter=corridor_interpreter, skip_book=True)
agent2 = MOISMCTSAgent(interpreter=corridor_interpreter, skip_book=True)
with agent1, agent2:
    agent1.prepare_match(
        role=corridor_left,
        ruleset=corridor_interpreter.ruleset,
        startclock_config=DEFAULT_START_CLOCK_CONFIGURATION,
        playclock_config=GameClock.Configuration(delay=0.0),
    )
    agent2.prepare_match(
        role=corridor_right,
        ruleset=corridor_interpreter.ruleset,
        startclock_config=DEFAULT_START_CLOCK_CONFIGURATION,
        playclock_config=GameClock.Configuration(delay=0.0),
    )

    print(0)
    agent1.calculate_move(0, 300 * ONE_S_IN_NS, view_left_0)
    agent1.trees[agent1.role].move = move_0

    print(1)
    agent2.calculate_move(1, 300 * ONE_S_IN_NS, view_right_1)
    agent2.trees[agent2.role].move = move_1

    print(2)
    agent1.calculate_move(2, 300 * ONE_S_IN_NS, view_left_2)
    agent1.trees[agent1.role].move = move_2

    print(3)
    agent2.calculate_move(3, 300 * ONE_S_IN_NS, view_right_3)
    agent2.trees[agent2.role].move = move_3

    print(4)
    agent1.calculate_move(4, 300 * ONE_S_IN_NS, view_left_4)
    agent1.trees[agent1.role].move = move_4

    print(5)
    agent2.calculate_move(5, 300 * ONE_S_IN_NS, view_right_5)
    agent2.search(300 * ONE_S_IN_NS)
