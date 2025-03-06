from tqdm import tqdm

from prof.prof_caches import clear_caches, print_cache_info
from prof.prof_common_tic_tac_toe import (
    tic_tac_toe_init_state,
    tic_tac_toe_init_view,
    tic_tac_toe_interpreter,
    tic_tac_toe_x,
)
from pyggp.agents.tree_agents.nodes import VisibleInformationSetNode

tree = VisibleInformationSetNode(
    role=tic_tac_toe_x,
    possible_states={tic_tac_toe_init_state},
    view=tic_tac_toe_init_view,
    fully_enumerated=True,
)

stack = [tree]

print()
print_cache_info(tic_tac_toe_interpreter)
clear_caches(tic_tac_toe_interpreter)
print()

MAX_DEPTH = 10
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
            stack.extend(node.children.values())
        pbar.update(1)

print()
print_cache_info(tic_tac_toe_interpreter)
