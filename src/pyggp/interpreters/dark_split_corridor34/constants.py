from typing import Final

from pyggp import game_description_language as gdl
from pyggp.engine_primitives import Role

left: Final[Role] = Role(gdl.Subrelation(gdl.Relation("left")))
right: Final[Role] = Role(gdl.Subrelation(gdl.Relation("right")))
north: Final[gdl.Subrelation] = gdl.Subrelation(gdl.Relation("north"))
east: Final[gdl.Subrelation] = gdl.Subrelation(gdl.Relation("east"))
south: Final[gdl.Subrelation] = gdl.Subrelation(gdl.Relation("south"))
west: Final[gdl.Subrelation] = gdl.Subrelation(gdl.Relation("west"))
control_left: Final[gdl.Subrelation] = gdl.Subrelation(gdl.Relation("control", (left,)))
control_right: Final[gdl.Subrelation] = gdl.Subrelation(gdl.Relation("control", (right,)))
a1: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(1))))
)
a2: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(2))))
)
a3: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(3))))
)
a4: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("a")), gdl.Subrelation(gdl.Number(4))))
)
b1: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(1))))
)
b2: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(2))))
)
b3: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(3))))
)
b4: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("b")), gdl.Subrelation(gdl.Number(4))))
)
c1: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(1))))
)
c2: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(2))))
)
c3: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(3))))
)
c4: Final[gdl.Subrelation] = gdl.Subrelation(
    gdl.Relation(None, (gdl.Subrelation(gdl.Relation("c")), gdl.Subrelation(gdl.Number(4))))
)
