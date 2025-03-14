import pathlib

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Move, Role, Turn
from pyggp.interpreters import ClingoInterpreter

corridor_str: str = pathlib.Path("../src/games/dark_split_corridor(3,4).gdl").read_text()

corridor_ruleset: gdl.Ruleset = gdl.parse(corridor_str)

corridor_interpreter = ClingoInterpreter.from_ruleset(corridor_ruleset)

corridor_init_state = corridor_interpreter.get_init_state()

corridor_roles = corridor_interpreter.get_roles()

corridor_left = Role(gdl.Subrelation(gdl.Relation("left")))
corridor_right = Role(gdl.Subrelation(gdl.Relation("right")))

b2: gdl.Subrelation = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(2))))
)
b3: gdl.Subrelation = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(3))))
)
b2_b3 = gdl.Subrelation(gdl.Relation(None, (b2, b3)))
block_b2_b3 = gdl.Subrelation(gdl.Relation("block", (b2_b3,)))

corridor_second_state = corridor_interpreter.get_next_state(
    corridor_init_state, Turn({corridor_left: Move(block_b2_b3)})
)
