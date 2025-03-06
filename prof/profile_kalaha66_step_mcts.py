import tqdm

from prof.prof_common_kalaha66 import kalaha_init_state, kalaha_interpreter, kalaha_north
from pyggp.agents import MCTSAgent
from pyggp.engine_primitives import View
from pyggp.gameclocks import GameClock

agent = MCTSAgent(interpreter=kalaha_interpreter)

with agent:
    agent.prepare_match(
        ruleset=kalaha_interpreter.ruleset,
        role=kalaha_north,
        startclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
        playclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
    )

    agent.update(0, View(kalaha_init_state), 100_000_000)

    for _ in tqdm.trange(100):
        agent.step()

    print(agent.tree.valuation)
    print("\n".join(f"{turn} -> {child.valuation}" for turn, child in agent.tree.children.items()))
