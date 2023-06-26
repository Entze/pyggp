"""Interpreters for GDL rulesets."""
import collections
import itertools
import logging
import multiprocessing
from dataclasses import dataclass, field
from typing import (
    Any,
    FrozenSet,
    Iterator,
    Mapping,
    MutableMapping,
    MutableSequence,
    Optional,
    Set,
    Tuple,
    Union,
)

import cachetools
import cachetools.keys as cachetools_keys
from typing_extensions import Self

import pyggp.game_description_language as gdl
from pyggp._caching import (
    get_roles_in_control_sizeof,
)
from pyggp._clingo_interpreter.base import _get_model, _transform_model
from pyggp._clingo_interpreter.cache import CacheContainer
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

log: logging.Logger = logging.getLogger("pyggp")

_get_roles_in_control_cache: cachetools.Cache[State, FrozenSet[Role]] = cachetools.LRUCache(
    maxsize=50_000_000,
    getsizeof=get_roles_in_control_sizeof,
)


@dataclass
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

    def get_possible_states(self, record: Record, ply: int) -> Iterator[State]:
        """Yield all possible states for the given record at the given ply.

        Args:
            record: Record of the game
            ply: Ply

        Yields:
            All possible states at the given ply

        """
        offset = record.offset
        horizon = record.horizon
        if not offset <= ply <= horizon:
            raise PlyOutsideOfBoundsError
        developments = self.get_developments(record)
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


@dataclass
class ClingoInterpreter(Interpreter):
    """An interpreter for a GDL ruleset using clingo."""

    parallel_mode: ParallelMode = field(default=1)
    _control_container: ControlContainer = field(default_factory=ControlContainer, repr=False)
    _shape_container: ShapeContainer = field(default_factory=ShapeContainer, repr=False)
    _temporal_rule_container: TemporalRuleContainer = field(default_factory=TemporalRuleContainer, repr=False)
    _cache_container: CacheContainer = field(default_factory=CacheContainer, repr=False)

    @classmethod
    def from_ruleset(
        cls,
        ruleset: gdl.Ruleset,
        *args: Any,
        parallel_mode: Optional[ParallelMode] = None,
        **kwargs: Any,
    ) -> Self:
        control_container = ControlContainer.from_ruleset(ruleset)
        shape_container = ShapeContainer.from_control_container(control_container)
        temporal_rule_container = TemporalRuleContainer.from_ruleset(ruleset)
        cache_container = CacheContainer()
        if parallel_mode is None:
            cpu_count = multiprocessing.cpu_count()
            parallel_mode = (max(2, min(64, cpu_count)), "compete")
        return cls(
            ruleset=ruleset,
            parallel_mode=parallel_mode,
            _control_container=control_container,
            _shape_container=shape_container,
            _temporal_rule_container=temporal_rule_container,
            _cache_container=cache_container,
        )

    def get_roles(self) -> FrozenSet[Role]:
        if self._cache_container.roles is None:
            self._cache_container.roles = self._get_roles()
        assert self._cache_container.roles is not None, "Guarantee: self._cache_container.roles is not None"
        return self._cache_container.roles

    def _get_roles(self) -> FrozenSet[Role]:
        model = _get_model(self._control_container.role)
        subrelations = _transform_model(model, unpack=0)
        roles = (Role(subrelation) for subrelation in subrelations)
        try:
            return frozenset(roles)
        except UnsatInterpreterError:
            raise UnsatRolesInterpreterError from UnsatInterpreterError

    def get_init_state(self) -> State:
        if self._cache_container.init is None:
            self._cache_container.init = self._get_init_state()
        assert self._cache_container.init is not None, "Guarantee: self._cache_container.init is not None"
        return self._cache_container.init

    def _get_init_state(self) -> State:
        model = _get_model(self._control_container.init)
        subrelations = _transform_model(model, unpack=0)
        try:
            return State(frozenset(subrelations))
        except UnsatInterpreterError:
            raise UnsatInitInterpreterError from UnsatInterpreterError

    def get_next_state(self, current: Union[State, View], turn: Mapping[Role, Move]) -> State:
        current_len = len(current)
        if not isinstance(turn, Turn):
            turn = Turn(turn)
        if (
            current_len not in self._cache_container.next
            or current not in self._cache_container.next[current_len]
            or turn not in self._cache_container.next[current_len][current]
        ):
            next_state = self._get_next_state(current, turn)
            self._cache_container.next[current_len][current][turn] = next_state
        assert current_len in self._cache_container.next, "Guarantee: current_len in self._cache_container.next"
        assert (
            current in self._cache_container.next[current_len]
        ), "Guarantee: current in self._cache_container.next[current_len]"
        assert (
            turn in self._cache_container.next[current_len][current]
        ), "Guarantee: turn in self._cache_container.next[current_len][current]"
        return self._cache_container.next[current_len][current][turn]

    def _get_next_state(self, current: Union[State, View], turn: Mapping[Role, Move]) -> State:
        with _set_state(
            self._control_container.next,
            self._control_container.next_state_to_literal,
            current,
        ) as _ctl, _set_turn(_ctl, self._control_container.next_action_to_literal, turn) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model, unpack=0)
            try:
                return State(frozenset(subrelations))
            except UnsatInterpreterError:
                raise UnsatNextInterpreterError from UnsatInterpreterError

    def get_all_next_states(self, current: Union[State, View]) -> Iterator[Tuple[Turn, State]]:
        current_len = len(current)
        if (
            current_len not in self._cache_container.all_next
            or current not in self._cache_container.all_next[current_len]
        ):
            all_next_states_iterator = self._get_all_next_states(current)
            for turn, next_state in all_next_states_iterator:
                yield turn, next_state
                self._cache_container.all_next[current_len][current].add((turn, next_state))
        else:
            assert (
                current_len in self._cache_container.all_next
            ), "Guarantee: current_len in self._cache_container.all_next"
            assert (
                current in self._cache_container.all_next[current_len]
            ), "Guarantee: current in self._cache_container.all_next[current_len]"
            yield from self._cache_container.all_next[current_len][current]

    def _get_all_next_states(self, current: Union[State, View]) -> Iterator[Tuple[Turn, State]]:
        return super().get_all_next_states(current)

    def get_sees(self, current: Union[State, View]) -> Mapping[Role, View]:
        current_len = len(current)
        if current_len not in self._cache_container.sees or current not in self._cache_container.sees[current_len]:
            sees = self._get_sees(current)
            self._cache_container.sees[current_len][current] = sees
        assert current_len in self._cache_container.sees, "Guarantee: current_len in self._cache_container.sees"
        assert current in self._cache_container.sees[current_len], "Guarantee: current in self._cache_container.sees"
        return self._cache_container.sees[current_len][current]

    def _get_sees(self, current: Union[State, View]) -> Mapping[Role, View]:
        if not self.has_incomplete_information:
            return {role: View(current) for role in self.get_roles()}
        with _set_state(self._control_container.sees, self._control_container.sees_state_to_literal, current) as ctl:
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

    def get_legal_moves(self, current: Union[State, View]) -> Mapping[Role, FrozenSet[Move]]:
        current_len = len(current)
        if current_len not in self._cache_container.legal or current not in self._cache_container.legal[current_len]:
            legal_moves = self._get_legal_moves(current)
            self._cache_container.legal[current_len][current] = legal_moves
        assert current_len in self._cache_container.legal, "Guarantee: current_len in self._cache_container.legal"
        assert current in self._cache_container.legal[current_len], "Guarantee: current in self._cache_container.legal"
        return self._cache_container.legal[current_len][current]

    def _get_legal_moves(self, current: Union[State, View]) -> Mapping[Role, FrozenSet[Move]]:
        with _set_state(self._control_container.legal, self._control_container.legal_state_to_literal, current) as ctl:
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

    def get_goals(self, current: Union[State, View]) -> Mapping[Role, Optional[int]]:
        current_len = len(current)
        if current_len not in self._cache_container.goal or current not in self._cache_container.goal[current_len]:
            goals = self._get_goals(current)
            self._cache_container.goal[current_len][current] = goals
        assert current_len in self._cache_container.goal, "Guarantee: current_len in self._cache_container.goal"
        assert current in self._cache_container.goal[current_len], "Guarantee: current in self._cache_container.goal"
        return self._cache_container.goal[current_len][current]

    def _get_goals(self, current: Union[State, View]) -> Mapping[Role, Optional[int]]:
        with _set_state(self._control_container.goal, self._control_container.goal_state_to_literal, current) as ctl:
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

    def is_terminal(self, current: Union[State, View]) -> bool:
        current_len = len(current)
        if (
            current_len not in self._cache_container.terminal
            or current not in self._cache_container.terminal[current_len]
        ):
            self._cache_container.terminal[current_len][current] = self._is_terminal(current)
        assert current_len in self._cache_container.terminal, "Guarantee: current_len in self._cache_container.terminal"
        assert (
            current in self._cache_container.terminal[current_len]
        ), "Guarantee: current in self._cache_container.terminal"
        return self._cache_container.terminal[current_len][current]

    def _is_terminal(self, current: Union[State, View]) -> bool:
        with _set_state(
            self._control_container.terminal,
            self._control_container.terminal_state_to_literal,
            current,
        ) as ctl:
            model = _get_model(ctl)
            subrelations = _transform_model(model)
            try:
                return bool(tuple(subrelations))
            except UnsatInterpreterError:
                raise UnsatTerminalInterpreterError from UnsatInterpreterError

    def get_developments(self, record: Record) -> Iterator[Development]:
        ctl, rules = _create_developments_ctl(
            temporal_rules=self._temporal_rule_container,
            shapes=self._shape_container,
            record=record,
        )
        offset = record.offset
        horizon = record.horizon
        models = _get_developments_models(ctl, offset=offset, horizon=horizon)
        developments = (
            transform_developments_model(symbols=symbols, offset=offset, horizon=horizon) for symbols in models
        )
        return developments

    def get_possible_states(self, record: Record, ply: int) -> Iterator[State]:
        ctl, rules = create_possible_states_ctl(
            temporal_rules=self._temporal_rule_container,
            shapes=self._shape_container,
            record=record,
            ply=ply,
            parallel_mode=self.parallel_mode,
        )
        offset = record.offset
        horizon = record.horizon
        # propagator = StateEnumerationPropagator(ply=ply, offset=offset)
        # ctl.register_propagator(propagator)
        models = get_possible_states_models(ctl, offset=offset, horizon=horizon)
        possible_states = (transform_possible_states_model(symbols=symbols) for symbols in models)
        return possible_states
