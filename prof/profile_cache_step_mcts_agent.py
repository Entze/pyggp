import tqdm
from pyggp.agents import MCTSAgent
from pyggp.gameclocks import DEFAULT_START_CLOCK_CONFIGURATION, GameClock
from pyggp.interpreters import ClingoInterpreter

from prof.prof_caches import LRUCacheWithInfo, clear_caches, print_cache_info
from prof.prof_common_tic_tac_toe import tic_tac_toe_init_view, tic_tac_toe_ruleset, tic_tac_toe_x

interpreter = ClingoInterpreter(
    _rules=ClingoInterpreter.ClingoASTRules.from_ruleset(tic_tac_toe_ruleset),
    _get_next_state_cache=LRUCacheWithInfo(maxsize=100_000),
    _get_sees_cache=LRUCacheWithInfo(maxsize=100_000),
    _get_legal_moves_cache=LRUCacheWithInfo(maxsize=100_000),
    _get_goals_cache=LRUCacheWithInfo(maxsize=100_000),
    _is_terminal_cache=LRUCacheWithInfo(maxsize=100_000),
)

agent = MCTSAgent(interpreter=interpreter)

with agent:
    agent.prepare_match(
        role=tic_tac_toe_x,
        ruleset=tic_tac_toe_ruleset,
        startclock_config=DEFAULT_START_CLOCK_CONFIGURATION,
        playclock_config=GameClock.Configuration(total_time=5, delay=5),
    )

    agent.calculate_move(0, 0, tic_tac_toe_init_view)

    print()
    print_cache_info(agent.interpreter)
    clear_caches(agent.interpreter)
    print()

    for _ in tqdm.trange(1_000_000):
        agent.step()

print()
print_cache_info(agent.interpreter)
print()
