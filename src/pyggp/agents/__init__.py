"""Providing a set of agents that are ready to be used to play games or extended."""
from pyggp.agents.base_agents import Agent, ArbitraryAgent, HumanAgent, InterpreterAgent, RandomAgent
from pyggp.agents.tree_agents.mcts.agents import MCTSAgent, SingleObserverInformationSetMCTSAgent

MonteCarloTreeSearchAgent = MCTSAgent
SOISMCTSAgent = SingleObserverInformationSetMCTSAgent

__all__ = [
    "Agent",
    "ArbitraryAgent",
    "HumanAgent",
    "InterpreterAgent",
    "RandomAgent",
    "MCTSAgent",
    "SingleObserverInformationSetMCTSAgent",
    "MonteCarloTreeSearchAgent",
    "SOISMCTSAgent",
]
