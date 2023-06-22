import collections
from dataclasses import dataclass, field
from typing import FrozenSet, Mapping, MutableMapping, Optional, Set, Tuple, TypeVar, Union

from pyggp.engine_primitives import Move, Role, State, Turn, View

_K = TypeVar("_K")
_V = TypeVar("_V")
_NextCache = MutableMapping[int, MutableMapping[Union[State, View], MutableMapping[Turn, State]]]
_AllNextCache = MutableMapping[int, MutableMapping[Union[State, View], Set[Tuple[Turn, State]]]]
_SeesCache = MutableMapping[int, MutableMapping[Union[State, View], Mapping[Role, View]]]
_LegalCache = MutableMapping[int, MutableMapping[Union[State, View], Mapping[Role, FrozenSet[Move]]]]
_GoalCache = MutableMapping[int, MutableMapping[Union[State, View], Mapping[Role, int]]]
_TerminalCache = MutableMapping[int, MutableMapping[Union[State, View], bool]]


def _state_to_dict_defaultdict_factory() -> collections.defaultdict[Union[State, View], MutableMapping[_K, _V]]:
    return collections.defaultdict(dict)


def _state_to_set_defaultdict_factory() -> collections.defaultdict[Union[State, View], Set[_V]]:
    return collections.defaultdict(set)


def _default_next_cache_factory() -> _NextCache:
    return collections.defaultdict(_state_to_dict_defaultdict_factory)


def _default_all_next_cache_factory() -> _AllNextCache:
    return collections.defaultdict(_state_to_set_defaultdict_factory)


def _default_sees_cache_factory() -> _SeesCache:
    return collections.defaultdict(_state_to_dict_defaultdict_factory)


def _default_legal_cache_factory() -> _LegalCache:
    return collections.defaultdict(_state_to_dict_defaultdict_factory)


def _default_goal_cache_factory() -> _GoalCache:
    return collections.defaultdict(_state_to_dict_defaultdict_factory)


def _default_terminal_cache_factory() -> _TerminalCache:
    return collections.defaultdict(dict)


@dataclass
class CacheContainer:
    roles: Optional[FrozenSet[Role]] = field(default=None)
    init: Optional[State] = field(default=None)
    next: _NextCache = field(default_factory=_default_next_cache_factory)
    all_next: _AllNextCache = field(default_factory=_default_all_next_cache_factory)
    sees: _SeesCache = field(default_factory=_default_sees_cache_factory)
    legal: _LegalCache = field(default_factory=_default_legal_cache_factory)
    goal: _GoalCache = field(default_factory=_default_goal_cache_factory)
    terminal: _TerminalCache = field(default_factory=_default_terminal_cache_factory)

    def clear(self) -> None:
        self.roles = None
        self.init = None
        self.next.clear()
        self.all_next.clear()
        self.sees.clear()
        self.legal.clear()
        self.goal.clear()
        self.terminal.clear()
