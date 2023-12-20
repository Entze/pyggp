import sys

from pyggp._caching import flatlen, weighted_len
from pyggp.agents.tree_agents.evaluators import final_goal_normalized_utility_evaluator
from pyggp.books import BookBuilder
from tqdm import trange

from prof.prof_caches import clear_caches, print_cache_info
from prof.prof_common_hexapawn import hexapawn_init_state, hexapawn_interpreter, hexapawn_white

print()
print_cache_info(hexapawn_interpreter)
clear_caches(hexapawn_interpreter)
print()

builder = BookBuilder(
    interpreter=hexapawn_interpreter,
    role=hexapawn_white,
    evaluator=final_goal_normalized_utility_evaluator,
    min_value=0.0,
    max_value=1.0,
)

for _ in trange(1_000_000_000):
    builder.step()

print("Size:", len(builder.book))
print("Queue:", len(builder._queue))
print(
    "Estimated size: ",
    flatlen(builder.book.keys(), factor=128) + weighted_len(builder.book, factor=sys.getsizeof(1.0)),
)
print("Done: ", builder.done)
book = builder()
if builder.done:
    print("white:", book[hexapawn_init_state])


print()
print_cache_info(hexapawn_interpreter)
