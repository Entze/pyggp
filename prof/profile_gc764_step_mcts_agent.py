from pyggp.agents import MCTSAgent
from pyggp.gameclocks import DEFAULT_START_CLOCK_CONFIGURATION, GameClock
from tqdm import trange

from prof.prof_caches import clear_caches, print_cache_info
from prof.prof_common_gravity_connect_7_6_4 import (
    gravity_connect_7_6_4_init_view,
    gravity_connect_7_6_4_interpreter,
    gravity_connect_7_6_4_ruleset,
    gravity_connect_7_6_4_yellow,
)

agent = MCTSAgent(interpreter=gravity_connect_7_6_4_interpreter)

with agent:
    agent.prepare_match(
        role=gravity_connect_7_6_4_yellow,
        ruleset=gravity_connect_7_6_4_ruleset,
        startclock_config=DEFAULT_START_CLOCK_CONFIGURATION,
        playclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
    )

    agent.calculate_move(ply=0, total_time_ns=0, view=gravity_connect_7_6_4_init_view)

    print()
    print_cache_info(agent.interpreter)
    clear_caches(agent.interpreter)

    for _ in trange(500):
        agent.step()

    print()
    print_cache_info(agent.interpreter)
print()
