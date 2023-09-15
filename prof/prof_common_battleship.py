import pathlib

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Role
from pyggp.interpreters import ClingoRegroundingInterpreter

battleship_str: str = pathlib.Path("../src/games/battleship.gdl").read_text()

battleship_ruleset: gdl.Ruleset = gdl.parse(battleship_str)

battleship_interpreter = ClingoRegroundingInterpreter.from_ruleset(battleship_ruleset)

battleship_init_state = battleship_interpreter.get_init_state()

battleship_roles = battleship_interpreter.get_roles()

battleship_first = Role(gdl.Subrelation(gdl.Relation("first")))
battleship_second = Role(gdl.Subrelation(gdl.Relation("second")))
