import pathlib

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Role
from pyggp.interpreters import ClingoRegroundingInterpreter

corridor_str: str = pathlib.Path("../src/games/phantom_split_corridor(3,5).gdl").read_text()

corridor_ruleset: gdl.Ruleset = gdl.parse(corridor_str)

corridor_interpreter = ClingoRegroundingInterpreter.from_ruleset(corridor_ruleset)

corridor_init_state = corridor_interpreter.get_init_state()

corridor_roles = corridor_interpreter.get_roles()

corridor_left = Role(gdl.Subrelation(gdl.Relation("left")))
corridor_right = Role(gdl.Subrelation(gdl.Relation("right")))
