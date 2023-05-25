import sys

from pyggp._caching import flatlen, weighted_len
from pyggp.agents.tree_agents.evaluators import final_goal_normalized_utility_evaluator
from pyggp.books import BookBuilder
from tqdm import trange

from prof.prof_caches import clear_caches, print_cache_info
from prof.prof_common_tic_tac_toe import tic_tac_toe_init_state, tic_tac_toe_interpreter, tic_tac_toe_x

print()
print_cache_info(tic_tac_toe_interpreter)
clear_caches(tic_tac_toe_interpreter)
print()

builder = BookBuilder(
    interpreter=tic_tac_toe_interpreter,
    role=tic_tac_toe_x,
    evaluator=final_goal_normalized_utility_evaluator,
    min_value=0.0,
    max_value=1.0,
)

for _ in trange(150_000):
    builder.step()
    if builder.done:
        break

print("Size:", len(builder.book))
print("Queue:", len(builder._queue))
print(
    "Estimated size: ",
    flatlen(builder.book.keys(), factor=128) + weighted_len(builder.book, factor=sys.getsizeof(1.0)),
)
book = builder()
print("Done: ", builder.done)
if builder.done:
    print("x:", book[tic_tac_toe_init_state])


print()
print_cache_info(tic_tac_toe_interpreter)
