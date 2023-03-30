import itertools
from typing import Any, Callable, Iterable, Optional, TypeAlias

from pyggp.agents import InterpreterAgent
from pyggp.agents.tree_agents.base_tree_agent import TreeAgent
from pyggp.agents.tree_agents.nodes import Node
from pyggp.agents.tree_agents.valuations import Valuation
from pyggp.gdl import State

NodeSelector: TypeAlias = Callable[[Iterable[Node]], Node]
GameSimulator: TypeAlias = Callable[[State], Optional[Iterable[State]]]
StateEvaluator: TypeAlias = Callable[[State], Valuation]


class MCTSAgent(TreeAgent, InterpreterAgent):
    def __init__(
        self,
        selector: NodeSelector,
        simulator: GameSimulator,
        evaluator: StateEvaluator,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.selector = selector
        self.simulator = simulator
        self.evaluator = evaluator

    def propagate_valuations(
        self,
        /,
        max_lookahead_depth: Optional[int] = None,
        max_lookahead_width: Optional[int] = None,
    ) -> None:
        pass  # expanding and searching already propagates values

    def _simulate(
        self,
        node: Node,
        /,
        max_lookahead_depth: Optional[int] = None,
        max_lookahead_width: Optional[int] = None,
    ) -> Valuation:
        depth = 0
        states = node.states
        while True:
            if max_lookahead_depth is not None and depth >= max_lookahead_depth:
                break
            if max_lookahead_width is not None:
                states = itertools.islice(states, max_lookahead_width)
            next_states = self.simulator(*states)
            if next_states is None:
                break
            states = next_states
            depth += 1
        return self.evaluator(*states)

    def search(
        self,
        /,
        max_expand_depth: Optional[int] = None,
        max_lookahead_depth: Optional[int] = None,
        max_expand_width: Optional[int] = None,
        max_lookahead_width: Optional[int] = None,
    ) -> None:
        node = self.root
        ply = 0
        while node.is_expanded and not node.is_terminal and (max_expand_depth is None or ply < max_expand_depth):
            node = node.selector(*node.children.values())
            ply += 1
        if not node.is_expanded:
            node.expand(self._interpreter, max_width=max_expand_width)
        assert node.is_expanded
        playout = self._simulate(node, max_lookahead_depth=max_lookahead_depth, max_lookahead_width=max_lookahead_width)
        node.valuation @= playout
        while not node.is_root:
            node = node.parent
            node.valuation @= playout
