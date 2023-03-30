from typing import TYPE_CHECKING, Any, Optional

from pyggp.agents import Agent

if TYPE_CHECKING:
    from pyggp.agents.tree_agents.nodes import Node


class TreeAgent(Agent):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.root: Optional[Node] = None

    def propagate_valuations(
        self,
        /,
        max_lookahead_depth: Optional[int] = None,
        max_lookahead_width: Optional[int] = None,
    ) -> None:
        raise NotImplementedError

    def search(
        self,
        /,
        max_expand_depth: Optional[int] = None,
        max_lookahead_depth: Optional[int] = None,
        max_expand_width: Optional[int] = None,
        max_lookahead_width: Optional[int] = None,
    ) -> None:
        raise NotImplementedError
