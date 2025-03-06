from tqdm import trange

from prof.prof_caches import clear_caches, print_cache_info
from prof.prof_common_phantom_connect_4_4_4 import (
    phantom_connect_4_4_4_init_state,
    phantom_connect_4_4_4_interpreter,
    phantom_connect_4_4_4_role_x,
    phantom_connect_4_4_4_ruleset,
)
from pyggp.agents import SOISMCTSAgent
from pyggp.gameclocks import GameClock

agent = SOISMCTSAgent(interpreter=phantom_connect_4_4_4_interpreter)

with agent:
    agent.prepare_match(
        role=phantom_connect_4_4_4_role_x,
        ruleset=phantom_connect_4_4_4_ruleset,
        startclock_config=GameClock.Configuration(total_time=0.0, delay=1.0),
        playclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
    )

    init_view = agent.interpreter.get_sees_by_role(phantom_connect_4_4_4_init_state, agent.role)

    print("Calculating move...")
    agent.calculate_move(ply=0, total_time_ns=0, view=init_view)

    print()
    print_cache_info(agent.interpreter)
    clear_caches(agent.interpreter)

    for _ in trange(10_000):
        agent.step()

    print()
    print_cache_info(agent.interpreter)
print()
