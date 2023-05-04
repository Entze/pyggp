from typing import FrozenSet, Generic, Iterable, Iterator, Mapping, Tuple, TypeVar, Union

_K = TypeVar("_K")
_V = TypeVar("_V")


class FrozenDict(Generic[_K, _V], Mapping[_K, _V]):
    def __init__(self, seq: Union[Mapping[_K, _V], Iterable[Tuple[_K, _V]], None] = None) -> None:
        self._pairs: FrozenSet[Tuple[_K, _V]]
        if seq is None:
            self._pairs = frozenset()
        elif isinstance(seq, Mapping):
            self._pairs = frozenset(seq.items())
        else:
            self._pairs = frozenset(seq)

    def __getitem__(self, __k: _K) -> _V:
        for k, v in self._pairs:
            if k == __k:
                return v
        raise KeyError(__k)

    def __len__(self) -> int:
        return len(self._pairs)

    def __iter__(self) -> Iterator[_K]:
        return (k for k, _ in self._pairs)

    def __hash__(self) -> int:
        return hash(self._pairs)
