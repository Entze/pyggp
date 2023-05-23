from pyggp.agents.tree_agents.nodes import PerfectInformationNode
from pyggp.game_description_language.subrelations import Subrelation, subrelation_as_clingo_symbol
from tqdm import tqdm

from prof.prof_common_tic_tac_toe import tic_tac_toe_init_state, tic_tac_toe_interpreter

tree = PerfectInformationNode(
    state=tic_tac_toe_init_state,
)

print()
print("subrelation_as_clingo_symbol: ", subrelation_as_clingo_symbol.cache_info())
print("Subrelation.from_clingo_sybmol: ", Subrelation.from_clingo_symbol.cache_info())
subrelation_as_clingo_symbol.cache_clear()
Subrelation.from_clingo_symbol.cache_clear()
print()

MAX_DEPTH = 5
nodes = 1
total = 0

levels = []

for depth in range(MAX_DEPTH + 1):
    levels.append(nodes)
    total += nodes
    nodes = (9 - depth) * nodes

print("Nodes per level: ", levels)
print("Total nodes: ", total)
print()

stack = [tree]

with tqdm(total=total) as pbar:
    while stack:
        node = stack.pop()
        node.expand(tic_tac_toe_interpreter)
        if node.depth < MAX_DEPTH:
            stack.extend(node.children.values())
        pbar.update(1)

print()
print("subrelation_as_clingo_symbol: ", subrelation_as_clingo_symbol.cache_info())
print("Subrelation.from_clingo_sybmol: ", Subrelation.from_clingo_symbol.cache_info())
