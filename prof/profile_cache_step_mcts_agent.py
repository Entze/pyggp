import tqdm
from pyggp.agents import MCTSAgent
from pyggp.game_description_language.subrelations import Subrelation
from pyggp.gameclocks import DEFAULT_START_CLOCK_CONFIGURATION, GameClock
from pyggp.interpreters import ClingoInterpreter, Interpreter

from prof.prof_caches import LRUCacheWithInfo, cache_info
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
    print("Subrelation._as_clingo_symbol_cache: ", cache_info(Subrelation._as_clingo_symbol_cache))
    print("Subrelation.from_clingo_sybmol: ", cache_info(Subrelation.as_clingo_symbol))
    print("interpreter._get_next_state_cache: ", cache_info(agent.interpreter._get_next_state_cache))
    print("interpreter._get_sees_cache: ", cache_info(agent.interpreter._get_sees_cache))
    print("interpreter._get_legal_moves_cache: ", cache_info(agent.interpreter._get_legal_moves_cache))
    print("interpreter._get_goals_cache: ", cache_info(agent.interpreter._get_goals_cache))
    print("interpreter._is_terminal_cache: ", cache_info(agent.interpreter._is_terminal_cache))
    print("Interpreter.get_roles_in_control:", cache_info(Interpreter.get_roles_in_control))
    Subrelation._as_clingo_symbol_cache.clear()
    Subrelation.from_clingo_symbol.cache_clear()
    agent.interpreter._get_next_state_cache.clear()
    agent.interpreter._get_sees_cache.clear()
    agent.interpreter._get_legal_moves_cache.clear()
    agent.interpreter._get_goals_cache.clear()
    agent.interpreter._is_terminal_cache.clear()
    Interpreter.get_roles_in_control.cache_clear()
    print()

    for _ in tqdm.trange(1_000_000):
        agent.step()

print()
print("Subrelation._as_clingo_symbol_cache: ", cache_info(Subrelation._as_clingo_symbol_cache))
print("Subrelation.from_clingo_sybmol: ", cache_info(Subrelation.as_clingo_symbol))
print("interpreter._get_next_state_cache: ", cache_info(agent.interpreter._get_next_state_cache))
print("interpreter._get_sees_cache: ", cache_info(agent.interpreter._get_sees_cache))
print("interpreter._get_legal_moves_cache: ", cache_info(agent.interpreter._get_legal_moves_cache))
print("interpreter._get_goals_cache: ", cache_info(agent.interpreter._get_goals_cache))
print("interpreter._is_terminal_cache: ", cache_info(agent.interpreter._is_terminal_cache))
print("Interpreter.get_roles_in_control:", cache_info(Interpreter.get_roles_in_control))
print()
