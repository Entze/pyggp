import tqdm

from prof.prof_common_battleship import battleship_first, battleship_init_state, battleship_interpreter
from pyggp.agents import MOISMCTSAgent
from pyggp.engine_primitives import View
from pyggp.gameclocks import GameClock

agent = MOISMCTSAgent(interpreter=battleship_interpreter)

with agent:
    agent.prepare_match(
        ruleset=battleship_interpreter.ruleset,
        role=battleship_first,
        startclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
        playclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
    )

    agent.update(0, View(battleship_init_state), 100_000_000)

    for _ in tqdm.trange(5):
        agent.step()

    print(agent.get_main_tree(3).valuation)
