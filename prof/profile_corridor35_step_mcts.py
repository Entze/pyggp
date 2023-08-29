import tqdm
from pyggp.agents import MCTSAgent
from pyggp.engine_primitives import View
from pyggp.gameclocks import GameClock

from prof.prof_common_split_corridor35 import corridor_init_state, corridor_interpreter, corridor_left

agent = MCTSAgent(interpreter=corridor_interpreter)

with agent:
    agent.prepare_match(
        ruleset=corridor_interpreter.ruleset,
        role=corridor_left,
        startclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
        playclock_config=GameClock.Configuration(total_time=2.5, delay=2.5),
    )

    agent.update(0, View(corridor_init_state), 100_000_000)

    for _ in tqdm.trange(5000):
        agent.step()

    print(agent.tree.valuation)
    print("\n".join(f"{turn} -> {child.valuation}" for turn, child in agent.tree.children.items()))
