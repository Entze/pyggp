from typing import Any, Mapping, Protocol, TypeVar

from pyggp.agents.tree_agents.mcts.valuations import PlayoutValuation
from pyggp.agents.tree_agents.nodes import Node

_U = TypeVar("_U")
_K = TypeVar("_K")


class MonteCarloTreeSearchNode(Node[_U, _K], Protocol[_U, _K]):
    valuation: PlayoutValuation[_U]
    children: Mapping[_K, "MonteCarloTreeSearchNode[_U, Any]"]
