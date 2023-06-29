import collections
import contextlib
import functools
import logging
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Mapping, MutableMapping, Union

import clingo
from clingo import ast as clingo_ast
from typing_extensions import Self

from pyggp import _clingo as clingo_helper
from pyggp import game_description_language as gdl
from pyggp._clingo_interpreter.base import _get_ctl
from pyggp.engine_primitives import Move, Role, State, View

log = logging.getLogger("pyggp")

MutableStateLiteralMapping = MutableMapping[gdl.Subrelation, int]
MutableActionLiteralMapping = MutableMapping[Role, MutableMapping[Move, int]]


@dataclass(frozen=True)
class ControlContainer:
    role: clingo.Control = field(default_factory=clingo.Control)
    init: clingo.Control = field(default_factory=clingo.Control)
    next: clingo.Control = field(default_factory=clingo.Control)
    next_state_to_literal: MutableStateLiteralMapping = field(default_factory=dict)
    next_action_to_literal: MutableActionLiteralMapping = field(
        default_factory=functools.partial(collections.defaultdict, dict),
    )
    sees: clingo.Control = field(default_factory=clingo.Control)
    sees_state_to_literal: MutableStateLiteralMapping = field(default_factory=dict)
    legal: clingo.Control = field(default_factory=clingo.Control)
    legal_state_to_literal: MutableStateLiteralMapping = field(default_factory=dict)
    goal: clingo.Control = field(default_factory=clingo.Control)
    goal_state_to_literal: MutableStateLiteralMapping = field(default_factory=dict)
    terminal: clingo.Control = field(default_factory=clingo.Control)
    terminal_state_to_literal: MutableStateLiteralMapping = field(default_factory=dict)

    @classmethod
    def from_ruleset(cls, ruleset: gdl.Ruleset) -> Self:
        role_ctl = ControlContainer.get_ctl(
            sentences=ruleset.role_rules,
            rules=(clingo_helper.SHOW_ROLE,),
            context="role",
        )
        init_ctl = ControlContainer.get_ctl(
            sentences=ruleset.init_rules,
            rules=(clingo_helper.SHOW_INIT,),
            context="init",
        )
        next_ctl = ControlContainer.get_ctl(
            sentences=ruleset.rules,
            rules=(
                *clingo_helper.EXTERNALS,
                clingo_helper.SHOW_NEXT,
            ),
            context="next",
        )
        sees_sentences = ruleset.rules if ruleset.sees_rules else ()
        sees_rules = (*clingo_helper.EXTERNALS, clingo_helper.SHOW_SEES) if ruleset.sees_rules else ()
        sees_ctl = ControlContainer.get_ctl(
            sentences=sees_sentences,
            rules=sees_rules,
            context="sees",
        )
        legal_ctl = ControlContainer.get_ctl(
            sentences=ruleset.rules,
            rules=(
                *clingo_helper.EXTERNALS,
                clingo_helper.SHOW_LEGAL,
            ),
            context="legal",
        )
        goal_ctl = ControlContainer.get_ctl(
            sentences=ruleset.rules,
            rules=(
                *clingo_helper.EXTERNALS,
                clingo_helper.SHOW_GOAL,
            ),
            context="goal",
        )
        terminal_ctl = ControlContainer.get_ctl(
            sentences=ruleset.rules,
            rules=(
                *clingo_helper.EXTERNALS,
                clingo_helper.SHOW_TERMINAL,
            ),
            context="terminal",
        )
        return cls(
            role=role_ctl,
            init=init_ctl,
            next=next_ctl,
            sees=sees_ctl,
            legal=legal_ctl,
            goal=goal_ctl,
            terminal=terminal_ctl,
        )

    @staticmethod
    def get_ctl(
        sentences: Iterable[gdl.Sentence] = (),
        rules: Iterable[clingo_ast.AST] = (),
        *,
        context: str,
        models=2,
    ):
        ctl = (
            clingo.Control()
            if not sentences
            else _get_ctl(
                sentences=sentences,
                rules=rules,
                models=models,
                logger=functools.partial(ControlContainer.log, context=context),
            )
        )
        ctl.configuration.solve.models = models
        ctl.ground((("base", ()),))
        return ctl

    @staticmethod
    def log(message_code: clingo.MessageCode, message: str, context: str) -> None:
        for level in ("debug", "info", "warning", "error"):
            message = message.replace(f"<pyggp>:0:0: {level}: ", "")
        if message_code in (
            clingo.MessageCode.OperationUndefined,
            clingo.MessageCode.RuntimeError,
            clingo.MessageCode.VariableUnbounded,
        ):
            log.error("%s: %s", context, message)
        elif message_code in (
            clingo.MessageCode.GlobalVariable,
            clingo.MessageCode.Other,
        ):
            log.warning("%s: %s", context, message)
        elif message_code in (clingo.MessageCode.AtomUndefined,):
            log.info("%s: %s", context, message)
        else:
            log.debug("%s: %s", context, message)


def lookup_state_literal(
    ctl: clingo.Control,
    subrelation: gdl.Subrelation,
    state_to_literal: MutableStateLiteralMapping,
) -> int:
    if subrelation not in state_to_literal:
        symbolic_atom = clingo.Function(name="true", arguments=(subrelation.as_clingo_symbol(),))
        lit = ctl.symbolic_atoms[symbolic_atom]
        if lit is None:
            return 0
        assert lit is not None, f"Assumption: ctl.symbolic_atoms[symbolic_atom] is not None (subrelation={subrelation})"
        state_to_literal[subrelation] = lit.literal
    assert subrelation in state_to_literal, f"Guarantee: {subrelation} in state_shape"
    return state_to_literal[subrelation]


@contextlib.contextmanager
def _set_state(
    ctl: clingo.Control,
    state_to_literal: MutableStateLiteralMapping,
    current: Union[State, View],
) -> Iterator[clingo.Control]:
    ground_literals = tuple(lookup_state_literal(ctl, subrelation, state_to_literal) for subrelation in current)
    try:
        for ground_literal in ground_literals:
            ctl.assign_external(external=ground_literal, truth=True)
        yield ctl
    finally:
        for ground_literal in ground_literals:
            ctl.assign_external(external=ground_literal, truth=False)


def lookup_action_literal(
    ctl: clingo.Control,
    role: Role,
    move: Move,
    action_to_literal: MutableActionLiteralMapping,
) -> int:
    if role not in action_to_literal or move not in action_to_literal[role]:
        symbolic_atom = clingo.Function(name="does", arguments=(role.as_clingo_symbol(), move.as_clingo_symbol()))
        lit = ctl.symbolic_atoms[symbolic_atom]
        assert lit is not None, "Assumption: ctl.symbolic_atoms[symbolic_atom] is not None"
        action_to_literal[role][move] = lit.literal

    assert role in action_to_literal, f"Guarantee: role in action_shape"
    assert move in action_to_literal[role], f"Guarantee: move in action_shape[role]"
    return action_to_literal[role][move]


@contextlib.contextmanager
def _set_turn(
    ctl: clingo.Control,
    action_to_literal: MutableActionLiteralMapping,
    turn: Mapping[Role, Move],
) -> Iterator[clingo.Control]:
    ground_literals = tuple(lookup_action_literal(ctl, role, move, action_to_literal) for role, move in turn.items())
    try:
        for ground_literal in ground_literals:
            ctl.assign_external(external=ground_literal, truth=True)
        yield ctl
    finally:
        for ground_literal in ground_literals:
            ctl.assign_external(external=ground_literal, truth=False)
