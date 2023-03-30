from dataclasses import dataclass, field
from typing import Generic, Iterable, Iterator, TypeVar

T = TypeVar("T")


@dataclass
class Returner(Generic[T]):
    to_return: Iterable[T] = field(default_factory=list)

    _iterable: Iterator[T] = field(init=False)

    def __post_init__(self):
        self._iterable = iter(self.to_return)

    def __call__(self, *args, **kwargs) -> T:
        return next(self._iterable)
