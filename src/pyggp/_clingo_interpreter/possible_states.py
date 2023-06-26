import functools
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, MutableMapping, Sequence, Tuple

import clingo
import clingo.ast as clingo_ast
from clingo import PropagateControl, PropagateInit

import pyggp._clingo as clingo_helper
import pyggp.game_description_language as gdl
from pyggp._clingo_interpreter.base import _get_ctl
from pyggp._clingo_interpreter.control_containers import ControlContainer
from pyggp._clingo_interpreter.developments import _get_developments_models
from pyggp._clingo_interpreter.shape_containers import ShapeContainer
from pyggp._clingo_interpreter.temporal_rule_containers import TemporalRuleContainer
from pyggp.engine_primitives import ParallelMode, State
from pyggp.records import Record


@dataclass
class StateEnumerationPropagator(clingo.Propagator):
    ply: int
    offset: int
    holds_program_to_solver: MutableMapping[int, int] = field(default_factory=dict)
    holds_solver_to_program: MutableMapping[int, int] = field(default_factory=dict)
    does_program_to_solver: MutableMapping[int, int] = field(default_factory=dict)
    does_solver_to_program: MutableMapping[int, int] = field(default_factory=dict)
    state_program_to_solver: MutableMapping[int, int] = field(default_factory=dict)
    state_solver_to_program: MutableMapping[int, int] = field(default_factory=dict)
    clause_queue: Deque[Sequence[int]] = field(default_factory=deque)

    def init(self, init: PropagateInit) -> None:
        for symbolic_atom in init.symbolic_atoms.by_signature("holds_at", 2):
            if symbolic_atom.symbol.arguments[1].number != self.ply:
                continue
            program_literal = symbolic_atom.literal
            solver_literal = init.solver_literal(program_literal)
            self.holds_program_to_solver[program_literal] = solver_literal
            self.holds_solver_to_program[solver_literal] = program_literal
        for symbolic_atom in init.symbolic_atoms.by_signature("does_at", 3):
            program_literal = symbolic_atom.literal
            solver_literal = init.solver_literal(program_literal)
            self.does_program_to_solver[program_literal] = solver_literal
            self.does_solver_to_program[solver_literal] = program_literal
        for symbolic_atom in init.symbolic_atoms.by_signature("__state", 2):
            if symbolic_atom.symbol.arguments[0].number != self.offset:
                continue
            program_literal = symbolic_atom.literal
            solver_literal = init.solver_literal(program_literal)
            self.state_program_to_solver[program_literal] = solver_literal
            self.state_solver_to_program[solver_literal] = program_literal

        init.check_mode = clingo.PropagatorCheckMode.Total

    def check(self, control: PropagateControl) -> None:
        (state_literal,) = (
            solver_literal
            for solver_literal in self.state_solver_to_program
            if control.assignment.is_true(solver_literal)
        )
        move_clause = (
            *(
                -solver_literal
                for solver_literal in self.holds_solver_to_program
                if control.assignment.is_true(solver_literal)
            ),
            -state_literal,
        )
        while self.clause_queue:
            clause = self.clause_queue.popleft()
            if not control.add_clause(clause) or not control.propagate():
                self.clause_queue.append(move_clause)
                return

        self.clause_queue.append(move_clause)

        state_clause = []
        for solver_literal in self.holds_solver_to_program:
            value = 1 - 2 * int(control.assignment.value(solver_literal))
            state_clause.append(value * solver_literal)

        self.clause_queue.append(state_clause)


def create_possible_states_ctl(
    temporal_rules: TemporalRuleContainer,
    shapes: ShapeContainer,
    record: Record,
    ply: int,
    *,
    is_final_view: bool = False,
    parallel_mode: ParallelMode = 4,
) -> Tuple[clingo.Control, Sequence[clingo_ast.AST]]:
    rules = (
        clingo_helper.HIDE,
        clingo_helper.get_holds_at_ply_show(ply),
        *record.get_state_assertions(shapes.state_shape),
        *record.get_turn_assertions(),
        *record.get_view_assertions(shapes.sees_shape),
        # *record.get_incidental_assertions(),
        clingo_helper.get_terminal_at_assertion(ply=record.horizon, invert=is_final_view),
        *temporal_rules.static,
        *temporal_rules.dynamic,
        *temporal_rules.statemachine,
        clingo_helper.create_pick_move_rule(record.horizon),
    )
    ctl = _get_ctl(
        sentences=(),
        rules=rules,
        models=0,
        parallel_mode=parallel_mode,
        logger=functools.partial(ControlContainer.log, context="possible states"),
    )
    return ctl, rules


get_possible_states_models = _get_developments_models


def transform_possible_states_model(symbols: Sequence[clingo.Symbol]) -> State:
    subrelations = (gdl.Subrelation.from_clingo_symbol(symbol) for symbol in symbols)
    return State(frozenset(subrelations))
