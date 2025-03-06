from collections import namedtuple
from typing import Any

import cachetools

from pyggp.game_description_language import Subrelation
from pyggp.interpreters import CachingInterpreter, Interpreter


class LRUCacheWithInfo(cachetools.LRUCache):
    def __init__(self, maxsize, getsizeof=None) -> None:
        cachetools.LRUCache.__init__(self, maxsize, getsizeof)
        self.accesses = 0

    @property
    def hits(self):
        return self.accesses - self.misses

    @property
    def misses(self):
        return self.currsize

    def __getitem__(self, key, cache_getitem=cachetools.Cache.__getitem__):
        _cache_getitem = self.inject("accesses", cache_getitem)
        return super().__getitem__(key, cache_getitem=_cache_getitem)

    def inject(self, attr, cache_getitem=cachetools.Cache.__getitem__):
        def get(obj, key):
            val = getattr(self, attr)
            setattr(self, attr, val + 1)
            return cache_getitem(obj, key)

        return get

    def cache_info(self):
        return namedtuple(
            "CacheInfo",
            ("hits", "misses", "maxsize", "currsize"),
        )(self.hits, self.misses, self.maxsize, self.currsize)


CacheInfo = namedtuple(
    "CacheInfo",
    ("hits", "misses", "maxsize", "currsize"),
    defaults=("Unknown", "Unknown", "Unknown", "Unknown"),
)


def cache_info(cache: Any) -> CacheInfo:
    if hasattr(cache, "cache_info"):
        return cache.cache_info()
    if isinstance(cache, cachetools.Cache):
        return CacheInfo(maxsize=cache.maxsize, currsize=cache.currsize)
    if isinstance(cache, dict):
        currsize = sum(len(v) for v in cache.values())
        return CacheInfo(maxsize="inf", currsize=currsize)
    return CacheInfo()


def print_cache_info(interpreter: CachingInterpreter):
    print("subrelation_as_clingo_symbol_cache: ", cache_info(Subrelation._as_clingo_symbol_cache))
    print("Subrelation.from_clingo_symbol: ", cache_info(Subrelation.from_clingo_symbol))
    print("interpreter.get_next_state: ", cache_info(interpreter.cache.next))
    print("interpreter.get_all_next_states: ", cache_info(interpreter.cache.all_next))
    print("interpreter.get_sees: ", cache_info(interpreter.cache.sees))
    print("interpreter.get_legal_moves: ", cache_info(interpreter.cache.legal))
    print("interpreter.get_goals: ", cache_info(interpreter.cache.goal))
    print("interpreter.is_terminal: ", cache_info(interpreter.cache.terminal))
    print("Interpreter.get_roles_in_control:", cache_info(Interpreter.get_roles_in_control))


def clear_caches(interpreter: CachingInterpreter):
    Subrelation._as_clingo_symbol_cache.clear()
    Subrelation.from_clingo_symbol.cache_clear()
    interpreter.cache.clear()
    Interpreter.get_roles_in_control.cache_clear()
