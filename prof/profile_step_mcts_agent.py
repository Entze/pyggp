import tqdm
from pyggp.agents import MCTSAgent
from pyggp.game_description_language.subrelations import Subrelation, subrelation_as_clingo_symbol
from pyggp.gameclocks import DEFAULT_START_CLOCK_CONFIGURATION, GameClock

from prof.prof_common_tic_tac_toe import tic_tac_toe_init_view, tic_tac_toe_ruleset, tic_tac_toe_x

agent = MCTSAgent()

with agent:
    agent.prepare_match(
        role=tic_tac_toe_x,
        ruleset=tic_tac_toe_ruleset,
        startclock_config=DEFAULT_START_CLOCK_CONFIGURATION,
        playclock_config=GameClock.Configuration(total_time=5, delay=5),
    )

    agent.calculate_move(0, 0, tic_tac_toe_init_view)

    print()
    print("subrelation_as_clingo_symbol: ", subrelation_as_clingo_symbol.cache_info())
    print("Subrelation.from_clingo_sybmol: ", Subrelation.from_clingo_symbol.cache_info())
    subrelation_as_clingo_symbol.cache_clear()
    Subrelation.from_clingo_symbol.cache_clear()
    print()

    for _ in tqdm.trange(15_000):
        agent.step()

print()
print("subrelation_as_clingo_symbol: ", subrelation_as_clingo_symbol.cache_info())
print("Subrelation.from_clingo_sybmol: ", Subrelation.from_clingo_symbol.cache_info())
