from collections import namedtuple
from typing import Any

import cachetools


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
    return CacheInfo()
