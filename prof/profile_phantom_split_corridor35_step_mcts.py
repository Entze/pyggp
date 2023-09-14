import tqdm
from pyggp._logging import rich
from pyggp.agents import MCTSAgent, MOISMCTSAgent
from pyggp.engine_primitives import View
from pyggp.gameclocks import GameClock
from rich import print

from prof.prof_common_phantom_split_corridor35 import corridor_init_state, corridor_interpreter, corridor_left

agent = MOISMCTSAgent(interpreter=corridor_interpreter)

with agent:
    agent.prepare_match(
        ruleset=corridor_interpreter.ruleset,
        role=corridor_left,
        startclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
        playclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
    )

    agent.update(0, View(corridor_init_state), 100_000_000)

    for _ in tqdm.trange(1000):
        agent.step()

    tree = agent.trees[agent.role]
    print(tree.valuation)
    print("\n".join(f"{rich(turn)} -> {rich(child.valuation)}" for turn, child in tree.children.items()))
