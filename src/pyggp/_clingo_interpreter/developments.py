import collections
import functools
from typing import Iterable, Iterator, MutableMapping, Optional, Sequence, Set, Tuple

import clingo
from clingo import ast as clingo_ast

from pyggp import _clingo as clingo_helper
from pyggp import game_description_language as gdl
from pyggp._clingo_interpreter.base import _get_ctl, _transform_model
from pyggp._clingo_interpreter.control_containers import ControlContainer
from pyggp._clingo_interpreter.temporal_rule_containers import TemporalRuleContainer
from pyggp.engine_primitives import Development, DevelopmentStep, Move, Role, State, Turn
from pyggp.exceptions.interpreter_exceptions import ModelTimeoutInterpreterError, UnsatDevelopmentsInterpreterError
from pyggp.records import Record


def _create_developments_ctl(
    temporal_rules: TemporalRuleContainer,
    record: Record,
) -> Tuple[clingo.Control, Sequence[clingo_ast.AST]]:
    rules = (
        *record.get_state_assertions(),
        *record.get_turn_assertions(),
        *record.get_view_assertions(),
        *temporal_rules.static,
        *temporal_rules.dynamic,
        *temporal_rules.statemachine,
        clingo_helper.create_pick_move_rule(record.horizon),
    )
    ctl = _get_ctl(
        sentences=(),
        rules=rules,
        models=0,
        logger=functools.partial(ControlContainer.log, context="development"),
    )
    return ctl, rules


def _get_developments_models(
    ctl: clingo.Control,
    offset: int,
    horizon: int,
    *,
    timeout: Optional[float] = None,
) -> Iterator[Sequence[clingo.Symbol]]:
    ctl.ground(
        (
            ("base", ()),
            ("static", ()),
            *(("dynamic", (clingo.Number(step),)) for step in range(offset, horizon + 1)),
            *(("statemachine", (clingo.Number(step),)) for step in range(offset, horizon)),
        ),
    )
    with ctl.solve(yield_=True, async_=True) as handle:
        handle.resume()
        done = handle.wait(timeout=timeout)
        if not done:
            handle.cancel()
            raise ModelTimeoutInterpreterError
        model = handle.model()
        if model is None:
            raise UnsatDevelopmentsInterpreterError
        while model is not None:
            symbols = model.symbols(shown=True)
            handle.resume()
            yield symbols
            done = handle.wait(timeout=timeout)
            if not done:
                handle.cancel()
                raise ModelTimeoutInterpreterError
            model = handle.model()


def transform_developments_model(symbols: Iterable[clingo.Symbol], offset: int, horizon: int) -> Development:
    subrelations = _transform_model(
        symbols,
        gdl.Relation.Signature(name="holds_at", arity=2),
        gdl.Relation.Signature(name="does_at", arity=3),
    )
    states: MutableMapping[int, Set[gdl.Subrelation]] = collections.defaultdict(set)
    role_to_moves: MutableMapping[int, MutableMapping[Role, Move]] = collections.defaultdict(dict)
    for subrelation in subrelations:
        if subrelation.matches_signature(name="holds_at", arity=2):
            holds: gdl.Subrelation = subrelation.symbol.arguments[0]
            step: int = subrelation.symbol.arguments[1].symbol.number
            states[step].add(holds)
        elif subrelation.matches_signature(name="does_at", arity=3):
            role: Role = Role(subrelation.symbol.arguments[0])
            move: Move = Move(subrelation.symbol.arguments[1])
            step: int = subrelation.symbol.arguments[2].symbol.number
            role_to_moves[step][role] = move

    development_steps = tuple(
        DevelopmentStep(
            state=State(frozenset(states[step])),
            turn=Turn(role_to_moves[step]) if step in role_to_moves else None,
        )
        for step in range(offset, horizon + 1)
    )
    return Development(development_steps)


def development_from_symbols(symbols: Sequence[clingo.Symbol], bounds: Optional[Tuple[int, int]] = None) -> Development:
    """Create a development from clingo symbols.

    Args:
        symbols: Clingo symbols
        bounds: (offset, horizon) bounds on the development

    Returns:
        Development

    """
    offset, horizon = bounds if bounds is not None else (None, None)
    ply_state_map: MutableMapping[int, Set[gdl.Subrelation]] = collections.defaultdict(set)
    ply_turn_map: MutableMapping[int, MutableMapping[Role, Move]] = collections.defaultdict(dict)
    for symbol in symbols:
        if symbol.match("holds_at", 2):
            subrelation = gdl.Subrelation.from_clingo_symbol(symbol.arguments[0])
            ply = symbol.arguments[1].number
            if bounds is None or offset <= ply <= horizon:
                ply_state_map[ply].add(subrelation)
        elif symbol.match("does_at", 3):
            role = Role(gdl.Subrelation.from_clingo_symbol(symbol.arguments[0]))
            move = Move(gdl.Subrelation.from_clingo_symbol(symbol.arguments[1]))
            ply = symbol.arguments[2].number
            if bounds is None or offset <= ply <= horizon:
                ply_turn_map[ply][role] = move
    if bounds is None:
        offset = 0
        horizon = len(ply_state_map)
    assert list(range(offset, horizon + 1)) == sorted(ply_state_map.keys())
    return Development(
        tuple(
            DevelopmentStep(
                state=State(frozenset(ply_state_map[ply])),
                turn=Turn(ply_turn_map[ply]) if ply_turn_map[ply] else None,
            )
            for ply in range(offset, horizon + 1)
        ),
    )
