import importlib
from dataclasses import dataclass, field
from typing import Mapping, Sequence, Tuple, Type, TypeVar, Union

import lark
from typing_extensions import Self

_T_co = TypeVar("_T_co", covariant=True)


@dataclass(frozen=True)
class ArgumentSpecification:
    name: str
    args: Sequence[str] = field(default_factory=tuple)
    kwargs: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_str(cls, spec: str) -> Self:
        tree = parser.parse(spec)
        return transformer.transform(tree)

    def __rich__(self) -> str:
        if not self.args and not self.kwargs:
            return self.name
        if not self.kwargs:
            return f"{self.name}({', '.join(self.args)})"
        if not self.args:
            return f"{self.name}({', '.join(f'{k}={v}' for k, v in self.kwargs.items())})"
        return f"{self.name}({', '.join(self.args), ', '.join(f'{k}={v}' for k, v in self.kwargs.items())})"

    def load(self) -> Type[_T_co]:
        modulename, classname = self.name.rsplit(".", 1)
        module = importlib.import_module(modulename)
        return getattr(module, classname)


grammar = r"""

    spec_argument: name ["(" arguments ")"]


    name: CNAME ("." CNAME)*
    ?arguments: args_and_kwargs | kwargs_only | args_only
    args_and_kwargs.3: args "," kwargs
    kwargs_only.2: kwargs
    args_only.1: args

    args: arg ("," arg)*
    arg: elem
    kwargs: kwarg ("," kwarg)*
    kwarg: CNAME "=" elem
    ?elem: string | num | boolean | none
    string: STRING
    num: SIGNED_NUMBER
    ?boolean: "True" -> boolean_true
        | "False" -> boolean_false
    none: "None"

    _seperated{x, sep}: x (sep x)*

    %import common (CNAME, WORD, SIGNED_NUMBER, WS)
    %import python (STRING)
    %ignore WS

"""

parser = lark.Lark(grammar=grammar, start="spec_argument", maybe_placeholders=True, parser="earley")

Primitive = Union[str, int, bool, None]
RawArgsAndKwargs = Tuple[Tuple[Primitive, ...], Mapping[str, Primitive]]


class TreeToSpecTransformer(lark.Transformer[lark.Token, ArgumentSpecification]):
    def spec_argument(self, children: Sequence[lark.Token]) -> ArgumentSpecification:
        (name, arguments) = children
        args, kwargs = (), {}
        if arguments is not None:
            (args, kwargs) = arguments
        return ArgumentSpecification(name=name, args=args, kwargs=kwargs)

    def name(self, children: Sequence[lark.Token]) -> str:
        return ".".join(c.value for c in children)

    def args_only(self, children: Sequence[lark.Token]) -> RawArgsAndKwargs:
        (args,) = children
        return tuple(args), {}

    def kwargs_only(self, children: Sequence[lark.Token]) -> RawArgsAndKwargs:
        (kwargs,) = children
        return (), kwargs

    def args_and_kwargs(self, children: Sequence[lark.Token]) -> RawArgsAndKwargs:
        args, kwargs = children
        return args, kwargs

    def args(self, children: Sequence[lark.Token]) -> Tuple[Primitive, ...]:
        return tuple(children)

    def arg(self, children: Sequence[lark.Token]) -> Primitive:
        (arg,) = children
        return arg

    def kwargs(self, children: Sequence[lark.Token]) -> Mapping[str, Primitive]:
        return {k: v for k, v in children}

    def kwarg(self, children: Sequence[lark.Token]) -> Tuple[str, Primitive]:
        head, tail = children
        return head.value, tail

    def string(self, children: Sequence[lark.Token]) -> str:
        (string,) = children
        return string.value[1:-1]

    def num(self, children: Sequence[lark.Token]) -> int:
        (num,) = children
        return int(num.value)

    def boolean_true(self, children: Sequence[lark.Token]) -> bool:
        return True

    def boolean_false(self, children: Sequence[lark.Token]) -> bool:
        return False

    def none(self, children: Sequence[lark.Token]) -> None:
        return None


transformer = TreeToSpecTransformer()
