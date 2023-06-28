from dataclasses import dataclass, field
from typing import Mapping, Sequence, Tuple

import lark
from typing_extensions import Self


@dataclass(frozen=True)
class ArgumentSpecification:
    name: str
    args: Sequence[str] = field(default_factory=tuple)
    kwargs: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_str(cls, spec: str) -> Self:
        tree = parser.parse(spec)
        return transformer.transform(tree)


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
    elem: STRING | SIGNED_NUMBER

    _seperated{x, sep}: x (sep x)*

    %import common (CNAME, WORD, SIGNED_NUMBER, WS)
    %import python (STRING)
    %ignore WS

"""

parser = lark.Lark(grammar=grammar, start="spec_argument", maybe_placeholders=True, parser="earley")


class TreeToSpecTransformer(lark.Transformer[lark.Token, ArgumentSpecification]):
    def spec_argument(self, children: Sequence[lark.Token]) -> ArgumentSpecification:
        (name, arguments) = children
        args, kwargs = (), {}
        if arguments is not None:
            (args, kwargs) = arguments
        return ArgumentSpecification(name=name, args=args, kwargs=kwargs)

    def name(self, children: Sequence[lark.Token]) -> str:
        return ".".join(c.value for c in children)

    def args_only(self, children: Sequence[lark.Token]) -> Tuple[Tuple[str, ...], Mapping[str, str]]:
        (args,) = children
        return tuple(args), {}

    def kwargs_only(self, children: Sequence[lark.Token]) -> Tuple[Tuple[str, ...], Mapping[str, str]]:
        (kwargs,) = children
        return (), kwargs

    def args_and_kwargs(self, children: Sequence[lark.Token]) -> Tuple[Tuple[str, ...], Mapping[str, str]]:
        args, kwargs = children
        return args, kwargs

    def args(self, children: Sequence[lark.Token]) -> Tuple[str, ...]:
        return tuple(children)

    def arg(self, children: Sequence[lark.Token]) -> str:
        (arg,) = children
        return arg

    def kwargs(self, children: Sequence[lark.Token]) -> Mapping[str, str]:
        return {k: v for k, v in children}

    def kwarg(self, children: Sequence[lark.Token]) -> Tuple[str, str]:
        head, tail = children
        return head.value, tail

    def elem(self, children: Sequence[lark.Token]) -> str:
        (elem,) = children
        if elem.type == "STRING":
            return elem.value[1:-1]
        return elem.value


transformer = TreeToSpecTransformer()
