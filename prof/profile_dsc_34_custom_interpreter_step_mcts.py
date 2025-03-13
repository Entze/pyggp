import tqdm

from prof.prof_common_dark_split_corridor34 import corridor_init_state, corridor_left
from pyggp.agents import MOISMCTSAgent
from pyggp.engine_primitives import View
from pyggp.gameclocks import GameClock
from pyggp.interpreters.dark_split_corridor_34_interpreter import DarkSplitCorridor34Interpreter

corridor_interpreter = DarkSplitCorridor34Interpreter()

agent = MOISMCTSAgent(interpreter=corridor_interpreter)

with agent:
    agent.prepare_match(
        ruleset=corridor_interpreter.ruleset,
        role=corridor_left,
        startclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
        playclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
    )

    agent.update(0, View(corridor_init_state), 100_000_000)

    for _ in tqdm.trange(500):
        agent.step()

    tree = agent.trees[agent.role]
    print(tree.valuation)
    print("\n".join(f"{turn} -> {child.valuation}" for turn, child in tree.children.items()))
