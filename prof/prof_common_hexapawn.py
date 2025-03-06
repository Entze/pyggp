import pathlib

import pyggp.game_description_language as gdl
from pyggp.engine_primitives import Role
from pyggp.interpreters import ClingoInterpreter

hexapawn_str: str = pathlib.Path("../src/games/hexapawn.gdl").read_text()

hexapawn_ruleset: gdl.Ruleset = gdl.parse(hexapawn_str)

hexapawn_interpreter = ClingoInterpreter.from_ruleset(hexapawn_ruleset)

hexapawn_init_state = hexapawn_interpreter.get_init_state()

hexapawn_roles = hexapawn_interpreter.get_roles()

hexapawn_white = Role(gdl.Subrelation(gdl.Relation("white")))
hexapawn_black = Role(gdl.Subrelation(gdl.Relation("black")))
