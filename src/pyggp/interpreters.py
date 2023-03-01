"""Interpreters for GDL rulesets."""
from dataclasses import dataclass
from typing import FrozenSet, Mapping, Sequence, MutableMapping, Set

import clingo.ast
from clingo import Control
from clingo.ast import ProgramBuilder
from clingox.backend import SymbolicBackend

from pyggp.exceptions import (
    MoreThanOneModelError,
    UnexpectedRoleError,
    MultipleGoalsError,
    UnsatRolesError,
    UnsatInitError,
    UnsatNextError,
    UnsatSeesError,
    UnsatLegalError,
    UnsatGoalError,
    GoalNotIntegerError,
)
from pyggp.gdl import Ruleset, State, Role, Move, Play, Relation, from_clingo_symbol, Subrelation


def get_roles_in_control(state: State) -> FrozenSet[Role]:
    """Return the roles in control in the given state.

    Args:
        state: The state to check.

    Returns:
        The roles in control in the given state.

    Examples:
        >>> state = frozenset()
        >>> get_roles_in_control(state)
        frozenset()
        >>> from pyggp.gdl import Relation
        >>> r = Relation("r")
        >>> state = frozenset({Relation.control(r)})
        >>> get_roles_in_control(state)
        frozenset({Relation(name='r', arguments=())})

    """
    return frozenset(
        (fluent.arguments[0] for fluent in state if isinstance(fluent, Relation) and fluent.match("control", 1))
    )


class Interpreter:
    """An interpreter for a GDL ruleset.

    Used to calculate the state transitions for games. The interpreter itself is stateless.

    Attributes:
        ruleset: The ruleset to interpret.

    """

    def __init__(self, ruleset: Ruleset) -> None:
        """Initialize the interpreter.

        Args:
            ruleset: The ruleset to interpret.

        """
        self.ruleset = ruleset

    def get_roles(self) -> FrozenSet[Role]:
        """Return the roles in the game.

        This is static information. The roles should never change during the game.

        Returns:
            The roles in the game.

        """
        raise NotImplementedError

    def get_init_state(self) -> State:
        """Return the initial state of the game.

        Returns:
            The initial state of the game.

        """
        raise NotImplementedError

    def get_next_state(self, state: State, *plays: Play) -> State:
        """Return the next state of the game.

        Args:
            state: The state of the game.
            plays: The plays of the roles in control.

        Returns:
            The next state of the game.

        """
        raise NotImplementedError

    def get_sees(self, state: State) -> Mapping[Role, State]:
        """Return each role's view of the state.

        Calculates the sees relation for the given state.

        Args:
            state: The state of the game.

        Returns:
            Each role's view of the state.

        See Also:
            :meth:`get_sees_by_role`

        """
        raise NotImplementedError

    def get_sees_by_role(self, state: State, role: Role) -> State:
        """Return the given role's view of the state.

        Args:
            state: The state of the game.
            role: The role.

        Returns:
            The given role's view of the state.

        See Also:
            :meth:`get_sees`

        """
        return self.get_sees(state).get(role, frozenset())

    def get_legal_moves(self, state: State) -> Mapping[Role, FrozenSet[Move]]:
        """Return the legal moves for each role.

        Calculates the legal relation for the given state.

        Args:
            state: The state of the game.

        Returns:
            The legal moves for each role.

        See Also:
            :meth:`is_legal`

        """
        raise NotImplementedError

    def is_legal(self, state: State, role: Role, move: Move) -> bool:
        """Check if the given move is legal for the given role.

        Args:
            state: The state of the game.
            role: The role.
            move: The move.

        Returns:
            True if the given move is legal for the given role, False otherwise.

        See Also:
            :meth:`get_legal_moves`

        """
        return move in self.get_legal_moves(state).get(role, frozenset())

    def get_goals(self, state: State) -> Mapping[Role, int | None]:
        """Return the goals for each role.

        Calculates the goal relation for the given state.

        Args:
            state: The state of the game.

        Returns:
            The goals for each role.

        See Also:
            :meth:`get_goal_by_role`

        """
        raise NotImplementedError

    def get_goal_by_role(self, state: State, role: Role) -> int | None:
        """Return the goal (utility value) for the given role.

        Args:
            state: The state of the game.
            role: The role.

        Returns:
            The goal for the given role.

        See Also:
            :meth:`get_goals`

        """
        return self.get_goals(state).get(role, None)

    def is_terminal(self, state: State) -> bool:
        """Check if the given state is terminal.

        Args:
            state: The state of the game.

        Returns:
            True if the given state is terminal, False otherwise.

        """
        raise NotImplementedError


def _get_ctl(state: State | None = None, plays: Sequence[Play] = (), rules: Sequence[clingo.ast.AST] = ()) -> Control:
    ctl = Control()
    ctl.configuration.solve.models = 2  # type: ignore

    if state is not None and state:
        with SymbolicBackend(ctl.backend()) as backend:
            for relation in state:
                head = Relation.true(relation).to_clingo_symbol()
                backend.add_rule(head=(head,))

    if plays:
        with SymbolicBackend(ctl.backend()) as backend:
            for play in plays:
                head = play.to_clingo_symbol()
                backend.add_rule(head=(head,))

    if rules:
        with ProgramBuilder(ctl) as builder:
            for rule in rules:
                builder.add(rule)

    return ctl


@dataclass
class _Rules:
    roles_rules: Sequence[clingo.ast.AST]
    init_rules: Sequence[clingo.ast.AST]
    next_rules: Sequence[clingo.ast.AST]
    sees_rules: Sequence[clingo.ast.AST]
    legal_rules: Sequence[clingo.ast.AST]
    goal_rules: Sequence[clingo.ast.AST]
    terminal_rules: Sequence[clingo.ast.AST]


class ClingoInterpreter(Interpreter):
    """An interpreter for a GDL ruleset using clingo.

    Queries the clingo solver for the state transitions. Translates the GDL ruleset to ASP.

    Attributes:
        ruleset: The ruleset to interpret.

    See Also:
        :class:`pyggp.interpreters.Interpreter`

    """

    # region Magic Methods

    def __init__(
        self, ruleset: Ruleset, model_timeout: float | None = 10.0, prove_only_model_timeout: float | None = 2.0
    ) -> None:
        """Initialize the interpreter.

        Convert the sentences to clingo ASTs.

        Args:
            ruleset: The ruleset to interpret.
            model_timeout: The timeout in seconds for each model query.
            prove_only_model_timeout: The timeout in seconds for proving that there is only one model.

        """
        super().__init__(ruleset)
        roles_rules = tuple(sentence.to_clingo_ast() for sentence in ruleset.role_rules)
        init_rules = tuple(sentence.to_clingo_ast() for sentence in ruleset.init_rules)
        next_rules = tuple(sentence.to_clingo_ast() for sentence in ruleset.next_rules)
        sees_rules = tuple(sentence.to_clingo_ast() for sentence in ruleset.sees_rules)
        legal_rules = tuple(sentence.to_clingo_ast() for sentence in ruleset.legal_rules)
        goal_rules = tuple(sentence.to_clingo_ast() for sentence in ruleset.goal_rules)
        terminal_rules = tuple(sentence.to_clingo_ast() for sentence in ruleset.terminal_rules)
        self._rules = _Rules(roles_rules, init_rules, next_rules, sees_rules, legal_rules, goal_rules, terminal_rules)
        self._model_timeout = model_timeout
        self._prove_only_model_timeout = prove_only_model_timeout

    # endregion

    # region Methods

    def get_roles(self) -> FrozenSet[Role]:
        ctl = _get_ctl(rules=self._rules.roles_rules)
        model = self._get_model(ctl)
        if model is None:
            raise UnsatRolesError
        return frozenset(from_clingo_symbol(symbol.arguments[0]) for symbol in model if symbol.match("role", 1))

    def get_init_state(self) -> State:
        ctl = _get_ctl(rules=self._rules.init_rules)
        model = self._get_model(ctl)
        if model is None:
            raise UnsatInitError
        return frozenset(from_clingo_symbol(symbol.arguments[0]) for symbol in model if symbol.match("init", 1))

    def get_next_state(self, state: State, *plays: Play) -> State:
        ctl = _get_ctl(state=state, plays=plays, rules=self._rules.next_rules)
        model = self._get_model(ctl)
        if model is None:
            raise UnsatNextError
        return frozenset(from_clingo_symbol(symbol.arguments[0]) for symbol in model if symbol.match("next", 1))

    def get_sees(self, state: State) -> Mapping[Role, State]:
        if not self._rules.sees_rules:
            return {role: state for role in self.get_roles()}
        ctl = _get_ctl(state=state, rules=self._rules.sees_rules)
        model = self._get_model(ctl)
        if model is None:
            raise UnsatSeesError
        views: MutableMapping[Role, Set[Subrelation] | None] = self._get_role_mapping(model, "sees", 2)
        if Relation.random() in self.get_roles():
            views[Relation.random()] = set(state)
        return {role: frozenset(view) if view is not None else frozenset() for role, view in views.items()}

    def get_legal_moves(self, state: State) -> Mapping[Role, FrozenSet[Move]]:
        ctl = _get_ctl(state=state, rules=self._rules.legal_rules)
        model = self._get_model(ctl)
        if model is None:
            raise UnsatLegalError
        role_moves_mapping = self._get_role_mapping(model, "legal", 2)
        return {
            role: frozenset(moves) if moves is not None else frozenset() for role, moves in role_moves_mapping.items()
        }

    def get_goals(self, state: State) -> Mapping[Role, int | None]:
        ctl = _get_ctl(state=state, rules=self._rules.goal_rules)
        model = self._get_model(ctl)
        if model is None:
            raise UnsatGoalError
        role_goalset_mapping = self._get_role_mapping(model, "goal", 2)
        goals: MutableMapping[Role, int | None] = {}
        for role, goalset in role_goalset_mapping.items():
            if goalset is None:
                goals[role] = None
            elif len(goalset) != 1:
                raise MultipleGoalsError
            else:
                goal = next(iter(goalset))
                if not isinstance(goal, int):
                    raise GoalNotIntegerError
                goals[role] = goal
        return goals

    def is_terminal(self, state: State) -> bool:
        ctl = _get_ctl(state=state, rules=self._rules.terminal_rules)
        with SymbolicBackend(ctl.backend()) as backend:
            backend.add_rule(pos_body=(Relation.terminal().to_clingo_symbol(),))
        model = self._get_model(ctl)
        return model is None

    def _get_model(self, ctl: Control) -> Sequence[clingo.Symbol] | None:
        ctl.ground((("base", ()),))
        solve_handle = ctl.solve(yield_=True, async_=True)
        assert isinstance(solve_handle, clingo.SolveHandle)
        with solve_handle as handle:
            handle.resume()
            ready = handle.wait(self._model_timeout)
            if not ready:
                raise TimeoutError("Timeout while waiting for model.")  # pragma: no cover
            model = handle.model()
            if model is None:
                return None
            symbols: Sequence[clingo.Symbol] = model.symbols(shown=True)
            handle.resume()
            ready = handle.wait(self._prove_only_model_timeout)
            if not ready:
                raise TimeoutError("Timeout while proving that there is only one model.")  # pragma: no cover
            _m = handle.model()
            if _m is not None:
                raise MoreThanOneModelError
            return symbols

    def _get_role_mapping(
        self, model: Sequence[clingo.Symbol] = (), name: str = "", arity: int = 0
    ) -> MutableMapping[Role, Set[Subrelation] | None]:
        mapping: MutableMapping[Role, Set[Subrelation] | None] = {role: None for role in self.get_roles()}
        unexpected_roles = set()
        for symbol in model:
            if symbol.match(name, arity):
                role = from_clingo_symbol(symbol.arguments[0])
                if role not in mapping:
                    unexpected_roles.add(role)
                else:
                    target = mapping[role]
                    if target is None:
                        target = set()
                    assert isinstance(target, set)
                    target.add(from_clingo_symbol(symbol.arguments[1]))
                    mapping[role] = target
        if unexpected_roles:
            raise UnexpectedRoleError
        return mapping


# endregion
