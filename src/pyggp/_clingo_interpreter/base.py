from typing import Callable, Iterable, Iterator, Optional

import clingo
from clingo import ast as clingo_ast

from pyggp import _clingo as clingo_helper
from pyggp import game_description_language as gdl
from pyggp.exceptions.interpreter_exceptions import (
    ModelTimeoutInterpreterError,
    MoreThanOneModelInterpreterError,
    UnsatInterpreterError,
)


def _get_shows(ruleset: gdl.Ruleset) -> Iterator[clingo_ast.AST]:
    if ruleset.role_rules:
        yield clingo_helper.SHOW_ROLE
    if ruleset.init_rules:
        yield clingo_helper.SHOW_INIT
    if ruleset.next_rules:
        yield clingo_helper.SHOW_NEXT
    if ruleset.sees_rules:
        yield clingo_helper.SHOW_SEES
    if ruleset.legal_rules:
        yield clingo_helper.SHOW_LEGAL
    if ruleset.goal_rules:
        yield clingo_helper.SHOW_GOAL
    if ruleset.terminal_rules:
        yield clingo_helper.SHOW_TERMINAL


def _get_ctl(
    sentences: Optional[Iterable[gdl.Sentence]] = None,
    rules: Optional[Iterable[clingo_ast.AST]] = None,
    *,
    logger: Callable[[clingo.MessageCode, str], None],
    models: int = 0,
) -> clingo.Control:
    ctl = clingo.Control(logger=logger)
    ctl.configuration.solve.models = models
    with clingo_ast.ProgramBuilder(ctl) as builder:
        if sentences is not None:
            for sentence in sentences:
                builder.add(sentence.as_clingo_ast())
        if rules is not None:
            for rule in rules:
                builder.add(rule)
    return ctl


def _get_model(ctl: clingo.Control, timeout: Optional[float] = None) -> Iterator[clingo.Symbol]:
    with ctl.solve(async_=True, yield_=True) as handle:
        handle.resume()
        done = handle.wait(timeout=timeout)
        if not done:
            handle.cancel()
            raise ModelTimeoutInterpreterError
        model = handle.model()
        if model is None:
            raise UnsatInterpreterError
        symbols = model.symbols(shown=True)
        handle.resume()
        yield from symbols
        done = handle.wait(timeout=timeout)
        if not done:
            handle.cancel()
            raise ModelTimeoutInterpreterError
        model = handle.model()
        if model is not None:
            raise MoreThanOneModelInterpreterError


def _transform_model(
    symbols: Iterable[clingo.Symbol],
    *signatures: gdl.Relation.Signature,
    unpack: Optional[int] = None,
) -> Iterator[gdl.Subrelation]:
    return (
        _transform(symbol, unpack=unpack)
        for symbol in symbols
        if not signatures or any(symbol.match(signature.name, signature.arity) for signature in signatures)
    )


def _transform(symbol: clingo.Symbol, unpack: Optional[int] = None) -> gdl.Subrelation:
    subrelation = gdl.Subrelation.from_clingo_symbol(symbol)
    if unpack is None:
        return subrelation
    return subrelation.symbol.arguments[unpack]
