"""Interpreters for GDL rulesets."""
import collections
import itertools
import logging
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    FrozenSet,
    Iterator,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import cachetools
import cachetools.keys as cachetools_keys
import clingo
from typing_extensions import Self

import pyggp._clingo as clingo_helper
import pyggp.game_description_language as gdl
from pyggp._caching import (
    get_roles_in_control_sizeof,
)
from pyggp._clingo_interpreter import (
    CacheContainer,
    TemporalRuleContainer,
    _create_developments_ctl,
    _get_ctl,
    _get_developments_models,
    _get_model,
    _get_shows,
    _set_state,
    _set_turn,
    _transform_model,
    transform_developments_model,
)
from pyggp.engine_primitives import Development, DevelopmentStep, Move, Role, State, Turn, View
from pyggp.exceptions.interpreter_exceptions import (
    GoalNotIntegerInterpreterError,
    MultipleGoalsInterpreterError,
    UnsatGoalInterpreterError,
    UnsatInitInterpreterError,
    UnsatInterpreterError,
    UnsatLegalInterpreterError,
    UnsatNextInterpreterError,
    UnsatRolesInterpreterError,
    UnsatSeesInterpreterError,
    UnsatTerminalInterpreterError,
)
from pyggp.records import Record

log: logging.Logger = logging.getLogger("pyggp")


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


_K = TypeVar("_K")
_V = TypeVar("_V")


def _get_lru_cache_factory(
    max_size: int,
    getsizeof: Optional[Callable[[_V], int]] = None,
) -> Callable[[], cachetools.Cache[_K, _V]]:
    def get_lru_cache() -> cachetools.Cache[_K, _V]:
        return cachetools.LRUCache(max_size, getsizeof)

    return get_lru_cache


_get_roles_in_control_cache: cachetools.Cache[State, FrozenSet[Role]] = cachetools.LRUCache(
    maxsize=50_000_000,
    getsizeof=get_roles_in_control_sizeof,
)


@dataclass(frozen=True)
class Interpreter:
    """An interpreter for a GDL ruleset.

    Used to calculate the state transitions for games. The interpreter itself is stateless.

    """

    ruleset: gdl.Ruleset = field(default_factory=gdl.Ruleset)
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

    def get_next_state(self, current: Union[State, View], turn: Mapping[Role, Move]) -> State:
        """Return the next state of the game.

        Args:
            current: Current state or view
            turn: Mapping from roles to moves

        Returns:
            Next state of the game

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
            turn = Turn(turn_role_move_pairs)
            next_state = self.get_next_state(current, turn)
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
        key=cachetools_keys.hashkey,
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
    """An interpreter for a GDL ruleset using clingo."""

    _control: clingo.Control = field(default_factory=clingo.Control, repr=False)
    _temporal_rule_container: TemporalRuleContainer = field(default_factory=TemporalRuleContainer, repr=False)
    _cache_container: CacheContainer = field(default_factory=CacheContainer, repr=False)

    @classmethod
    def from_ruleset(cls, ruleset: gdl.Ruleset, *args: Any, **kwargs: Any) -> Self:
        ctl = _get_ctl(
            sentences=ruleset.rules,
            rules=(
                clingo_helper.EXTERNAL_TRUE_INIT,
                clingo_helper.EXTERNAL_TRUE_NEXT,
                clingo_helper.EXTERNAL_DOES_ROLE_LEGAL,
                *_get_shows(ruleset),
            ),
            models=2,
        )
        ctl.ground((("base", ()),))
        temporal_rule_container = TemporalRuleContainer.from_ruleset(ruleset)
        return cls(
            ruleset=ruleset,
            _control=ctl,
            _temporal_rule_container=temporal_rule_container,
        )

    def get_roles(self) -> FrozenSet[Role]:
        model = _get_model(self._control)
        subrelations = _transform_model(model, gdl.Relation.Signature("role", 1), unpack=0)
        roles = (Role(subrelation) for subrelation in subrelations)
        try:
            return frozenset(roles)
        except UnsatInterpreterError:
            raise UnsatRolesInterpreterError from UnsatInterpreterError

    def get_init_state(self) -> State:
        model = _get_model(self._control)
        subrelations = _transform_model(model, gdl.Relation.Signature("init", 1), unpack=0)
        try:
            return State(frozenset(subrelations))
        except UnsatInterpreterError:
            raise UnsatInitInterpreterError from UnsatInterpreterError

    def get_next_state(self, current: Union[State, View], turn: Mapping[Role, Move]) -> State:
        with _set_state(self._control, current) as _ctl, _set_turn(_ctl, turn) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model, gdl.Relation.Signature("next", 1), unpack=0)
            try:
                return State(frozenset(subrelations))
            except UnsatInterpreterError:
                raise UnsatNextInterpreterError from UnsatInterpreterError

    def get_sees(self, current: Union[State, View]) -> Mapping[Role, View]:
        if not self.has_incomplete_information:
            return {role: View(current) for role in self.get_roles()}
        with _set_state(self._control, current) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model, gdl.Relation.Signature("sees", 2))
            role_subrelation_pairs = (
                (Role(subrelation.symbol.arguments[0]), subrelation.symbol.arguments[1]) for subrelation in subrelations
            )
            try:
                sees: Mapping[Role, Set[gdl.Subrelation]] = collections.defaultdict(set)
                for role, subrelation in role_subrelation_pairs:
                    sees[role].add(subrelation)
                return {role: View(State(frozenset(subrelations))) for role, subrelations in sees.items()}
            except UnsatInterpreterError:
                raise UnsatSeesInterpreterError from UnsatInterpreterError

    def get_legal_moves(self, current: Union[State, View]) -> Mapping[Role, FrozenSet[Move]]:
        with _set_state(self._control, current) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model, gdl.Relation.Signature("legal", 2))
            role_move_pairs = (
                (Role(subrelation.symbol.arguments[0]), Move(subrelation.symbol.arguments[1]))
                for subrelation in subrelations
            )
            try:
                legal_moves: Mapping[Role, Set[Move]] = collections.defaultdict(set)
                for role, move in role_move_pairs:
                    legal_moves[role].add(move)
                return {role: frozenset(moves) for role, moves in legal_moves.items()}
            except UnsatInterpreterError:
                raise UnsatLegalInterpreterError from UnsatInterpreterError

    def get_goals(self, current: Union[State, View]) -> Mapping[Role, Optional[int]]:
        with _set_state(self._control, current) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model, gdl.Relation.Signature("goal", 2))
            role_goal_pairs = (
                (Role(subrelation.symbol.arguments[0]), subrelation.symbol.arguments[1]) for subrelation in subrelations
            )
            try:
                roles = self.get_roles()
                goals: MutableMapping[Role, Optional[int]] = {}
                for role, goal in role_goal_pairs:
                    if role in goals:
                        raise MultipleGoalsInterpreterError
                    if goal.is_number:
                        assert isinstance(goal.symbol, gdl.Number)
                        goals[role] = goal.symbol.number
                    else:
                        raise GoalNotIntegerInterpreterError
                return {role: goals.get(role, None) for role in roles}
            except UnsatInterpreterError:
                raise UnsatGoalInterpreterError from UnsatInterpreterError

    def is_terminal(self, current: Union[State, View]) -> bool:
        with _set_state(self._control, current) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model, gdl.Relation.Signature("terminal", 0))
            try:
                return bool(tuple(subrelations))
            except UnsatInterpreterError:
                raise UnsatTerminalInterpreterError from UnsatInterpreterError

    def get_developments(self, record: Record) -> Iterator[Development]:
        ctl, rules = _create_developments_ctl(temporal_rules=self._temporal_rule_container, record=record)
        offset = record.offset
        horizon = record.horizon
        models = _get_developments_models(ctl, offset=offset, horizon=horizon)
        developments = (
            transform_developments_model(symbols=symbols, offset=offset, horizon=horizon) for symbols in models
        )
        return developments
