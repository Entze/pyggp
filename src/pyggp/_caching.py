import contextlib
import functools
import re
import sys
from typing import (
    Any,
    Callable,
    Final,
    Hashable,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Protocol,
    Sized,
    Tuple,
    TypeVar,
    Union,
)

SUBRELATION_SIZE: Final[int] = 128
CLINGO_SYMBOL_SIZE: Final[int] = 128
CLINGO_AST_SIZE: Final[int] = 128
# Disables FBT003. Because: Explicitly need True (or False) as function argument.
BOOL_SIZE: Final[int] = sys.getsizeof(True)  # noqa: FBT003
INT_SIZE: Final[int] = sys.getsizeof(0)

size_re = re.compile(r"^(?P<num>\d+(\.\d+)?)\s*((?P<prefix>[kMG]i?)?(?P<unit>[Bb]?))$")

prefix_to_factor: Final[Mapping[str, float]] = {
    "k": 10**3,
    "M": 10**6,
    "G": 10**9,
    "ki": 2**10,
    "Mi": 2**20,
    "Gi": 2**30,
}

unit_to_factor: Final[Mapping[str, float]] = {
    "B": 1.0,
    "b": 1 / 8,
}


def size_str_to_int(size_str: str) -> int:
    with contextlib.suppress(ValueError):
        return int(float(size_str))
    match = size_re.match(size_str)
    if match is None:
        message = f"Invalid size string: {size_str}"
        raise ValueError(message)
    num = float(match.group("num"))
    prefix = match.group("prefix")
    unit = match.group("unit")
    return int(float(num) * prefix_to_factor.get(prefix, 1) * unit_to_factor.get(unit, 1))


def hashedkey(*args: Hashable, **kwargs: Hashable) -> Tuple[Union[int, Tuple[str,]]]:
    hashed_args: Iterator[int] = map(hash, args)
    hashed_kwargs: Iterator[Tuple[str, int]] = zip(kwargs.keys(), map(hash, kwargs.values()))
    # Disables return-value. Because: Typechecker does not infer correct type.
    return (  # type: ignore[return-value]
        *hashed_args,
        *hashed_kwargs,
    )


def hashedmethodkey(self: Any, *args: Hashable, **kwargs: Hashable) -> Tuple[Union[int, Tuple[str,]]]:  # noqa: ARG001
    # Disables ARG001. Because: deliberately ignoring self.
    hashed_args: Iterator[int] = map(hash, args)
    hashed_kwargs: Iterator[Tuple[str, int]] = zip(kwargs.keys(), map(hash, kwargs.values()))
    # Disables return-value. Because: Typechecker does not infer correct type.
    return (  # type: ignore[return-value]
        *hashed_args,
        *hashed_kwargs,
    )


def flatlen(container: Iterable[Sized], *, factor: int = 1, offset: int = 0) -> int:
    return sum(len(elem) * factor + offset for elem in container)


def flatmaplen(
    mapping: Mapping[Any, Sized],
    *,
    key_factor: int = 1,
    key_offset: int = 0,
    value_factor: int = 1,
    value_offset: int = 0,
) -> int:
    return sum(len(value) * value_factor + value_offset for value in mapping.values()) + sum(
        key_factor + key_offset for _ in mapping
    )


def weighted_len(sized: Sized, *, factor: int = 1, offset: int = 0) -> int:
    return len(sized) * factor + offset


def weighted_map_len(
    mapping: Mapping[Any, Sized],
    *,
    key_factor: int = 1,
    key_offset: int = 0,
    value_factor: int = 1,
    value_offset: int = 0,
) -> int:
    return len(mapping) * (key_factor + key_offset + value_factor + value_offset)


_V = TypeVar("_V")


def const(__value: _V, _ignored: Any, /) -> _V:
    return __value


_V_co = TypeVar("_V_co", covariant=True)


class _ConstProtocol(Protocol[_V_co]):
    def __call__(self, *args: Any, **kwargs: Any) -> _V_co:
        ...


next_sizeof: Callable[[Sized], int] = functools.partial(weighted_len, factor=SUBRELATION_SIZE)
sees_sizeof: Callable[[Sized], int] = functools.partial(weighted_len, factor=SUBRELATION_SIZE)
legal_sizeof: Callable[[Mapping[Any, Sized]], int] = functools.partial(
    flatmaplen,
    key_factor=SUBRELATION_SIZE,
    value_factor=SUBRELATION_SIZE,
)
goal_sizeof: Callable[[Mapping[Any, Optional[int]]], int] = functools.partial(
    weighted_map_len,
    key_factor=SUBRELATION_SIZE,
    value_factor=INT_SIZE,
)
terminal_sizeof: _ConstProtocol[int] = functools.partial(const, BOOL_SIZE)
get_roles_in_control_sizeof: Callable[[Sized], int] = functools.partial(weighted_len, factor=SUBRELATION_SIZE)
from_clingo_symbol_sizeof: _ConstProtocol[int] = functools.partial(const, SUBRELATION_SIZE)

as_clingo_symbol_sizeof: _ConstProtocol[int] = functools.partial(const, CLINGO_SYMBOL_SIZE)
