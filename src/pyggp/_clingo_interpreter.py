import collections
import contextlib
import functools
import logging
from dataclasses import dataclass, field
from typing import (
    Callable,
    FrozenSet,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import clingo
from clingo import ast as clingo_ast
from typing_extensions import Self

import pyggp._clingo as clingo_helper
from pyggp import game_description_language as gdl
from pyggp.engine_primitives import Development, DevelopmentStep, Move, Role, State, Turn, View
from pyggp.exceptions.interpreter_exceptions import (
    ModelTimeoutInterpreterError,
    MoreThanOneModelInterpreterError,
    UnsatDevelopmentsInterpreterError,
    UnsatInterpreterError,
)
from pyggp.records import Record

log = logging.getLogger("pyggp")

MutableStateShape = MutableMapping[gdl.Subrelation, int]
MutableActionShape = MutableMapping[Role, MutableMapping[Move, int]]


@dataclass(frozen=True)
class ControlContainer:
    role: clingo.Control = field(default_factory=clingo.Control)
    init: clingo.Control = field(default_factory=clingo.Control)
    next: clingo.Control = field(default_factory=clingo.Control)
    next_state_shape: MutableStateShape = field(default_factory=dict)
    next_action_shape: MutableActionShape = field(default_factory=functools.partial(collections.defaultdict, dict))
    sees: clingo.Control = field(default_factory=clingo.Control)
    sees_state_shape: MutableStateShape = field(default_factory=dict)
    legal: clingo.Control = field(default_factory=clingo.Control)
    legal_state_shape: MutableStateShape = field(default_factory=dict)
    goal: clingo.Control = field(default_factory=clingo.Control)
    goal_state_shape: MutableStateShape = field(default_factory=dict)
    terminal: clingo.Control = field(default_factory=clingo.Control)
    terminal_state_shape: MutableStateShape = field(default_factory=dict)

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
        sees_ctl = ControlContainer.get_ctl(
            sentences=ruleset.rules,
            rules=(
                *clingo_helper.EXTERNALS,
                clingo_helper.SHOW_SEES,
            ),
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
        if message_code in (
            clingo.MessageCode.OperationUndefined,
            clingo.MessageCode.RuntimeError,
            clingo.MessageCode.VariableUnbounded,
        ):
            log.error("%s: %s", context, message)
        elif message_code in (
            clingo.MessageCode.AtomUndefined,
            clingo.MessageCode.GlobalVariable,
            clingo.MessageCode.Other,
        ):
            log.warning("%s: %s", context, message)
        else:
            log.debug("%s: %s", context, message)


@dataclass(frozen=True)
class TemporalInformation:
    name: str
    time: Union[int, str, None] = None
    timeshift: Optional[int] = None

    @classmethod
    def static(cls, name: str) -> Self:
        return cls(name=f"{name}_static", time=None)

    @classmethod
    def dynamic(cls, name: str, time: Union[int, str] = "__time", timeshift: Optional[int] = None) -> Self:
        return cls(name=f"{name}_at", time=time, timeshift=timeshift)


Categorization = Mapping[gdl.Relation.Signature, TemporalInformation]
MutableCategorization = MutableMapping[gdl.Relation.Signature, TemporalInformation]

role_signature = gdl.Relation.Signature(name="role", arity=1)
init_signature = gdl.Relation.Signature(name="init", arity=1)
next_signature = gdl.Relation.Signature(name="next", arity=1)
true_signature = gdl.Relation.Signature(name="true", arity=1)
does_signature = gdl.Relation.Signature(name="does", arity=2)
sees_signature = gdl.Relation.Signature(name="sees", arity=2)
legal_signature = gdl.Relation.Signature(name="legal", arity=2)
goal_signature = gdl.Relation.Signature(name="goal", arity=2)
terminal_signature = gdl.Relation.Signature(name="terminal", arity=0)

base_static_categorization: Categorization = {
    role_signature: TemporalInformation(name="role"),
    init_signature: TemporalInformation(name="holds_at", time=0, timeshift=None),
}
base_statemachine_categorization: Categorization = {
    next_signature: TemporalInformation(name="holds_at", time="__time", timeshift=1),
}
base_dynamic_categorization: Categorization = {
    true_signature: TemporalInformation(name="holds_at", time="__time"),
    does_signature: TemporalInformation(name="does_at", time="__time"),
    sees_signature: TemporalInformation(name="sees_at", time="__time"),
    legal_signature: TemporalInformation(name="legal_at", time="__time"),
    goal_signature: TemporalInformation(name="goal_at", time="__time"),
    terminal_signature: TemporalInformation(name="terminal_at", time="__time"),
}


def create_temporal_function(
    name: str,
    arguments: Sequence[clingo_ast.AST],
    time_: Union[int, str, None],
    timeshift: Optional[int],
) -> clingo_ast.AST:
    if time_ is None:
        return clingo_helper.create_function(name=name, arguments=arguments)
    if isinstance(time_, str):
        time_ast = clingo_helper.create_function(name=time_)
    else:
        assert isinstance(time_, int)
        time_ast = clingo_helper.create_symbolic_term(symbol=clingo.Number(time_))

    if timeshift is not None:
        timeshift_ast = clingo_helper.create_symbolic_term(symbol=clingo.Number(timeshift))
        time_ast = clingo_helper.create_binary_operation(
            operator_type=clingo_ast.BinaryOperator.Plus,
            left=time_ast,
            right=timeshift_ast,
        )
    return clingo_helper.create_function(name=name, arguments=(*arguments, time_ast))


@dataclass(frozen=True)
class TemporalRuleContainer:
    static: Sequence[clingo_ast.AST]
    dynamic: Sequence[clingo_ast.AST]
    statemachine: Sequence[clingo_ast.AST]

    @property
    def rules(self) -> Iterator[clingo_ast.AST]:
        yield from self.static
        yield from self.dynamic
        yield from self.statemachine

    @classmethod
    def from_ruleset(cls, ruleset: gdl.Ruleset) -> Self:
        static_categorization, dynamic_categorization = TemporalRuleContainer.categorize_signatures(ruleset.rules)
        return cls.transform_sentences(
            sentences=ruleset.rules,
            static_categorization=static_categorization,
            dynamic_categorization=dynamic_categorization,
        )

    @classmethod
    def transform_sentences(
        cls,
        sentences: Sequence[gdl.Sentence],
        static_categorization: Categorization,
        dynamic_categorization: Categorization,
    ) -> Self:
        visitor = TemporalTransformer(
            static=static_categorization,
            dynamic=dynamic_categorization,
            statemachine=base_statemachine_categorization,
        )

        static = (
            clingo_helper.PROGRAM_STATIC,
            *(
                visitor.visit(sentence.as_clingo_ast())
                for sentence in sentences
                if sentence.head.signature in static_categorization
            ),
        )
        statemachine = (
            clingo_helper.PROGRAM_STATEMACHINE,
            *(
                visitor.visit(sentence.as_clingo_ast())
                for sentence in sentences
                if sentence.head.signature in base_statemachine_categorization
            ),
        )
        dynamic = (
            clingo_helper.PROGRAM_DYNAMIC,
            *(
                visitor.visit(sentence.as_clingo_ast())
                for sentence in sentences
                if sentence.head.signature in dynamic_categorization
            ),
        )
        return TemporalRuleContainer(static=static, dynamic=dynamic, statemachine=statemachine)

    @staticmethod
    def categorize_signatures(
        sentences: Sequence[gdl.Sentence],
    ) -> Tuple[Categorization, Categorization]:
        static_categorization: MutableCategorization = {**base_static_categorization}
        dynamic_categorization: MutableCategorization = {**base_dynamic_categorization}
        body_only_signatures = set()
        changes = True
        while changes:
            changes = False
            for sentence in sentences:
                head, body = sentence.head, sentence.body
                body_only_signatures.update(
                    literal.atom.signature
                    for literal in body
                    if not literal.is_comparison
                    and not any(
                        literal.atom.signature in signatures
                        for signatures in (static_categorization, dynamic_categorization)
                    )
                )
                if any(
                    head.signature in signatures
                    for signatures in (static_categorization, dynamic_categorization, base_statemachine_categorization)
                ):
                    continue
                changes = True
                if any(literal.atom.signature in dynamic_categorization for literal in body):
                    dynamic_categorization[head.signature] = TemporalInformation.dynamic(name=head.name)
                    body_only_signatures.discard(head.signature)
                else:
                    static_categorization[head.signature] = TemporalInformation.static(name=head.name)

        for signature in body_only_signatures:
            static_categorization[signature] = TemporalInformation.static(name=signature.name)
        return static_categorization, dynamic_categorization


@dataclass(frozen=True)
class TemporalTransformer(clingo_ast.Transformer):
    static: Mapping[gdl.Relation.Signature, TemporalInformation]
    dynamic: Mapping[gdl.Relation.Signature, TemporalInformation]
    statemachine: Mapping[gdl.Relation.Signature, TemporalInformation]

    def visit_Function(self, function: clingo_ast.AST) -> clingo_ast.AST:
        original_name = function.name if function.name != "" else None
        original_arity = len(function.arguments)
        original_signature = gdl.Relation.Signature(name=original_name, arity=original_arity)
        temporal_information = None
        for mapping in (self.static, self.dynamic, self.statemachine):
            if original_signature in mapping:
                temporal_information = mapping[original_signature]
                break
        if temporal_information is None:
            return function
        return create_temporal_function(
            name=temporal_information.name,
            arguments=function.arguments,
            time_=temporal_information.time,
            timeshift=temporal_information.timeshift,
        )


_K = TypeVar("_K")
_V = TypeVar("_V")

_NextCache = MutableMapping[int, MutableMapping[Union[State, View], MutableMapping[Turn, State]]]
_AllNextCache = MutableMapping[int, MutableMapping[Union[State, View], Set[Tuple[Turn, State]]]]
_SeesCache = MutableMapping[int, MutableMapping[Union[State, View], Mapping[Role, View]]]
_LegalCache = MutableMapping[int, MutableMapping[Union[State, View], Mapping[Role, FrozenSet[Move]]]]
_GoalCache = MutableMapping[int, MutableMapping[Union[State, View], Mapping[Role, int]]]
_TerminalCache = MutableMapping[int, MutableMapping[Union[State, View], bool]]


def _state_to_dict_defaultdict_factory() -> collections.defaultdict[Union[State, View], MutableMapping[_K, _V]]:
    return collections.defaultdict(dict)


def _state_to_set_defaultdict_factory() -> collections.defaultdict[Union[State, View], Set[_V]]:
    return collections.defaultdict(set)


def _default_next_cache_factory() -> _NextCache:
    return collections.defaultdict(_state_to_dict_defaultdict_factory)


def _default_all_next_cache_factory() -> _AllNextCache:
    return collections.defaultdict(_state_to_set_defaultdict_factory)


def _default_sees_cache_factory() -> _SeesCache:
    return collections.defaultdict(_state_to_dict_defaultdict_factory)


def _default_legal_cache_factory() -> _LegalCache:
    return collections.defaultdict(_state_to_dict_defaultdict_factory)


def _default_goal_cache_factory() -> _GoalCache:
    return collections.defaultdict(_state_to_dict_defaultdict_factory)


def _default_terminal_cache_factory() -> _TerminalCache:
    return collections.defaultdict(dict)


@dataclass
class CacheContainer:
    roles: Optional[FrozenSet[Role]] = field(default=None)
    init: Optional[State] = field(default=None)
    next: _NextCache = field(default_factory=_default_next_cache_factory)
    all_next: _AllNextCache = field(default_factory=_default_all_next_cache_factory)
    sees: _SeesCache = field(default_factory=_default_sees_cache_factory)
    legal: _LegalCache = field(default_factory=_default_legal_cache_factory)
    goal: _GoalCache = field(default_factory=_default_goal_cache_factory)
    terminal: _TerminalCache = field(default_factory=_default_terminal_cache_factory)

    def clear(self) -> None:
        self.roles = None
        self.init = None
        self.next.clear()
        self.all_next.clear()
        self.sees.clear()
        self.legal.clear()
        self.goal.clear()
        self.terminal.clear()


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


def lookup_state_shape(ctl: clingo.Control, subrelation: gdl.Subrelation, state_shape: MutableStateShape) -> int:
    if subrelation not in state_shape:
        symbolic_atom = clingo.Function(name="true", arguments=(subrelation.as_clingo_symbol(),))
        lit = ctl.symbolic_atoms[symbolic_atom]
        if lit is None:
            return 0
        assert lit is not None, f"Assumption: ctl.symbolic_atoms[symbolic_atom] is not None (subrelation={subrelation})"
        state_shape[subrelation] = lit.literal
    assert subrelation in state_shape, f"Guarantee: {subrelation} in state_shape"
    return state_shape[subrelation]


@contextlib.contextmanager
def _set_state(
    ctl: clingo.Control,
    state_shape: MutableMapping[gdl.Subrelation, int],
    current: Union[State, View],
) -> Iterator[clingo.Control]:
    ground_literals = tuple(lookup_state_shape(ctl, subrelation, state_shape) for subrelation in current)
    try:
        for ground_literal in ground_literals:
            ctl.assign_external(external=ground_literal, truth=True)
        yield ctl
    finally:
        for ground_literal in ground_literals:
            ctl.assign_external(external=ground_literal, truth=False)


def lookup_action_shape(
    ctl: clingo.Control,
    role: Role,
    move: Move,
    action_shape: MutableActionShape,
) -> int:
    if role not in action_shape or move not in action_shape[role]:
        symbolic_atom = clingo.Function(name="does", arguments=(role.as_clingo_symbol(), move.as_clingo_symbol()))
        lit = ctl.symbolic_atoms[symbolic_atom]
        assert lit is not None, "Assumption: ctl.symbolic_atoms[symbolic_atom] is not None"
        action_shape[role][move] = lit.literal

    assert role in action_shape, f"Guarantee: role in action_shape"
    assert move in action_shape[role], f"Guarantee: move in action_shape[role]"
    return action_shape[role][move]


@contextlib.contextmanager
def _set_turn(
    ctl: clingo.Control,
    action_shape: MutableActionShape,
    turn: Mapping[Role, Move],
) -> Iterator[clingo.Control]:
    ground_literals = tuple(lookup_action_shape(ctl, role, move, action_shape) for role, move in turn.items())
    try:
        for ground_literal in ground_literals:
            ctl.assign_external(external=ground_literal, truth=True)
        yield ctl
    finally:
        for ground_literal in ground_literals:
            ctl.assign_external(external=ground_literal, truth=False)


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
