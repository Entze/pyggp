"""Interpreters for GDL rulesets."""
import abc
import collections
import functools
import itertools
import logging
import multiprocessing
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    FrozenSet,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

import cachetools
import cachetools.keys as cachetools_keys
import clingo
import clingo.ast as clingo_ast
from typing_extensions import Self

import pyggp._clingo as clingo_helper
import pyggp.game_description_language as gdl
from pyggp._caching import (
    get_roles_in_control_sizeof,
)
from pyggp._clingo_interpreter.base import _get_ctl, _get_model, _transform_model
from pyggp._clingo_interpreter.control_containers import ControlContainer, _set_state, _set_turn
from pyggp._clingo_interpreter.developments import (
    _create_developments_ctl,
    _get_developments_models,
    transform_developments_model,
)
from pyggp._clingo_interpreter.possible_states import (
    create_possible_states_ctl,
    get_possible_states_models,
    transform_possible_states_model,
)
from pyggp._clingo_interpreter.shape_containers import ShapeContainer
from pyggp._clingo_interpreter.temporal_rule_containers import TemporalRuleContainer
from pyggp._logging import rich
from pyggp.engine_primitives import Development, Move, ParallelMode, Role, State, Turn, View
from pyggp.exceptions.interpreter_exceptions import (
    GoalNotIntegerInterpreterError,
    MultipleGoalsInterpreterError,
    PlyOutsideOfBoundsError,
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

if TYPE_CHECKING:
    # TODO: Remove this when python 3.8 is no longer supported.
    RolesInControlCache = cachetools.Cache[State, FrozenSet[Role]]
else:
    RolesInControlCache = cachetools.Cache

log: logging.Logger = logging.getLogger("pyggp")

_get_roles_in_control_cache: RolesInControlCache = cachetools.LRUCache(
    maxsize=50_000_000,
    getsizeof=get_roles_in_control_sizeof,
)


class Interpreter(Protocol):
    """An interpreter for a GDL ruleset.

    Used to calculate the state transitions for games. The interpreter itself is stateless.

    """

    ruleset: gdl.Ruleset

    @property
    @abc.abstractmethod
    def has_incomplete_information(self) -> bool:
        """Whether the game has incomplete information."""

    @classmethod
    def from_ruleset(cls, ruleset: gdl.Ruleset) -> Self:
        """Create an interpreter from a ruleset.

        Args:
            ruleset: Ruleset to create the interpreter from

        Returns:
            Interpreter for the given ruleset

        """

    def get_roles(self) -> FrozenSet[Role]:
        """Return the roles in the game.

        This is static information. Roles should never change during the game.

        Returns:
            Roles in the game

        """

    def get_init_state(self) -> State:
        """Return the initial state of the game.

        Returns:
            Initial state of the game

        """

    def get_next_state(self, current: Union[State, View], turn: Mapping[Role, Move]) -> State:
        """Return the next state of the game.

        Args:
            current: Current state or view
            turn: Mapping from roles to moves

        Returns:
            Next state of the game

        """

    def get_all_next_states(self, current: Union[State, View]) -> Iterator[Tuple[Turn, State]]:
        """Yields all possible follow states from the given state or view.

        Args:
            current: View or state to get follow states from

        Yields:
            Pairs of turns and states

        """

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

    def get_legal_moves_by_role(self, current: Union[State, View], role: Role) -> FrozenSet[Move]:
        """Return the legal moves for the given role.

        Args:
            current: Current state or view of the game
            role: Role to get the legal moves for

        Returns:
            Legal moves for the given role

        """

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

    def is_terminal(self, current: Union[State, View]) -> bool:
        """Check if the given state is terminal.

        Args:
            current: Current state or view of the game

        Returns:
            True if the given state is terminal, False otherwise

        """

    def get_developments(
        self,
        record: Record,
        *,
        last_ply_is_final_state: Optional[bool] = None,
    ) -> Iterator[Development]:
        """Return all possible developments for the given record.

        Args:
            record: Record of the game
            last_ply_is_final_state: Whether the last ply of the record is a final state

        Returns:
            All possible developments for the given record

        """

    def get_possible_states(self, record: Record, ply: int, *, is_final: Optional[bool] = None) -> Iterator[State]:
        """Yield all possible states for the given record at the given ply.

        Args:
            record: Record of the game
            ply: Ply
            is_final: Whether the given ply is a final state

        Yields:
            All possible states at the given ply

        """

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


@dataclass
class AbstractInterpreter(Interpreter):
    """An interpreter for a GDL ruleset.

    Used to calculate the state transitions for games. The interpreter itself is stateless.

    """

    ruleset: gdl.Ruleset = field(default_factory=gdl.Ruleset)
    """The ruleset to interpret."""

    @property
    def has_incomplete_information(self) -> bool:
        """Whether the game has incomplete information."""
        return bool(self.ruleset.sees_rules)

    @abc.abstractmethod
    def get_roles(self) -> FrozenSet[Role]:
        """Return the roles in the game.

        This is static information. Roles should never change during the game.

        Returns:
            Roles in the game

        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_init_state(self) -> State:
        """Return the initial state of the game.

        Returns:
            Initial state of the game

        """
        raise NotImplementedError

    @abc.abstractmethod
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

    @abc.abstractmethod
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

    @abc.abstractmethod
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

    @abc.abstractmethod
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

    @abc.abstractmethod
    def is_terminal(self, current: Union[State, View]) -> bool:
        """Check if the given state is terminal.

        Args:
            current: Current state or view of the game

        Returns:
            True if the given state is terminal, False otherwise

        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_developments(
        self,
        record: Record,
        *,
        last_ply_is_final_state: Optional[bool] = None,
    ) -> Iterator[Development]:
        """Return all possible developments for the given record.

        Args:
            record: Record of the game
            last_ply_is_final_state: Whether the last ply is a final state

        Returns:
            All possible developments for the given record

        """
        raise NotImplementedError

    def get_possible_states(self, record: Record, ply: int, *, is_final: Optional[bool] = None) -> Iterator[State]:
        """Yield all possible states for the given record at the given ply.

        Args:
            record: Record of the game
            ply: Ply
            is_final: Whether the ply is a final state

        Yields:
            All possible states at the given ply

        """
        offset = record.offset
        horizon = record.horizon
        if not offset <= ply <= horizon:
            raise PlyOutsideOfBoundsError
        developments = self.get_developments(record, last_ply_is_final_state=is_final)
        shift = ply - offset
        for development in developments:
            yield development[shift].state

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


_K1 = TypeVar("_K1")
_K2 = TypeVar("_K2")
_K3 = TypeVar("_K3")
_V = TypeVar("_V")
_NextCache = MutableMapping[int, MutableMapping[Union[State, View], MutableMapping[Turn, State]]]
_AllNextCache = MutableMapping[int, MutableMapping[Union[State, View], Set[Tuple[Turn, State]]]]
_SeesCache = MutableMapping[int, MutableMapping[Union[State, View], Mapping[Role, View]]]
_LegalCache = MutableMapping[int, MutableMapping[Union[State, View], Mapping[Role, FrozenSet[Move]]]]
_GoalCache = MutableMapping[int, MutableMapping[Union[State, View], Mapping[Role, int]]]
_TerminalCache = MutableMapping[int, MutableMapping[Union[State, View], bool]]


def _get_single_nested_defaultdict_factory(
    factory: Callable[[], _V],
) -> Callable[[], DefaultDict[_K1, DefaultDict[_K2, _V]]]:
    return functools.partial(collections.defaultdict, functools.partial(collections.defaultdict, factory))


@dataclass
class CachingInterpreter(AbstractInterpreter, abc.ABC):
    @dataclass
    class CacheContainer:
        roles: Optional[FrozenSet[Role]] = field(default=None)
        init: Optional[State] = field(default=None)
        next: _NextCache = field(default_factory=_get_single_nested_defaultdict_factory(dict))
        all_next: _AllNextCache = field(default_factory=_get_single_nested_defaultdict_factory(set))
        sees: _SeesCache = field(default_factory=functools.partial(collections.defaultdict, dict))
        legal: _LegalCache = field(default_factory=functools.partial(collections.defaultdict, dict))
        goal: _GoalCache = field(default_factory=functools.partial(collections.defaultdict, dict))
        terminal: _TerminalCache = field(default_factory=functools.partial(collections.defaultdict, dict))

        def clear(self) -> None:
            self.roles = None
            self.init = None
            self.next.clear()
            self.all_next.clear()
            self.sees.clear()
            self.legal.clear()
            self.goal.clear()
            self.terminal.clear()

    cache: CacheContainer = field(default_factory=CacheContainer)
    disable_cache: bool = field(default=False)

    def get_roles(self) -> FrozenSet[Role]:
        if self.cache.roles is None:
            roles = self._get_roles()
            if not self.disable_cache:
                self.cache.roles = roles
        else:
            roles = self.cache.roles
        return roles

    @abc.abstractmethod
    def _get_roles(self) -> FrozenSet[Role]:
        raise NotImplementedError

    def get_init_state(self) -> State:
        if self.cache.init is None:
            init_state = self._get_init_state()
            if not self.disable_cache:
                self.cache.init = init_state
        else:
            init_state = self.cache.init
        return init_state

    @abc.abstractmethod
    def _get_init_state(self) -> State:
        raise NotImplementedError

    def get_next_state(self, current: Union[State, View], turn: Mapping[Role, Move]) -> State:
        current_len = 0
        if not self.disable_cache:
            current_len = len(current)
            if not isinstance(turn, Turn):
                turn = Turn(turn)
        if (
            self.disable_cache
            or current_len not in self.cache.next
            or current not in self.cache.next[current_len]
            or turn not in self.cache.next[current_len][current]
        ):
            next_state = self._get_next_state(current, turn)
            if not self.disable_cache:
                self.cache.next[current_len][current][turn] = next_state
        else:
            next_state = self.cache.next[current_len][current][turn]
        return next_state

    @abc.abstractmethod
    def _get_next_state(self, current: Union[State, View], turn: Mapping[Role, Move]) -> State:
        raise NotImplementedError

    def get_all_next_states(self, current: Union[State, View]) -> Iterator[Tuple[Turn, State]]:
        current_len = len(current)
        if (
            self.disable_cache
            or current_len not in self.cache.all_next
            or current not in self.cache.all_next[current_len]
        ):
            all_next_states = self._get_all_next_states(current)
            if not self.disable_cache:
                for turn, next_state in all_next_states:
                    self.cache.all_next[current_len][current].add((turn, next_state))
                    yield turn, next_state
                return
        else:
            all_next_states = self.cache.all_next[current_len][current]
        yield from all_next_states

    def _get_all_next_states(self, current: Union[State, View]) -> Iterator[Tuple[Turn, State]]:
        return super().get_all_next_states(current)

    def get_sees(self, current: Union[State, View]) -> Mapping[Role, View]:
        if not self.has_incomplete_information:
            return {role: cast(View, current) for role in self.get_roles()}
        current_len = len(current)
        if self.disable_cache or current_len not in self.cache.sees or current not in self.cache.sees[current_len]:
            sees = self._get_sees(current)
            if not self.disable_cache:
                self.cache.sees[current_len][current] = sees
        else:
            sees = self.cache.sees[current_len][current]
        return sees

    @abc.abstractmethod
    def _get_sees(self, current: Union[State, View]) -> Mapping[Role, View]:
        raise NotImplementedError

    def get_legal_moves(self, current: Union[State, View]) -> Mapping[Role, FrozenSet[Move]]:
        current_len = len(current)
        if self.disable_cache or current_len not in self.cache.legal or current not in self.cache.legal[current_len]:
            legal_moves = self._get_legal_moves(current)
            if not self.disable_cache:
                self.cache.legal[current_len][current] = legal_moves
        else:
            legal_moves = self.cache.legal[current_len][current]
        return legal_moves

    @abc.abstractmethod
    def _get_legal_moves(self, current: Union[State, View]) -> Mapping[Role, FrozenSet[Move]]:
        raise NotImplementedError

    def get_goals(self, current: Union[State, View]) -> Mapping[Role, Optional[int]]:
        current_len = len(current)
        if self.disable_cache or current_len not in self.cache.goal or current not in self.cache.goal[current_len]:
            goals = self._get_goals(current)
            if not self.disable_cache:
                self.cache.goal[current_len][current] = goals
        else:
            goals = self.cache.goal[current_len][current]
        return goals

    @abc.abstractmethod
    def _get_goals(self, current: Union[State, View]) -> Mapping[Role, Optional[int]]:
        raise NotImplementedError

    def is_terminal(self, current: Union[State, View]) -> bool:
        current_len = len(current)
        if (
            self.disable_cache
            or current_len not in self.cache.terminal
            or current not in self.cache.terminal[current_len]
        ):
            terminal = self._is_terminal(current)
            if not self.disable_cache:
                self.cache.terminal[current_len][current] = terminal
        else:
            terminal = self.cache.terminal[current_len][current]
        return terminal

    @abc.abstractmethod
    def _is_terminal(self, current: Union[State, View]) -> bool:
        raise NotImplementedError


_StateToRulesCache = MutableMapping[int, MutableMapping[Union[State, View], MutableSequence[clingo_ast.AST]]]
_SubrelationToRuleCache = MutableMapping[gdl.Subrelation, clingo_ast.AST]
_RoleToMoveToRuleCache = MutableMapping[Role, MutableMapping[Move, clingo_ast.AST]]


@dataclass
class ClingoRegroundingInterpreter(CachingInterpreter):
    @dataclass
    class ClingoASTCache:
        roles: Optional[Sequence[clingo_ast.AST]] = None
        init: Optional[Sequence[clingo_ast.AST]] = None
        next: Optional[Sequence[clingo_ast.AST]] = None
        sees: Optional[Sequence[clingo_ast.AST]] = None
        legal: Optional[Sequence[clingo_ast.AST]] = None
        goal: Optional[Sequence[clingo_ast.AST]] = None
        terminal: Optional[Sequence[clingo_ast.AST]] = None
        state_to_rules: _StateToRulesCache = field(default_factory=_get_single_nested_defaultdict_factory(list))
        subrelation_to_rule: _SubrelationToRuleCache = field(default_factory=dict)
        role_to_move_to_rule: _RoleToMoveToRuleCache = field(
            default_factory=functools.partial(collections.defaultdict, dict),
        )

    shape_container: ShapeContainer = field(default_factory=ShapeContainer)
    temporal_rule_container: TemporalRuleContainer = field(default_factory=TemporalRuleContainer)
    parallel_mode: ParallelMode = field(default=1)
    clingo_ast_cache: ClingoASTCache = field(default_factory=ClingoASTCache)

    @classmethod
    def from_ruleset(
        cls,
        ruleset: gdl.Ruleset,
        *args: Any,
        disable_cache: bool = False,
        parallel_mode: Optional[ParallelMode] = None,
        **kwargs: Any,
    ) -> Self:
        shape_container = ShapeContainer.from_ruleset(ruleset)
        temporal_rule_container = TemporalRuleContainer.from_ruleset(ruleset)
        if parallel_mode is None:
            cpu_count = multiprocessing.cpu_count()
            parallel_mode = (max(2, min(64, cpu_count)), "compete")
        return cls(
            ruleset=ruleset,
            shape_container=shape_container,
            temporal_rule_container=temporal_rule_container,
            parallel_mode=parallel_mode,
            disable_cache=disable_cache,
        )

    def _get_roles(self) -> FrozenSet[Role]:
        if self.clingo_ast_cache.roles is None:
            roles_rules = tuple(sentence.as_clingo_ast() for sentence in self.ruleset.role_rules)
            self.clingo_ast_cache.roles = roles_rules
        ctl = self._get_ctl(
            context="roles",
            rules=(*self.clingo_ast_cache.roles, clingo_helper.SHOW_ROLE),
        )
        ctl.ground()
        model = _get_model(ctl)
        subrelations = _transform_model(model, unpack=0)
        try:
            roles = frozenset(Role(role) for role in subrelations)
        except UnsatInterpreterError:
            raise UnsatRolesInterpreterError from UnsatInterpreterError
        return roles

    def _get_init_state(self) -> State:
        if self.clingo_ast_cache.init is None:
            init_rules = tuple(sentence.as_clingo_ast() for sentence in self.ruleset.init_rules)
            self.clingo_ast_cache.init = init_rules
        ctl = self._get_ctl(
            context="init",
            rules=(*self.clingo_ast_cache.init, clingo_helper.SHOW_INIT),
        )
        ctl.ground()
        model = _get_model(ctl)
        subrelations = _transform_model(model, unpack=0)
        try:
            init_state = State(frozenset(subrelations))
        except UnsatInterpreterError:
            raise UnsatInitInterpreterError from UnsatInterpreterError
        return init_state

    def _get_next_state(self, current: Union[State, View], turn: Mapping[Role, Move]) -> State:
        if self.clingo_ast_cache.next is None:
            next_rules = tuple(sentence.as_clingo_ast() for sentence in self.ruleset.next_rules)
            self.clingo_ast_cache.next = next_rules
        ctl = self._get_ctl(
            context="next",
            rules=(*self.clingo_ast_cache.next, clingo_helper.SHOW_NEXT),
            current=current,
            turn=turn,
        )
        ctl.ground()
        model = _get_model(ctl)
        subrelations = _transform_model(model, unpack=0)
        try:
            next_state = State(frozenset(subrelations))
        except UnsatInterpreterError:
            raise UnsatNextInterpreterError from UnsatInterpreterError
        return next_state

    def _get_sees(self, current: Union[State, View]) -> Mapping[Role, View]:
        if not self.has_incomplete_information:
            return {role: cast(View, current) for role in self.get_roles()}
        if self.clingo_ast_cache.sees is None:
            sees_rules = tuple(sentence.as_clingo_ast() for sentence in self.ruleset.sees_rules)
            self.clingo_ast_cache.sees = sees_rules
        ctl = self._get_ctl(
            context="sees",
            rules=(*self.clingo_ast_cache.sees, clingo_helper.SHOW_SEES),
            current=current,
        )
        ctl.ground()
        model = _get_model(ctl)
        subrelations = _transform_model(model)
        sees: DefaultDict[Role, Set[gdl.Subrelation]] = collections.defaultdict(set)
        try:
            for subrelation in subrelations:
                role, sees_subrelation = subrelation.symbol.arguments
                sees[Role(role)].add(sees_subrelation)
        except UnsatInterpreterError:
            raise UnsatSeesInterpreterError from UnsatInterpreterError
        return {role: View(State(frozenset(subrelations))) for role, subrelations in sees.items()}

    def _get_legal_moves(self, current: Union[State, View]) -> Mapping[Role, FrozenSet[Move]]:
        if self.clingo_ast_cache.legal is None:
            legal_rules = tuple(sentence.as_clingo_ast() for sentence in self.ruleset.legal_rules)
            self.clingo_ast_cache.legal = legal_rules
        ctl = self._get_ctl(
            context="legal",
            rules=(*self.clingo_ast_cache.legal, clingo_helper.SHOW_LEGAL),
            current=current,
        )
        ctl.ground()
        model = _get_model(ctl)
        subrelations = _transform_model(model)
        legal: DefaultDict[Role, Set[Move]] = collections.defaultdict(set)
        try:
            for subrelation in subrelations:
                role, legal_subrelation = subrelation.symbol.arguments
                legal[Role(role)].add(Move(legal_subrelation))
        except UnsatInterpreterError:
            raise UnsatLegalInterpreterError from UnsatInterpreterError
        return {role: frozenset(moves) for role, moves in legal.items()}

    def _get_goals(self, current: Union[State, View]) -> Mapping[Role, Optional[int]]:
        if self.clingo_ast_cache.goal is None:
            goal_rules = tuple(sentence.as_clingo_ast() for sentence in self.ruleset.goal_rules)
            self.clingo_ast_cache.goal = goal_rules
        ctl = self._get_ctl(
            context="goal",
            rules=(*self.clingo_ast_cache.goal, clingo_helper.SHOW_GOAL),
            current=current,
        )
        ctl.ground()
        model = _get_model(ctl)
        subrelations = _transform_model(model)
        goals: DefaultDict[Role, MutableSequence[int]] = collections.defaultdict(list)
        try:
            for subrelation in subrelations:
                role, goal_subrelation = subrelation.symbol.arguments
                if not goal_subrelation.is_number:
                    raise GoalNotIntegerInterpreterError
                goals[Role(role)].append(goal_subrelation.symbol.number)
        except UnsatInterpreterError:
            raise UnsatGoalInterpreterError from UnsatInterpreterError

        if any(len(goal) > 1 for role, goal in goals.items()):
            raise MultipleGoalsInterpreterError(goals)
        return {role: goals[role][0] if goals[role] else None for role in self.get_roles()}

    def _is_terminal(self, current: Union[State, View]) -> bool:
        if self.clingo_ast_cache.terminal is None:
            terminal_rules = tuple(sentence.as_clingo_ast() for sentence in self.ruleset.terminal_rules)
            self.clingo_ast_cache.terminal = terminal_rules
        ctl = self._get_ctl(
            context="terminal",
            rules=(*self.clingo_ast_cache.terminal, clingo_helper.SHOW_TERMINAL),
            current=current,
        )
        ctl.ground()
        model = _get_model(ctl)
        subrelations = _transform_model(model)
        try:
            terminal = bool(tuple(subrelations))
        except UnsatInterpreterError:
            raise UnsatTerminalInterpreterError from UnsatInterpreterError
        return terminal

    def _get_ctl(
        self,
        context: str,
        rules: Iterable[clingo_ast.AST],
        current: Union[State, View, None] = None,
        turn: Optional[Mapping[Role, Move]] = None,
    ):
        _state_rules = self._get_state_rules(current)
        _turn_rules = self._get_turn_rules(turn)
        ctl = _get_ctl(
            rules=itertools.chain(_state_rules, _turn_rules, rules),
            models=2,
            logger=ClingoRegroundingInterpreter.get_logger(context),
        )
        return ctl

    def _get_state_rules(self, current: Union[State, View, None] = None) -> Iterator[clingo_ast.AST]:
        if current is None:
            return
        current_len = len(current)
        if (
            self.disable_cache
            or current_len not in self.clingo_ast_cache.state_to_rules
            or current not in self.clingo_ast_cache.state_to_rules[current_len]
        ):
            state_rules = (self._get_subrelation_rule(subrelation) for subrelation in current)
            if not self.disable_cache:
                for rule in state_rules:
                    self.clingo_ast_cache.state_to_rules[current_len][current].append(rule)
                    yield rule
                return
        else:
            state_rules = self.clingo_ast_cache.state_to_rules[current_len][current]
        yield from state_rules

    def _get_subrelation_rule(self, subrelation: gdl.Subrelation) -> clingo_ast.AST:
        if subrelation in self.clingo_ast_cache.subrelation_to_rule:
            return self.clingo_ast_cache.subrelation_to_rule[subrelation]
        func = clingo_helper.create_function(name="true", arguments=(subrelation.as_clingo_ast(),))
        atom = clingo_helper.create_atom(func)
        lit = clingo_helper.create_literal(atom=atom)
        rule = clingo_helper.create_rule(head=lit)
        self.clingo_ast_cache.subrelation_to_rule[subrelation] = rule
        return rule

    def _get_turn_rules(self, turn: Optional[Mapping[Role, Move]] = None) -> Iterator[clingo_ast.AST]:
        if turn is None:
            return
        yield from (self._get_move_rule(role, move) for role, move in turn.items())

    def _get_move_rule(self, role: Role, move: Move) -> clingo_ast.AST:
        if move in self.clingo_ast_cache.role_to_move_to_rule[role]:
            return self.clingo_ast_cache.role_to_move_to_rule[role][move]
        func = clingo_helper.create_function(name="does", arguments=(role.as_clingo_ast(), move.as_clingo_ast()))
        atom = clingo_helper.create_atom(func)
        lit = clingo_helper.create_literal(atom=atom)
        rule = clingo_helper.create_rule(head=lit)
        self.clingo_ast_cache.role_to_move_to_rule[role][move] = rule
        return rule

    def get_developments(
        self,
        record: Record,
        *,
        last_ply_is_final_state: Optional[bool] = None,
    ) -> Iterator[Development]:
        ctl, rules = _create_developments_ctl(
            temporal_rules=self.temporal_rule_container,
            shapes=self.shape_container,
            record=record,
            is_final_view=last_ply_is_final_state,
        )
        offset = record.offset
        horizon = record.horizon
        models = _get_developments_models(ctl, offset=offset, horizon=horizon)
        developments = (
            transform_developments_model(symbols=symbols, offset=offset, horizon=horizon) for symbols in models
        )
        return developments

    def get_possible_states(self, record: Record, ply: int, *, is_final: Optional[bool] = None) -> Iterator[State]:
        ctl, rules = create_possible_states_ctl(
            temporal_rules=self.temporal_rule_container,
            shapes=self.shape_container,
            record=record,
            ply=ply,
            is_final_view=is_final,
            parallel_mode=self.parallel_mode,
        )
        offset = record.offset
        horizon = record.horizon
        models = get_possible_states_models(ctl, offset=offset, horizon=horizon)
        possible_states = (transform_possible_states_model(symbols=symbols) for symbols in models)
        return possible_states

    @staticmethod
    def get_logger(context: str) -> Callable[[clingo.MessageCode, str], None]:
        return functools.partial(ControlContainer.log, context=context)


@dataclass
class ClingoInterpreter(ClingoRegroundingInterpreter):
    """An interpreter for a GDL ruleset using clingo."""

    control_container: ControlContainer = field(default_factory=ControlContainer, repr=False)

    @classmethod
    def from_ruleset(
        cls,
        ruleset: gdl.Ruleset,
        *args: Any,
        parallel_mode: Optional[ParallelMode] = None,
        disable_cache: bool = False,
        **kwargs: Any,
    ) -> Self:
        control_container = ControlContainer.from_ruleset(ruleset)
        shape_container = ShapeContainer.from_control_container(control_container)
        temporal_rule_container = TemporalRuleContainer.from_ruleset(ruleset)
        if parallel_mode is None:
            cpu_count = multiprocessing.cpu_count()
            parallel_mode = (max(2, min(64, cpu_count)), "compete")
        return cls(
            ruleset=ruleset,
            parallel_mode=parallel_mode,
            control_container=control_container,
            shape_container=shape_container,
            temporal_rule_container=temporal_rule_container,
            disable_cache=disable_cache,
        )

    def __rich__(self) -> str:
        state_shape = self.shape_container.state_shape
        state_shape_size_str = f"#P(state)={len(state_shape)}"
        action_shape = self.shape_container.action_shape
        all_moves = {move for moves in action_shape.values() for move in moves}
        action_shape_size = len(all_moves)
        action_shape_size_str = f"#P(action)={action_shape_size}"
        information_str = f"\[{state_shape_size_str}, {action_shape_size_str}]"  # noqa: W605
        ruleset_str = f"ruleset={rich(self.ruleset)}"
        parallel_mode_str = f"parallel_mode={rich(self.parallel_mode)}"
        attributes_str = f"{ruleset_str}, {parallel_mode_str}"

        return f"{self.__class__.__name__}{information_str}({attributes_str})"

    def _get_roles(self) -> FrozenSet[Role]:
        model = _get_model(self.control_container.role)
        subrelations = _transform_model(model, unpack=0)
        roles = (Role(subrelation) for subrelation in subrelations)
        try:
            return frozenset(roles)
        except UnsatInterpreterError:
            raise UnsatRolesInterpreterError from UnsatInterpreterError

    def _get_init_state(self) -> State:
        model = _get_model(self.control_container.init)
        subrelations = _transform_model(model, unpack=0)
        try:
            return State(frozenset(subrelations))
        except UnsatInterpreterError:
            raise UnsatInitInterpreterError from UnsatInterpreterError

    def _get_next_state(self, current: Union[State, View], turn: Mapping[Role, Move]) -> State:
        with _set_state(
            self.control_container.next,
            self.control_container.next_state_to_literal,
            current,
        ) as _ctl, _set_turn(_ctl, self.control_container.next_action_to_literal, turn) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model, unpack=0)
            try:
                return State(frozenset(subrelations))
            except UnsatInterpreterError:
                raise UnsatNextInterpreterError from UnsatInterpreterError

    def _get_sees(self, current: Union[State, View]) -> Mapping[Role, View]:
        if not self.has_incomplete_information:
            return {role: View(current) for role in self.get_roles()}
        with _set_state(self.control_container.sees, self.control_container.sees_state_to_literal, current) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model)
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

    def _get_legal_moves(self, current: Union[State, View]) -> Mapping[Role, FrozenSet[Move]]:
        with _set_state(self.control_container.legal, self.control_container.legal_state_to_literal, current) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model)
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

    def _get_goals(self, current: Union[State, View]) -> Mapping[Role, Optional[int]]:
        with _set_state(self.control_container.goal, self.control_container.goal_state_to_literal, current) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model)
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

    def _is_terminal(self, current: Union[State, View]) -> bool:
        with _set_state(
            self.control_container.terminal,
            self.control_container.terminal_state_to_literal,
            current,
        ) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model)
            try:
                return bool(tuple(subrelations))
            except UnsatInterpreterError:
                raise UnsatTerminalInterpreterError from UnsatInterpreterError
