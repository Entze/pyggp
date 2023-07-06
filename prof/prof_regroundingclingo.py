import collections
from typing import Iterator, Optional

import clingo.ast as clingo_ast
import pyggp._clingo as clingo_helper
import pyggp.game_description_language as gdl
import tqdm
from pyggp._clingo_interpreter.base import _get_ctl, _get_model, _transform_model
from pyggp.engine_primitives import Move, Role, State
from pyggp.interpreters import Interpreter

from prof.prof_common_kalaha import kalaha_ruleset


def solve(
    sentences,
    state: Optional[State] = None,
    role: Optional[Role] = None,
    move: Optional[Move] = None,
    name: str = "true",
    arity: int = 1,
    unpack: Optional[int] = None,
) -> Iterator[gdl.Subrelation]:
    ctl = _get_ctl(sentences=sentences)
    if state:
        with clingo_ast.ProgramBuilder(ctl) as builder:
            for subrelation in state:
                func = clingo_helper.create_function("true", (subrelation.as_clingo_ast(),))
                atom = clingo_helper.create_atom(func)
                lit = clingo_helper.create_literal(atom=atom)
                rule = clingo_helper.create_rule(head=lit)
                builder.add(rule)
    if role is not None and move is not None:
        with clingo_ast.ProgramBuilder(ctl) as builder:
            func = clingo_helper.create_function("does", (role.as_clingo_ast(), move.as_clingo_ast()))
            atom = clingo_helper.create_atom(func)
            lit = clingo_helper.create_literal(atom=atom)
            rule = clingo_helper.create_rule(head=lit)
            builder.add(rule)

    ctl.ground()
    model = _get_model(ctl)
    return _transform_model(model, gdl.Relation.Signature(name, arity), unpack=unpack)


init_state = State(frozenset(solve(kalaha_ruleset.init_rules, name="init", arity=1, unpack=0)))

states = collections.deque((init_state,))

searched = 0
max_search = 1_000

with tqdm.tqdm(total=max_search) as pbar:
    while states and searched < max_search:
        searched += 1
        pbar.update(1)
        current = states.pop()
        terminal = next(solve(kalaha_ruleset.terminal_rules, state=current, name="terminal", arity=0), None) is not None
        if terminal:
            continue
        roles_in_control = Interpreter.get_roles_in_control(current)
        in_control = next(iter(roles_in_control))
        legal_moves = frozenset(
            Move(move)
            for move in solve(kalaha_ruleset.legal_rules, state=current, role=in_control, name="legal", arity=2)
            if move.symbol.arguments[0] == in_control
        )
        for move in legal_moves:
            next_state = State(
                frozenset(
                    solve(
                        kalaha_ruleset.next_rules,
                        state=current,
                        role=in_control,
                        move=move,
                        name="next",
                        arity=1,
                        unpack=0,
                    ),
                ),
            )
            states.append(next_state)
