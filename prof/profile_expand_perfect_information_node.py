from pyggp.agents.tree_agents.nodes import PerfectInformationNode
from tqdm import tqdm

from prof.prof_caches import clear_caches, print_cache_info
from prof.prof_common_tic_tac_toe import tic_tac_toe_init_state, tic_tac_toe_interpreter

tree = PerfectInformationNode(
    state=tic_tac_toe_init_state,
)

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
print_cache_info(tic_tac_toe_interpreter)
