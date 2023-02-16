from dataclasses import dataclass, field
from typing import Sequence, Self


@dataclass(frozen=True)
class Variable:
    name: str


@dataclass(frozen=True)
class Relation:
    name: str | None = None
    arguments: Sequence[Self | int | str | Variable] = field(default_factory=tuple)

    @property
    def arity(self) -> int:
        return len(self.arguments)

    def match(self, name: str | None = None, arity: int = 0) -> bool:
        return name == self.name and arity == self.arity
