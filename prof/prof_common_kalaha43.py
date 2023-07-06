import pathlib

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Role
from pyggp.interpreters import ClingoRegroundingInterpreter

kalaha_str: str = pathlib.Path("../src/games/kalaha(4,3).gdl").read_text()

kalaha_ruleset: gdl.Ruleset = gdl.parse(kalaha_str)

kalaha_interpreter = ClingoRegroundingInterpreter.from_ruleset(kalaha_ruleset)

kalaha_init_state = kalaha_interpreter.get_init_state()

kalaha_roles = kalaha_interpreter.get_roles()

kalaha_north = Role(gdl.Subrelation(gdl.Relation("north")))
kalaha_south = Role(gdl.Subrelation(gdl.Relation("south")))
