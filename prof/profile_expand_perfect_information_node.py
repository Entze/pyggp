from pyggp.agents.tree_agents.nodes import PerfectInformationNode
from pyggp.game_description_language.subrelations import Subrelation
from pyggp.interpreters import Interpreter
from tqdm import tqdm

from prof.prof_caches import cache_info
from prof.prof_common_tic_tac_toe import tic_tac_toe_init_state, tic_tac_toe_interpreter

tree = PerfectInformationNode(
    state=tic_tac_toe_init_state,
)

print()
print("Subrelation._as_clingo_symbol_cache: ", cache_info(Subrelation._as_clingo_symbol_cache))
print("Subrelation.from_clingo_sybmol: ", cache_info(Subrelation.as_clingo_symbol))
print("interpreter._get_next_state_cache: ", cache_info(tic_tac_toe_interpreter._get_next_state_cache))
print("interpreter._get_sees_cache: ", cache_info(tic_tac_toe_interpreter._get_sees_cache))
print("interpreter._get_legal_moves_cache: ", cache_info(tic_tac_toe_interpreter._get_legal_moves_cache))
print("interpreter._get_goals_cache: ", cache_info(tic_tac_toe_interpreter._get_goals_cache))
print("interpreter._is_terminal_cache: ", cache_info(tic_tac_toe_interpreter._is_terminal_cache))
print("Interpreter.get_roles_in_control:", cache_info(Interpreter.get_roles_in_control))
Subrelation._as_clingo_symbol_cache.clear()
Subrelation.from_clingo_symbol.cache_clear()
tic_tac_toe_interpreter._get_next_state_cache.clear()
tic_tac_toe_interpreter._get_sees_cache.clear()
tic_tac_toe_interpreter._get_legal_moves_cache.clear()
tic_tac_toe_interpreter._get_goals_cache.clear()
tic_tac_toe_interpreter._is_terminal_cache.clear()
Interpreter.get_roles_in_control.cache_clear()
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
print("Subrelation._as_clingo_symbol_cache: ", cache_info(Subrelation._as_clingo_symbol_cache))
print("Subrelation.from_clingo_sybmol: ", cache_info(Subrelation.as_clingo_symbol))
print("interpreter._get_next_state_cache: ", cache_info(tic_tac_toe_interpreter._get_next_state_cache))
print("interpreter._get_sees_cache: ", cache_info(tic_tac_toe_interpreter._get_sees_cache))
print("interpreter._get_legal_moves_cache: ", cache_info(tic_tac_toe_interpreter._get_legal_moves_cache))
print("interpreter._get_goals_cache: ", cache_info(tic_tac_toe_interpreter._get_goals_cache))
print("interpreter._is_terminal_cache: ", cache_info(tic_tac_toe_interpreter._is_terminal_cache))
print("Interpreter.get_roles_in_control:", cache_info(Interpreter.get_roles_in_control))
