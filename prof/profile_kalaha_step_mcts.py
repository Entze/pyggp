import tqdm
from pyggp.agents import MCTSAgent
from pyggp.engine_primitives import View
from pyggp.gameclocks import GameClock

from prof.prof_common_kalaha import kalaha_init_state, kalaha_interpreter, kalaha_north

agent = MCTSAgent(interpreter=kalaha_interpreter)

with agent:
    agent.prepare_match(
        ruleset=kalaha_interpreter.ruleset,
        role=kalaha_north,
        startclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
        playclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
    )

    agent.calculate_move(0, 2_500_000, View(kalaha_init_state))

    for _ in tqdm.trange(100):
        agent.step()
