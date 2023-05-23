"""Interpreters for GDL rulesets."""
import collections
import functools
import itertools
import logging
import operator
import time
from dataclasses import dataclass, field
from typing import (
    Callable,
    ClassVar,
    FrozenSet,
    Iterator,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    TypeVar,
    Union,
)

import cachetools
import clingo
import clingo.ast as clingo_ast
import clingox.backend as clingox_backend
from typing_extensions import NotRequired, Self, assert_type

import pyggp._clingo as clingo_helper
import pyggp.game_description_language as gdl
from pyggp._caching import (
    get_goals_sizeof,
    get_legal_moves_sizeof,
    get_next_state_sizeof,
    get_roles_in_control_sizeof,
    get_sees_sizeof,
    hashedkey,
    hashedmethodkey,
    is_terminal_sizeof,
    size_str_to_int,
)
from pyggp.engine_primitives import Development, DevelopmentStep, Move, Play, Role, State, Turn, View
from pyggp.exceptions.interpreter_exceptions import (
    InterpreterError,
    ModelTimeoutInterpreterError,
    MoreThanOneModelInterpreterError,
    MultipleGoalsInterpreterError,
    SolveTimeoutInterpreterError,
    UnsatDevelopmentsInterpreterError,
    UnsatGoalInterpreterError,
    UnsatInitInterpreterError,
    UnsatLegalInterpreterError,
    UnsatNextInterpreterError,
    UnsatRolesInterpreterError,
    UnsatSeesInterpreterError,
)
from pyggp.records import Record

log: logging.Logger = logging.getLogger("pyggp")


def development_from_symbols(symbols: Sequence[clingo.Symbol]) -> Development:
    """Create a development from clingo symbols.

    Args:
        symbols: Clingo symbols

    Returns:
        Development

    """
    ply_state_map: MutableMapping[int, Set[gdl.Subrelation]] = collections.defaultdict(set)
    ply_turn_map: MutableMapping[int, MutableMapping[Role, Move]] = collections.defaultdict(dict)
    for symbol in symbols:
        if symbol.match("holds_at", 2):
            subrelation = gdl.Subrelation.from_clingo_symbol(symbol.arguments[0])
            ply = symbol.arguments[1].number
            ply_state_map[ply].add(subrelation)
        elif symbol.match("does_at", 3):
            role = Role(gdl.Subrelation.from_clingo_symbol(symbol.arguments[0]))
            move = Move(gdl.Subrelation.from_clingo_symbol(symbol.arguments[1]))
            ply = symbol.arguments[2].number
            ply_turn_map[ply][role] = move
    assert list(range(0, len(ply_state_map))) == sorted(ply_state_map.keys())
    return Development(
        tuple(
            DevelopmentStep(
                state=State(frozenset(ply_state_map[ply])),
                turn=Turn(ply_turn_map[ply]) if ply_turn_map[ply] else None,
            )
            for ply in range(0, len(ply_state_map))
        ),
    )


_K = TypeVar("_K")
_V = TypeVar("_V")


def _get_lru_cache_factory(
    max_size: int,
    getsizeof: Optional[Callable[[_V], int]] = None,
) -> Callable[[], cachetools.Cache[_K, _V]]:
    def get_lru_cache() -> cachetools.Cache[_K, _V]:
        return cachetools.LRUCache(max_size, getsizeof)

    return get_lru_cache


_get_roles_in_control_cache: cachetools.Cache[Tuple[int], FrozenSet[Role]] = cachetools.LRUCache(
    maxsize=500_000,
    getsizeof=get_roles_in_control_sizeof,
)


@dataclass(frozen=True)
class Interpreter:
    """An interpreter for a GDL ruleset.

    Used to calculate the state transitions for games. The interpreter itself is stateless.

    """

    ruleset: gdl.Ruleset = field(default_factory=gdl.Ruleset, repr=False)
    """The ruleset to interpret."""

    @property
    def has_incomplete_information(self) -> bool:
        """Whether the game has incomplete information."""
        return bool(self.ruleset.sees_rules)

    def get_roles(self) -> FrozenSet[Role]:
        """Return the roles in the game.

        This is static information. Roles should never change during the game.

        Returns:
            Roles in the game

        """
        raise NotImplementedError

    def get_init_state(self) -> State:
        """Return the initial state of the game.

        Returns:
            Initial state of the game

        """
        raise NotImplementedError

    def get_next_state(self, current: Union[State, View], *plays: Play) -> State:
        """Return the next state of the game.

        Args:
            current: Current state or view
            plays: Plays of the roles in control

        Returns:
            The next state of the game

        """
        raise NotImplementedError

    def get_all_next_states(self, current: Union[State, View]) -> Iterator[Tuple[Turn, State]]:
        """Yields all possible follow states from the given state or view.

        Args:
            current: View or state to get follow states from

        Yields:
            Pairs of turns and states

        """
        if self.is_terminal(current):
            return
        roles_in_control = Interpreter.get_roles_in_control(current)
        all_role_move_pairs = set()
        for role in roles_in_control:
            legal_moves = self.get_legal_moves_by_role(current, role)
            role_move_pairs = set()
            for move in legal_moves:
                role_move_pairs.add((role, move))
            all_role_move_pairs.add(frozenset(role_move_pairs))
        for turn_role_move_pairs in itertools.product(*all_role_move_pairs):
            turn = Turn(frozenset(turn_role_move_pairs))
            next_state = self.get_next_state(current, *turn.as_plays())
            yield turn, next_state

    def get_sees(self, current: Union[State, View]) -> Mapping[Role, View]:
        """Return each role's view of the state.

        Calculates the sees relation for the given state.

        Args:
            current: Current state or view of the game

        Returns:
            Each role's view of the state

        See Also:
            :meth:`get_sees_by_role`

        """
        raise NotImplementedError

    def get_sees_by_role(self, current: Union[State, View], role: Role) -> View:
        """Return the given role's view of the state.

        Args:
            current: Current state or view of the game
            role: Role to get the view for

        Returns:
            Role's view of the state

        See Also:
            :meth:`get_sees`

        """
        return self.get_sees(current).get(role, View(State(frozenset())))

    def get_legal_moves(self, current: Union[State, View]) -> Mapping[Role, FrozenSet[Move]]:
        """Return the legal moves for each role.

        Calculates the legal relation for the given state or view.

        Args:
            current: Current state or view of the game

        Returns:
            The legal moves for each role

        See Also:
            :meth:`is_legal`

        """
        raise NotImplementedError

    def is_legal(self, current: Union[State, View], role: Role, move: Move) -> bool:
        """Check if the given move is legal for the given role.

        Args:
            current: Current state or view of the game
            role: Role to check the move for
            move: Move to check

        Returns:
            True if the given move is legal for the given role, False otherwise

        See Also:
            :meth:`get_legal_moves`

        """
        return move in self.get_legal_moves(current).get(role, frozenset())

    def get_legal_moves_by_role(self, current: Union[State, View], role: Role) -> FrozenSet[Move]:
        """Return the legal moves for the given role.

        Args:
            current: Current state or view of the game
            role: Role to get the legal moves for

        Returns:
            Legal moves for the given role

        """
        return self.get_legal_moves(current).get(role, frozenset())

    def get_goals(self, current: Union[State, View]) -> Mapping[Role, Optional[int]]:
        """Return the goals for each role.

        Calculates the goal relation for the given state.

        Args:
            current: Current state or view of the game

        Returns:
            Mapping of role to its goal (utility value)

        See Also:
            :meth:`get_goal_by_role`

        """
        raise NotImplementedError

    def get_goal_by_role(self, current: Union[State, View], role: Role) -> Optional[int]:
        """Return the goal (utility value) for the given role.

        Args:
            current: Current state or view of the game
            role: Role to get the goal for

        Returns:
            Goal for the given role

        See Also:
            :meth:`get_goals`

        """
        return self.get_goals(current).get(role, None)

    def is_terminal(self, current: Union[State, View]) -> bool:
        """Check if the given state is terminal.

        Args:
            current: Current state or view of the game

        Returns:
            True if the given state is terminal, False otherwise

        """
        raise NotImplementedError

    def get_developments(
        self,
        record: Record,
    ) -> Iterator[Development]:
        """Return all possible developments for the given record.

        Args:
            record: Record of the game

        Returns:
            All possible developments for the given record

        """
        raise NotImplementedError

    @staticmethod
    @cachetools.cached(
        cache=_get_roles_in_control_cache,
        # Disables arg-type. Because: hashedkey depends on the arguments of the wrapped function.
        key=hashedkey,  # type: ignore[arg-type]
        info=True,
    )
    def get_roles_in_control(current: Union[State, View]) -> FrozenSet[Role]:
        """Return the roles in control from the given state or view.

        Args:
            current: Current state or view.

        Returns:
            Roles in control from the given state or view.

        """
        return frozenset(
            Role(subrelation.symbol.arguments[0])
            for subrelation in current
            if isinstance(subrelation.symbol, gdl.Relation)
            and subrelation.symbol.matches_signature(name="control", arity=1)
        )

    @staticmethod
    def get_ranks(goals: Mapping[Role, Optional[int]]) -> Mapping[Role, int]:
        """Return the ranks for each role.

        Args:
            goals: Mapping of role to its goal (utility value)

        Returns:
            Mapping of role to its rank

        """
        ranking: MutableSequence[Union[int, None]] = []
        ranking.extend(sorted((goal for goal in goals.values() if isinstance(goal, int)), reverse=True))
        ranking.append(None)
        return {role: ranking.index(goal) for role, goal in goals.items()}


@dataclass(frozen=True)
class ClingoInterpreter(Interpreter):
    """An interpreter for a GDL ruleset_resource using clingo.

    Queries the clingo solver for the state transitions. Translates the GDL ruleset_resource to ASP.

    """

    # region Inner Classes

    class TemporalClassification(TypedDict):
        """Describes how a GDL sentence is to be transformed to a temporal ASP rule."""

        name: NotRequired[str]
        "Associated name of the temporal ASP rule (default {name}_at)."
        timeshift: NotRequired[Optional[int]]
        "Associated timeshift of the temporal ASP rule (default for dynamic 0, default for static None)."
        time: NotRequired[Union[str, int, None]]
        "Associated time argument of the temporal ASP rule (default for dynamic '__time', default for static None)."
        is_static: NotRequired[bool]
        "Whether the temporal ASP rule is static (default False)."
        program: NotRequired[str]
        "Associated program of the temporal ASP rule (default for dynamic 'dynamic', default for static 'static')."

    @dataclass(frozen=True)
    class ClingoASTRules:
        """Container for the clingo AST rules."""

        roles_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        init_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        next_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        sees_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        legal_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        goal_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        terminal_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)

        dynamic_rules: Sequence[Tuple[clingo_ast.AST, Sequence[clingo_ast.AST]]] = field(default_factory=tuple)

        dynamic_pick_plays: ClassVar[Callable[[int], clingo_ast.AST]] = staticmethod(
            clingo_helper.create_pick_move_rule,
        )

        @classmethod
        def from_ruleset(cls, ruleset: gdl.Ruleset) -> Self:
            """Create a ClingoASTRules object from a GDL ruleset.

            Args:
                ruleset: GDL ruleset to create the ClingoASTRules object from

            """
            roles_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.role_rules)
            init_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.init_rules)
            next_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.next_rules)
            sees_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.sees_rules)
            legal_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.legal_rules)
            goal_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.goal_rules)
            terminal_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.terminal_rules)
            temporal_classification = ClingoInterpreter.ClingoASTRules.build_temporal_classification(ruleset)
            dynamic_rules_map: MutableMapping[str, MutableSequence[clingo_ast.AST]] = collections.defaultdict(list)
            dynamic_rules_map["statemachine"] = []

            program_parameters_map: MutableMapping[str, Set[clingo_ast.AST]] = collections.defaultdict(set)
            program_parameters_map["statemachine"] = {clingo_helper.create_id("__time")}

            for sentence in ruleset.rules:
                rule = ClingoInterpreter.ClingoASTRules.sentence_to_rule(sentence, temporal_classification)
                is_static = temporal_classification[sentence.head.signature].get("is_static", False)
                program = temporal_classification[sentence.head.signature].get(
                    "program",
                    "static" if is_static else "dynamic",
                )
                time_param = temporal_classification[sentence.head.signature].get(
                    "time",
                    None if is_static else "__time",
                )
                if isinstance(time_param, str):
                    parameter = clingo_helper.create_id(time_param)
                    program_parameters_map[program].add(parameter)
                dynamic_rules_map[program].append(rule)

            mutable_dynamic_rules = []
            for program, rules in dynamic_rules_map.items():
                parameters = tuple(program_parameters_map[program])
                mutable_dynamic_rules.append(
                    (clingo_helper.create_program(program, parameters=parameters), tuple(rules)),
                )
            dynamic_rules = tuple(mutable_dynamic_rules)

            return cls(
                roles_rules=roles_rules,
                init_rules=init_rules,
                next_rules=next_rules,
                sees_rules=sees_rules,
                legal_rules=legal_rules,
                goal_rules=goal_rules,
                terminal_rules=terminal_rules,
                dynamic_rules=dynamic_rules,
            )

        @staticmethod
        def build_temporal_classification(
            ruleset: gdl.Ruleset,
        ) -> Mapping[gdl.Relation.Signature, "ClingoInterpreter.TemporalClassification"]:
            """Build the temporal classification for the GDL ruleset."""
            signature_temporal_classification_map = {
                gdl.Relation.Signature("role", 1): ClingoInterpreter.TemporalClassification(
                    name="role",
                    is_static=True,
                ),
                gdl.Relation.Signature("init", 1): ClingoInterpreter.TemporalClassification(
                    name="holds_at",
                    time=0,
                    is_static=True,
                ),
                gdl.Relation.Signature("next", 1): ClingoInterpreter.TemporalClassification(
                    name="holds_at",
                    timeshift=1,
                    program="statemachine",
                ),
                gdl.Relation.Signature("true", 1): ClingoInterpreter.TemporalClassification(
                    name="holds_at",
                ),
                gdl.Relation.Signature("does", 2): ClingoInterpreter.TemporalClassification(),
                gdl.Relation.Signature("sees", 2): ClingoInterpreter.TemporalClassification(),
                gdl.Relation.Signature("legal", 2): ClingoInterpreter.TemporalClassification(),
                gdl.Relation.Signature("goal", 2): ClingoInterpreter.TemporalClassification(),
                gdl.Relation.Signature("terminal", 0): ClingoInterpreter.TemporalClassification(),
            }
            relevant_signatures = set(signature_temporal_classification_map.keys())
            has_changed = True
            while has_changed:
                __before_len = len(relevant_signatures)
                relevant_signatures.update(
                    body_literal.atom.signature
                    for sentence in ruleset.rules
                    for body_literal in sentence.body
                    if not body_literal.is_comparison
                )
                relevant_signatures.update(
                    sentence.head.signature
                    for sentence in ruleset.rules
                    if any(body_literal.atom.signature in relevant_signatures for body_literal in sentence.body)
                )
                __after_len = len(relevant_signatures)
                has_changed = __before_len != __after_len

            has_changed = True
            while has_changed:
                has_changed = False
                for sentence in ruleset.rules:
                    head_relation = sentence.head
                    head_signature = head_relation.signature
                    if head_signature in signature_temporal_classification_map:
                        continue
                    if head_signature not in relevant_signatures:
                        signature_temporal_classification_map[
                            head_signature
                        ] = ClingoInterpreter.TemporalClassification(is_static=True)
                        continue
                    has_changed = True
                    is_static = True
                    time_ = None
                    for body_literal in sentence.body:
                        body_relation = body_literal.atom
                        body_signature = body_relation.signature
                        if body_signature not in signature_temporal_classification_map:
                            continue
                        body_classification = signature_temporal_classification_map[body_signature]
                        body_is_static = body_classification.get("is_static", False)
                        is_static = is_static and body_is_static
                        body_time = body_classification.get("time", "__time") if not body_is_static else None
                        if time_ is None:
                            time_ = body_time
                    name = f"{head_relation.name}_static" if is_static else f"{head_relation.name}_at"
                    signature_temporal_classification_map[head_signature] = ClingoInterpreter.TemporalClassification(
                        name=name,
                        time=time_,
                        is_static=is_static,
                    )
            return signature_temporal_classification_map

        @staticmethod
        def sentence_to_rule(
            sentence: gdl.Sentence,
            temporal_classification: Mapping[gdl.Relation.Signature, "ClingoInterpreter.TemporalClassification"],
        ) -> clingo_ast.AST:
            """Convert a GDL sentence to a Clingo rule.

            Args:
                sentence: GDL sentence to convert
                temporal_classification: Mapping from GDL relation signatures to temporal classifications

            Returns:
                Clingo rule

            """
            clingo_head_function = ClingoInterpreter.ClingoASTRules.relation_to_clingo_function(
                sentence.head,
                temporal_classification,
            )
            clingo_head_literal = clingo_helper.create_literal(atom=clingo_helper.create_atom(clingo_head_function))
            clingo_body_literals = []
            for body_literal in sentence.body:
                if body_literal.is_comparison:
                    clingo_body_literals.append(body_literal.as_clingo_ast())
                else:
                    function = ClingoInterpreter.ClingoASTRules.relation_to_clingo_function(
                        body_literal.atom,
                        temporal_classification,
                    )
                    sign = body_literal.sign.as_clingo_ast()
                    clingo_body_literals.append(clingo_helper.create_literal(sign, clingo_helper.create_atom(function)))
            return clingo_helper.create_rule(clingo_head_literal, tuple(clingo_body_literals))

        @staticmethod
        def relation_to_clingo_function(
            relation: gdl.Relation,
            signature_temporal_classification_map: Mapping[
                gdl.Relation.Signature,
                "ClingoInterpreter.TemporalClassification",
            ],
        ) -> clingo_ast.AST:
            """Convert a GDL relation to a Clingo function.

            Args:
                relation: GDL relation to convert
                signature_temporal_classification_map: Mapping from GDL relation signatures to temporal classifications

            Returns:
                Clingo function

            """
            signature = relation.signature
            if signature not in signature_temporal_classification_map:
                return relation.as_clingo_ast()
            temporal_classification = signature_temporal_classification_map[signature]
            is_static = temporal_classification.get("is_static", False)
            if not is_static:
                name = temporal_classification.get("name", f"{relation.name}_at")
                time_ = temporal_classification.get("time", "__time")
                timeshift = temporal_classification.get("timeshift", None)
            else:
                name = temporal_classification.get("name", f"{relation.name}_static")
                time_ = temporal_classification.get("time", None)
                timeshift = temporal_classification.get("timeshift", None)

            last_arguments: Sequence[clingo_ast.AST] = ()
            if time_ is not None:
                time_ast = None
                if isinstance(time_, int):
                    time_ast = clingo_helper.create_symbolic_term(symbol=clingo.Number(time_))
                elif isinstance(time_, str):
                    time_ast = clingo_helper.create_function(name=time_)
                assert time_ast is not None, "Assumption: time is either an int, str or None."
                if timeshift is not None:
                    last_argument = clingo_helper.create_binary_operation(
                        left=time_ast,
                        right=clingo_helper.create_symbolic_term(clingo.Number(timeshift)),
                    )
                else:
                    last_argument = time_ast
                last_arguments = (last_argument,)
            arguments: Sequence[clingo_ast.AST] = (
                *(argument.as_clingo_ast() for argument in relation.arguments),
                *last_arguments,
            )
            return clingo_helper.create_function(name=name, arguments=arguments)

    # Disables N818 (Exception name should be named with an Error suffix). Because this is not an error, but an effect.
    class Unsat(Exception):  # noqa: N818
        """Raised when the query is unsatisfiable."""

    # endregion

    # region Attributes and Properties

    model_timeout: float = 8.0
    """Timeout for the model query in seconds."""
    solve_timeout: float = 10.0
    """Timeout for all model queries in seconds."""
    _rules: ClingoASTRules = field(default_factory=ClingoASTRules, repr=False)
    _get_next_state_cache: cachetools.Cache[Tuple[int, Tuple[int, ...]], State] = field(
        default_factory=_get_lru_cache_factory(500_000, getsizeof=get_next_state_sizeof),
        repr=False,
        hash=False,
    )
    _get_sees_cache: cachetools.Cache[Tuple[int], View] = field(
        default_factory=_get_lru_cache_factory(500_000, getsizeof=get_sees_sizeof),
        repr=False,
        hash=False,
    )
    _get_legal_moves_cache: cachetools.Cache[Tuple[int], Mapping[Role, FrozenSet[Move]]] = field(
        default_factory=_get_lru_cache_factory(500_000, getsizeof=get_legal_moves_sizeof),
        repr=False,
        hash=False,
    )
    _get_goals_cache: cachetools.Cache[Tuple[int], Mapping[Role, Optional[int]]] = field(
        default_factory=_get_lru_cache_factory(500_000, getsizeof=get_goals_sizeof),
        repr=False,
        hash=False,
    )
    _is_terminal_cache: cachetools.Cache[Tuple[int], bool] = field(
        default_factory=_get_lru_cache_factory(500_000, getsizeof=is_terminal_sizeof),
        repr=False,
        hash=False,
    )

    # endregion

    # region Constructors

    @classmethod
    def from_ruleset(
        cls,
        ruleset: gdl.Ruleset,
        *,
        model_timeout: float = 8.0,
        solve_timeout: float = 10.0,
        cache_size: Union[int, float, str, None] = None,
        get_next_state_cache_quota: float = 0.55,
        get_sees_cache_quota: float = 0.2,
        get_legal_moves_cache_quota: float = 0.1,
        get_goals_cache_quota: float = 0.1,
        is_terminal_cache_quota: float = 0.05,
    ) -> Self:
        """Create a ClingoInterpreter from a ruleset.

        Args:
            ruleset: Ruleset to create the interpreter from
            model_timeout: Timeout for the model query in seconds (default: 8.0)
            solve_timeout: Timeout for total solve call in seconds (default: 10.0)
            cache_size: Size of the cache in bytes (default: 1GB)
            get_next_state_cache_quota: Quota of the cache for get_next_state (default: 0.55)
            get_sees_cache_quota: Quota of the cache for get_sees (default: 0.2)
            get_legal_moves_cache_quota: Quota of the cache for get_legal_moves (default: 0.1)
            get_goals_cache_quota: Quota of the cache for get_goals (default: 0.1)
            is_terminal_cache_quota: Quota of the cache for is_terminal (default: 0.05)

        Returns:
            ClingoInterpreter

        """
        if cache_size is None:
            cache_size = 1_000_000_000
        elif isinstance(cache_size, str):
            cache_size = size_str_to_int(cache_size)
        elif isinstance(cache_size, float):
            cache_size = int(cache_size)
        assert isinstance(cache_size, int), "Assumption: cache_size is an int"

        if not ruleset.sees_rules:
            get_sees_cache_quota = 0.0

        total_quota = (
            get_next_state_cache_quota
            + get_sees_cache_quota
            + get_legal_moves_cache_quota
            + get_goals_cache_quota
            + is_terminal_cache_quota
        )
        get_next_state_cache_quota /= total_quota
        get_sees_cache_quota /= total_quota
        get_legal_moves_cache_quota /= total_quota
        get_goals_cache_quota /= total_quota
        is_terminal_cache_quota /= total_quota

        get_next_state_cache_size = int(cache_size * get_next_state_cache_quota)
        get_sees_cache_size = int(cache_size * get_sees_cache_quota)
        get_legal_moves_cache_size = int(cache_size * get_legal_moves_cache_quota)
        get_goals_cache_size = int(cache_size * get_goals_cache_quota)
        is_terminal_cache_size = int(cache_size * is_terminal_cache_quota)

        get_next_state_cache: cachetools.Cache[Tuple[int, Tuple[int, ...]], State] = cachetools.LRUCache(
            maxsize=get_next_state_cache_size,
            getsizeof=get_next_state_sizeof,
        )
        get_sees_cache: cachetools.Cache[Tuple[int], View] = cachetools.LRUCache(
            maxsize=get_sees_cache_size,
            getsizeof=get_sees_sizeof,
        )
        get_legal_moves_cache: cachetools.Cache[Tuple[int], Mapping[Role, FrozenSet[Move]]] = cachetools.LRUCache(
            maxsize=get_legal_moves_cache_size,
            getsizeof=get_legal_moves_sizeof,
        )
        get_goals_cache: cachetools.Cache[Tuple[int], Mapping[Role, Optional[int]]] = cachetools.LRUCache(
            maxsize=get_goals_cache_size,
            getsizeof=get_goals_sizeof,
        )
        is_terminal_cache: cachetools.Cache[Tuple[int], bool] = cachetools.LRUCache(
            maxsize=is_terminal_cache_size,
            getsizeof=is_terminal_sizeof,
        )

        return cls(
            ruleset=ruleset,
            model_timeout=model_timeout,
            solve_timeout=solve_timeout,
            _rules=ClingoInterpreter.ClingoASTRules.from_ruleset(ruleset),
            _get_next_state_cache=get_next_state_cache,
            _get_sees_cache=get_sees_cache,
            _get_legal_moves_cache=get_legal_moves_cache,
            _get_goals_cache=get_goals_cache,
            _is_terminal_cache=is_terminal_cache,
        )

    # endregion

    # region Methods

    def get_roles(self) -> FrozenSet[Role]:
        """Return the roles in the game.

        This is static information. Roles should never change during the game.

        Returns:
            Roles in the game

        Raises:
            UnsatRolesInterpreterError: The role sentences are unsatisfiable

        """
        ctl = ClingoInterpreter.get_ctl(rules=self._rules.roles_rules, context="get_roles")
        try:
            model = self._get_model(ctl)
            roles = frozenset(
                Role(gdl.Subrelation.from_clingo_symbol(symbol.arguments[0]))
                for symbol in model
                if symbol.match("role", 1)
            )
        except ClingoInterpreter.Unsat as unsat:
            raise UnsatRolesInterpreterError from unsat
        return roles

    def get_init_state(self) -> State:
        """Return the initial state of the game.

        Returns:
            Initial state of the game

        Raises:
            UnsatInitInterpreterError: The init sentences are unsatisfiable

        """
        ctl = ClingoInterpreter.get_ctl(rules=self._rules.init_rules, context="get_init_state")
        model = self._get_model(ctl)
        try:
            state = State(
                frozenset(
                    gdl.Subrelation.from_clingo_symbol(symbol.arguments[0])
                    for symbol in model
                    if symbol.match("init", 1)
                ),
            )
        except ClingoInterpreter.Unsat as unsat:
            raise UnsatInitInterpreterError from unsat
        return state

    @cachetools.cachedmethod(cache=operator.attrgetter("_get_next_state_cache"), key=hashedmethodkey)
    def get_next_state(self, current: Union[State, View], *plays: Play) -> State:
        """Return the next state of the game.

        Args:
            current: Current state or view
            plays: Plays of the roles in control

        Returns:
            The next state of the game

        Raises:
            UnsatNextInterpreterError: The next sentences are unsatisfiable

        """
        ctl = ClingoInterpreter.get_ctl(
            state=current,
            plays=plays,
            rules=self._rules.next_rules,
            context="get_next_state",
        )
        model = self._get_model(ctl)
        try:
            state = State(
                frozenset(
                    gdl.Subrelation.from_clingo_symbol(symbol.arguments[0])
                    for symbol in model
                    if symbol.match("next", 1)
                ),
            )
        except ClingoInterpreter.Unsat as unsat:
            raise UnsatNextInterpreterError from unsat
        return state

    @cachetools.cachedmethod(cache=operator.attrgetter("_get_sees_cache"))
    def get_sees(self, current: Union[State, View]) -> Mapping[Role, View]:
        """Return each role's view of the state.

        Calculates the sees relation for the given state.

        Args:
            current: Current state or view of the game

        Returns:
            Each role's view of the state

        Raises:
            UnsatSeesInterpreterError: The sees sentences are unsatisfiable

        See Also:
            :meth:`get_sees_by_role`

        """
        if not self.has_incomplete_information:
            return {role: View(current) for role in self.get_roles()}
        ctl = ClingoInterpreter.get_ctl(state=current, rules=self._rules.sees_rules, context="get_sees")
        model = self._get_model(ctl)
        try:
            symbols = tuple(model)
        except ClingoInterpreter.Unsat as unsat:
            raise UnsatSeesInterpreterError from unsat
        sees: MutableMapping[Role, Set[gdl.Subrelation]] = collections.defaultdict(set)
        for symbol in symbols:
            if symbol.match("sees", 2):
                role = Role(gdl.Subrelation.from_clingo_symbol(symbol.arguments[0]))
                sees[role].add(gdl.Subrelation.from_clingo_symbol(symbol.arguments[1]))
        return {role: View(State(frozenset(subrelations))) for role, subrelations in sees.items()}

    @cachetools.cachedmethod(cache=operator.attrgetter("_get_legal_moves_cache"))
    def get_legal_moves(self, current: Union[State, View]) -> Mapping[Role, FrozenSet[Move]]:
        """Return the legal moves for each role.

        Calculates the legal relation for the given state or view.

        Args:
            current: Current state or view of the game

        Returns:
            The legal moves for each role

        Raises:
            UnsatLegalInterpreterError: The legal sentences are unsatisfiable

        See Also:
            :meth:`is_legal`

        """
        ctl = ClingoInterpreter.get_ctl(state=current, rules=self._rules.legal_rules, context="get_legal_moves")
        model = self._get_model(ctl)
        try:
            symbols = tuple(model)
        except ClingoInterpreter.Unsat as unsat:
            raise UnsatLegalInterpreterError from unsat
        legal_moves_mutable: MutableMapping[Role, Set[Move]] = collections.defaultdict(set)
        for symbol in symbols:
            if symbol.match("legal", 2):
                role = Role(gdl.Subrelation.from_clingo_symbol(symbol.arguments[0]))
                legal_moves_mutable[role].add(Move(gdl.Subrelation.from_clingo_symbol(symbol.arguments[1])))
        return {role: frozenset(moves) for role, moves in legal_moves_mutable.items()}

    @cachetools.cachedmethod(cache=operator.attrgetter("_get_goals_cache"))
    def get_goals(self, current: Union[State, View]) -> Mapping[Role, Optional[int]]:
        """Return the goals for each role.

        Calculates the goal relation for the given state.

        Args:
            current: Current state or view of the game

        Returns:
            Mapping of role to its goal (utility value)

        Raises:
            UnsatGoalInterpreterError: The goal sentences are unsatisfiable

        See Also:
            :meth:`get_goal_by_role`

        """
        ctl = ClingoInterpreter.get_ctl(state=current, rules=self._rules.goal_rules, context="get_goals")
        model = self._get_model(ctl)
        try:
            symbols = tuple(model)
        except ClingoInterpreter.Unsat as unsat:
            raise UnsatGoalInterpreterError from unsat
        goals_mutable: MutableMapping[Role, Optional[int]] = collections.defaultdict(None)
        for symbol in symbols:
            if symbol.match("goal", 2):
                role = Role(gdl.Subrelation.from_clingo_symbol(symbol.arguments[0]))
                if role in goals_mutable:
                    raise MultipleGoalsInterpreterError
                goals_mutable[role] = symbol.arguments[1].number
        return {role: goals_mutable.get(role) for role in self.get_roles()}

    @cachetools.cachedmethod(cache=operator.attrgetter("_is_terminal_cache"))
    def is_terminal(self, current: Union[State, View]) -> bool:
        """Check if the given state is terminal.

        Args:
            current: Current state or view of the game

        Returns:
            True if the given state is terminal, False otherwise

        """
        ctl = ClingoInterpreter.get_ctl(state=current, rules=self._rules.terminal_rules, context="is_terminal")
        with clingox_backend.SymbolicBackend(ctl.backend()) as backend:
            backend.add_rule(neg_body=(clingo.Function("terminal", []),))
        model = self._get_model(ctl)
        try:
            next(model, None)
        except ClingoInterpreter.Unsat:
            return False
        return True

    def get_developments(self, record: Record) -> Iterator[Development]:
        """Return all possible developments for the given record.

        Args:
            record: Record of the game

        Yields:
            All possible developments for the given record

        """
        ctl, rules = self._get_development_ctl(record)
        try:
            yield from self._get_development_model(ctl, record)
        except InterpreterError:
            log.debug(
                "Error while getting developments. Solving the following rules until the horizon %d:\n%s",
                record.horizon,
                "\n".join(rules),
            )
            raise

    def _get_development_model(self, ctl: clingo.Control, record: Record) -> Iterator[Development]:
        ctl.ground(
            (
                ("base", ()),
                ("static", ()),
                *(("dynamic", (clingo.Number(__time),)) for __time in range(0, record.horizon + 1)),
                *(("statemachine", (clingo.Number(__time),)) for __time in range(0, record.horizon)),
            ),
        )
        # Disables mypy. Because contract guarantees that handle is not SolveResult when called with yield_=True or
        # async_=True.
        with ctl.solve(yield_=True, async_=True) as handle:  # type: ignore[union-attr]
            handle.resume()
            done = handle.wait(self.model_timeout)
            if not done:
                handle.cancel()
                raise ModelTimeoutInterpreterError
            model = handle.model()
            if model is None:
                raise UnsatDevelopmentsInterpreterError
            symbols = model.symbols(shown=True)
            yield development_from_symbols(symbols)
            while model is not None:
                handle.resume()
                done = handle.wait(self.model_timeout)
                if not done:
                    handle.cancel()
                    raise ModelTimeoutInterpreterError
                model = handle.model()
                if model is not None:
                    symbols = model.symbols(shown=True)
                    yield development_from_symbols(symbols)

    def _get_development_ctl(self, record: Record) -> Tuple[clingo.Control, Sequence[str]]:
        ctl = clingo.Control()
        # Disables mypy. Because: clingo does not provide a typesafe way to set the configuration.
        ctl.configuration.solve.models = 0  # type: ignore[union-attr]

        rules = []
        with clingo_ast.ProgramBuilder(ctl) as ast_builder:
            for rule in record.get_state_assertions():
                ast_builder.add(rule)
                rules.append(str(rule))
            if self.has_incomplete_information:
                for rule in record.get_view_assertions():
                    ast_builder.add(rule)
                    rules.append(str(rule))
            for rule in record.get_turn_assertions():
                ast_builder.add(rule)
                rules.append(str(rule))
            for program, dynamic_rules in self._rules.dynamic_rules:
                ast_builder.add(program)
                rules.append(str(program))
                for rule in dynamic_rules:
                    ast_builder.add(rule)
                    rules.append(str(rule))
                if program == clingo_helper.PROGRAM_STATEMACHINE:
                    horizon = record.horizon
                    assert_type(horizon, int)
                    assert isinstance(horizon, int)
                    rule = ClingoInterpreter.ClingoASTRules.dynamic_pick_plays(horizon)
                    ast_builder.add(rule)
                    rules.append(str(rule))
        return ctl, rules

    def _get_model(self, ctl: clingo.Control) -> Iterator[clingo.Symbol]:
        total_wait_time = 0.0
        ctl.ground([("base", [])])
        # Disables mypy. Because contract guarantees that handle is not SolveResult when called with yield_=True or
        # async_=True
        with ctl.solve(yield_=True, async_=True) as handle:  # type: ignore[union-attr]
            handle.resume()
            __start = time.monotonic()
            done = handle.wait(self.model_timeout)
            total_wait_time += time.monotonic() - __start
            if not done:
                handle.cancel()
                raise ModelTimeoutInterpreterError
            model = handle.model()
            if model is None:
                raise ClingoInterpreter.Unsat
            yield from model.symbols(shown=True)
            handle.resume()
            __start = time.monotonic()
            done = handle.wait(self.solve_timeout - total_wait_time)
            total_wait_time += time.monotonic() - __start
            if not done:
                handle.cancel()
                raise SolveTimeoutInterpreterError
            model = handle.model()
            if model is not None:
                raise MoreThanOneModelInterpreterError

    # endregion

    # region Static Methods

    @staticmethod
    def _get_log(context: Optional[str] = None) -> Callable[[clingo.MessageCode, str], None]:
        # Disables SLF001 ( Private member accessed). Because this its own static method.
        logger = functools.partial(ClingoInterpreter._log, context=context)  # noqa: SLF001
        assert callable(logger)
        # noinspection PyTypeChecker
        return logger

    @staticmethod
    def _log(message_code: clingo.MessageCode, message: str, context: Optional[str] = None) -> None:
        if message_code in (
            clingo.MessageCode.OperationUndefined,
            clingo.MessageCode.RuntimeError,
            clingo.MessageCode.VariableUnbounded,
        ):
            log.error("%s%s", f"{context}: " if context is not None else "", message)
        elif message_code in (
            clingo.MessageCode.AtomUndefined,
            clingo.MessageCode.GlobalVariable,
            clingo.MessageCode.Other,
        ):
            log.warning("%s%s", f"{context}: " if context is not None else "", message)
        else:
            log.debug("%s%s", f"{context}: " if context is not None else "", message)

    @staticmethod
    def get_ctl(
        state: Union[State, View, None] = None,
        plays: Sequence[Play] = (),
        rules: Sequence[clingo_ast.AST] = (),
        context: Optional[str] = None,
    ) -> clingo.Control:
        """Return a clingo control object with the given state, plays and rules.

        The control object assumes that there is only one model.

        Args:
            state: State or view to be added to the control object
            plays: Plays to be added to the control object
            rules: Rules to be added to the control object
            context: Context in which the control object is used

        Returns:
            A clingo control object with the given state, plays and rules

        """
        # Disables SLF001 ( Private member accessed). Because this its own static method.
        ctl = clingo.Control(logger=ClingoInterpreter._get_log(context=context))  # noqa: SLF001
        # Disables mypy. Because clingo does not define types for configuration options.
        ctl.configuration.solve.models = 2  # type: ignore[union-attr]

        asp_rules: MutableSequence[str] = []

        if rules:
            with clingo_ast.ProgramBuilder(ctl) as builder:
                for rule in rules:
                    builder.add(rule)
                    asp_rules.append(str(rule))

        with clingox_backend.SymbolicBackend(ctl.backend()) as backend:
            if state is not None and state:
                for subrelation in state:
                    head = clingo.Function("true", arguments=(subrelation.as_clingo_symbol(),))
                    backend.add_rule(head=(head,))
                    asp_rules.append(f"{head}.")

            if plays:
                for play in plays:
                    head = play.as_clingo_symbol()
                    backend.add_rule(head=(head,))
                    asp_rules.append(f"{head}.")

        return ctl

    # endregion
