from typing import Mapping, Sequence, Tuple

import lark

grammar = r"""

    spec_argument: name -> name_only
        | name "(" args ")" -> args_only
        | name "(" kwargs ")" -> kwargs_only
        | name "(" args "," kwargs ")" -> args_and_kwargs

    ?name: CNAME
    args: _seperated{arg, ","}
    arg: /[A-Za-z0-9]+/
    kwargs: _seperated{kwarg, ","}
    kwarg: head "=" tail
    ?head: CNAME
    ?tail: /[A-Za-z0-9]+/

    _seperated{x, sep}: x (sep x)*

    %import common (CNAME, STRING, NUMBER, WS)
    %ignore WS

"""

parser = lark.Lark(grammar=grammar, start="spec_argument")

Spec = Tuple[str, Tuple[str, ...], Mapping[str, str]]


class TreeToSpecTransformer(lark.Transformer[lark.Token, Spec]):
    def name_only(self, name: lark.Token) -> Spec:
        return name.value, (), {}

    def args_only(self, children: Sequence[lark.Token]) -> Spec:
        name, args = children
        return name.value, args, {}

    def kwargs_only(self, children: Sequence[lark.Token]) -> Spec:
        name, kwargs = children
        return name.value, (), kwargs

    def args_and_kwargs(self, children: Sequence[lark.Token]) -> Spec:
        name, args, kwargs = children
        return name.value, args, kwargs

    def args(self, children: Sequence[lark.Token]) -> Tuple[str, ...]:
        return tuple(children)

    def arg(self, children: Sequence[lark.Token]) -> str:
        (arg,) = children
        return arg.value

    def kwargs(self, children: Sequence[lark.Token]) -> Mapping[str, str]:
        return {k: v for k, v in children}

    def kwarg(self, children: Sequence[lark.Token]) -> Tuple[str, str]:
        head, tail = children
        return head.value, tail.value


transformer = TreeToSpecTransformer()
