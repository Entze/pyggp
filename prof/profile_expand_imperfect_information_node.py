from pyggp.agents.tree_agents.nodes import VisibleInformationSetNode
from pyggp.game_description_language.subrelations import Subrelation, subrelation_as_clingo_symbol
from tqdm import tqdm

from prof.prof_common_tic_tac_toe import (
    tic_tac_toe_init_state,
    tic_tac_toe_init_view,
    tic_tac_toe_interpreter,
    tic_tac_toe_x,
)

tree = VisibleInformationSetNode(
    role=tic_tac_toe_x,
    possible_states={tic_tac_toe_init_state},
    view=tic_tac_toe_init_view,
)

stack = [tree]

print()
print("subrelation_as_clingo_symbol: ", subrelation_as_clingo_symbol.cache_info())
print("Subrelation.from_clingo_sybmol: ", Subrelation.from_clingo_symbol.cache_info())
subrelation_as_clingo_symbol.cache_clear()
Subrelation.from_clingo_symbol.cache_clear()
print()

MAX_DEPTH = 6
nodes = 1
total = 0

levels = []

for depth in range(MAX_DEPTH + 1):
    levels.append(nodes)
    total += nodes
    if depth % 2 == 0:
        nodes = (9 - depth) * nodes

print("Nodes per level: ", levels)
print("Total nodes: ", total)
print()

with tqdm(total=1) as pbar:
    while stack:
        node = stack.pop()
        node.expand(tic_tac_toe_interpreter)
        if node.depth < MAX_DEPTH:
            pbar.total += node.arity
            stack.extend(node.unique_children)
        pbar.update(1)

print()
print("subrelation_as_clingo_symbol: ", subrelation_as_clingo_symbol.cache_info())
print("Subrelation.from_clingo_sybmol: ", Subrelation.from_clingo_symbol.cache_info())
