"""Interpreters for GDL rulesets."""
import collections
import time
from dataclasses import dataclass, field
from typing import (
    FrozenSet,
    Iterator,
    Mapping,
    MutableMapping,
    NamedTuple,
    NewType,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import clingo
import clingo.ast as clingo_ast
import clingox.backend as clingox_backend
from typing_extensions import Self

import pyggp.game_description_language as gdl
from pyggp.exceptions.interpreter_exceptions import (
    ModelTimeoutInterpreterError,
    MoreThanOneModelInterpreterError,
    MultipleGoalsInterpreterError,
    SolveTimeoutInterpreterError,
    UnsatGoalInterpreterError,
    UnsatInitInterpreterError,
    UnsatLegalInterpreterError,
    UnsatNextInterpreterError,
    UnsatRolesInterpreterError,
    UnsatSeesInterpreterError,
)

_State = FrozenSet[gdl.Subrelation]
State = NewType("State", _State)
"""States are sets of subrelations."""
View = NewType("View", State)
"""Views are (partial) states."""

Role = NewType("Role", gdl.Subrelation)
"""Roles are relations, numbers, or string."""

Play = NewType("Play", gdl.Relation)
"""Plays are does/2 relations.

Plays are of the form does(Subrelation(Role), Subrelation(Move)).

"""

Move = NewType("Move", gdl.Subrelation)
"""Moves are relations, numbers, or strings."""


@dataclass(frozen=True)
class Turn(Mapping[Role, Move]):
    """Mapping of roles to a move.

    Resembles a collection of plays.

    """

    _role_move_pairs: FrozenSet[Tuple[Role, Move]] = field(default_factory=frozenset)

    @classmethod
    def from_mapping(cls, mapping: Mapping[Role, Move]) -> Self:
        """Create a turn from a mapping of roles to moves.

        Args:
            mapping: Mapping of roles to moves

        Returns:
            Turn

        """
        # Disables PyCharm's type checker. Because seems to be a bug.
        # noinspection PyTypeChecker
        return cls(frozenset(mapping.items()))

    def __getitem__(self, role: Role) -> Move:
        """Get the move for the given role.

        Args:
            role: Role

        Returns:
            Move

        Raises:
            KeyError: Role does not have a move

        """
        for role_, move in self._role_move_pairs:
            if role_ == role:
                return move
        raise KeyError(role)

    def __len__(self) -> int:
        """Return the number of roles that have moves.

        Returns:
            Number of roles that have moves

        """
        return len(self._role_move_pairs)

    def __iter__(self) -> Iterator[Role]:
        """Iterate over the roles that have moves.

        Yields:
            Roles that have moves

        """
        for role, _ in self._role_move_pairs:
            yield role


class Record(NamedTuple):
    """Record (possibly partial) of a game."""

    states: Mapping[int, State]
    """States of the game by ply."""
    views: Mapping[int, Mapping[Role, View]]
    """Views of the state by role by ply."""
    turns: Mapping[int, Turn]
    """Turns of the game by ply."""


class DevelopmentStep(NamedTuple):
    """A development."""

    state: State
    """State of that step."""
    turn: Optional[Turn]
    """Turn of that step, None if ambiguous."""


_Development = Sequence[DevelopmentStep]
Development = NewType("Development", _Development)


@dataclass
class Interpreter:
    """An interpreter for a GDL ruleset_resource.

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

    def get_next_state(self, current: Union[State, View], *plays: Play) -> State:
        """Return the next state of the game.

        Args:
            current: Current state or view
            plays: Plays of the roles in control

        Returns:
            The next state of the game

        """
        raise NotImplementedError

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


@dataclass
class ClingoInterpreter(Interpreter):
    """An interpreter for a GDL ruleset_resource using clingo.

    Queries the clingo solver for the state transitions. Translates the GDL ruleset_resource to ASP.

    """

    # region Inner Classes

    @dataclass(frozen=True)
    class _ClingoASTRules:
        roles_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        init_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        next_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        sees_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        legal_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        goal_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)
        terminal_rules: Sequence[clingo_ast.AST] = field(default_factory=tuple)

        static_rules: Sequence[clingo_ast.AST] = field(init=False)
        dynamic_rules: Sequence[clingo_ast.AST] = field(init=False)

        @classmethod
        def from_ruleset(cls, ruleset: gdl.Ruleset) -> Self:
            roles_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.role_rules)
            init_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.init_rules)
            next_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.next_rules)
            sees_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.sees_rules)
            legal_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.legal_rules)
            goal_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.goal_rules)
            terminal_rules = tuple(sentence.as_clingo_ast() for sentence in ruleset.terminal_rules)
            return cls(roles_rules, init_rules, next_rules, sees_rules, legal_rules, goal_rules, terminal_rules)

    # Disables N818 (Exception name should be named with an Error suffix). Because this is not an error, but an effect.
    class Unsat(Exception):  # noqa: N818
        """Raised when the query is unsatisfiable."""

    # endregion
    model_timeout: float = 8.0
    """Timeout for the model query in seconds."""
    solve_timeout: float = 10.0
    """Timeout for all model queries in seconds."""
    _rules: _ClingoASTRules = field(default_factory=_ClingoASTRules)

    def get_roles(self) -> FrozenSet[Role]:
        """Return the roles in the game.

        This is static information. Roles should never change during the game.

        Returns:
            Roles in the game

        Raises:
            UnsatRolesInterpreterError: The role sentences are unsatisfiable

        """
        ctl = ClingoInterpreter.get_ctl(rules=self._rules.roles_rules)
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
        ctl = ClingoInterpreter.get_ctl(rules=self._rules.init_rules)
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
        ctl = ClingoInterpreter.get_ctl(state=current, plays=plays, rules=self._rules.next_rules)
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
        ctl = ClingoInterpreter.get_ctl(state=current, rules=self._rules.sees_rules)
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
        ctl = ClingoInterpreter.get_ctl(state=current, rules=self._rules.legal_rules)
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
        ctl = ClingoInterpreter.get_ctl(state=current, rules=self._rules.goal_rules)
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
        return {role: goals_mutable[role] for role in self.get_roles()}

    def is_terminal(self, current: Union[State, View]) -> bool:
        """Check if the given state is terminal.

        Args:
            current: Current state or view of the game

        Returns:
            True if the given state is terminal, False otherwise

        """
        ctl = ClingoInterpreter.get_ctl(state=current, rules=self._rules.terminal_rules)
        with clingox_backend.SymbolicBackend(ctl.backend()) as backend:
            backend.add_rule(neg_body=(clingo.Function("terminal", []),))
        try:
            self._get_model(ctl)
        except ClingoInterpreter.Unsat:
            return False
        return True

    def get_developments(self, record: Record) -> Iterator[Development]:
        """Return all possible developments for the given record.

        Args:
            record: Record of the game

        Returns:
            All possible developments for the given record

        """

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

    @staticmethod
    def get_ctl(
        state: Union[State, View, None] = None,
        plays: Sequence[Play] = (),
        rules: Sequence[clingo_ast.AST] = (),
    ) -> clingo.Control:
        """Return a clingo control object with the given state, plays and rules.

        The control object assumes that there is only one model.

        Args:
            state: State or view to be added to the control object
            plays: Plays to be added to the control object
            rules: Rules to be added to the control object

        Returns:
            A clingo control object with the given state, plays and rules

        """
        ctl = clingo.Control()
        # Disables mypy. Because clingo does not define types for configuration options.
        ctl.configuration.solve.models = 2  # type: ignore[union-attr]
        if state is not None and state:
            with clingox_backend.SymbolicBackend(ctl.backend()) as backend:
                for subrelation in state:
                    head = clingo.Function("true", arguments=(subrelation.as_clingo_symbol(),))
                    backend.add_rule(head=(head,))

        if plays:
            with clingox_backend.SymbolicBackend(ctl.backend()) as backend:
                for play in plays:
                    head = play.as_clingo_symbol()
                    backend.add_rule(head=(head,))

        if rules:
            with clingo_ast.ProgramBuilder(ctl) as builder:
                for rule in rules:
                    builder.add(rule)

        return ctl


#
#

#
#
# class _ToRenameDict(TypedDict):
#     name: str
#     head_shift: Optional[int]
#     body_shift: Optional[int]
#     append_arguments: Sequence[clingo.ast.AST]
#
#
# @dataclass
# class _EventCalculus:
#     static: Sequence[clingo.ast.AST]
#     dynamic: Sequence[clingo.ast.AST]
#
#     @classmethod
#     def from_ruleset(cls, ruleset: Ruleset) -> Self:
#         static = [clingo.ast.Program(pyggp.gdl._loc, "static", ())]
#         dynamic = [clingo.ast.Program(pyggp.gdl._loc, "dynamic", (clingo.ast.Id(pyggp.gdl._loc, "__time"),))]
#         dynamic_to_rename: MutableMapping[Signature, _ToRenameDict] = {
#             Signature("next", 1): _ToRenameDict(head_shift=0, body_shift=1, name="holds_at", append_arguments=()),
#             Signature("true", 1): _ToRenameDict(head_shift=0, body_shift=0, name="holds_at", append_arguments=()),
#             Signature("sees", 2): _ToRenameDict(head_shift=0, body_shift=0, name="sees_at", append_arguments=()),
#             Signature("legal", 2): _ToRenameDict(head_shift=0, body_shift=0, name="legal_at", append_arguments=()),
#             Signature("does", 2): _ToRenameDict(head_shift=0, body_shift=0, name="does_at", append_arguments=()),
#         }
#         static_to_rename: MutableMapping[Signature, _ToRenameDict] = {
#             Signature("init", 1): _ToRenameDict(
#                 head_shift=None,
#                 body_shift=None,
#                 name="holds_at",
#                 append_arguments=(clingo.ast.SymbolicTerm(pyggp.gdl._loc, clingo.Number(0)),),
#             ),
#         }
#         to_rename_size = len(dynamic_to_rename)
#         changed = True
#         while changed:
#             for sentence in ruleset.rules:
#                 if any(signature in sentence for signature in dynamic_to_rename):
#                     signature = sentence.head.signature
#                     name, arity = signature
#                     dynamic_to_rename.setdefault(
#                         signature,
#                         _ToRenameDict(head_shift=0, body_shift=0, name=f"{name}_at", append_arguments=()),
#                     )
#             changed = len(dynamic_to_rename) != to_rename_size
#             to_rename_size = len(dynamic_to_rename)
#
#         assert set(dynamic_to_rename.keys()).isdisjoint(set(static_to_rename.keys())), (
#             "There exists Signatures that are both static and dynamic: "
#             f"{set(dynamic_to_rename.keys()) & set(static_to_rename.keys())}"
#         )
#
#         for sentence in ruleset.rules:
#             rule_ast = _EventCalculus.sentence_to_clingo_ast_with_time(sentence, dynamic_to_rename, static_to_rename)
#             assert not (sentence.head.signature in static_to_rename and sentence.head.signature in dynamic_to_rename)
#             if sentence.head.signature not in dynamic_to_rename:
#                 static.append(rule_ast)
#             else:
#                 dynamic.append(rule_ast)
#
#         return cls(static, dynamic)
#
#     @staticmethod
#     def relation_to_clingo_ast_with_time(
#         relation: Relation,
#         name: str,
#         shift: Optional[int],
#         append_arguments: Sequence[clingo.ast.AST],
#     ) -> clingo.ast.AST:
#         if shift is not None:
#             time_ = clingo.ast.Function(pyggp.gdl._loc, "__time", (), False)
#             if shift == 0:
#                 time_shift = (time_,)
#             else:
#                 if shift > 0:
#                     operator = clingo.ast.BinaryOperator.Minus
#                 else:
#                     assert shift < 0
#                     operator = clingo.ast.BinaryOperator.Plus
#
#                 time_shift = (
#                     clingo.ast.BinaryOperation(
#                         pyggp.gdl._loc,
#                         operator,
#                         time_,
#                         clingo.ast.SymbolicTerm(pyggp.gdl._loc, clingo.Number(abs(shift))),
#                     ),
#                 )
#         else:
#             time_shift = ()
#
#         arguments = (*relation.to_clingo_ast().arguments, *time_shift, *append_arguments)
#         return clingo.ast.SymbolicAtom(clingo.ast.Function(pyggp.gdl._loc, name, arguments, False))
#
#     @staticmethod
#     def literal_to_clingo_ast_with_time(
#         literal: Literal,
#         name: str,
#         shift: int,
#         append_arguments: Sequence[clingo.ast.AST],
#     ) -> clingo.ast.AST:
#         atom = _EventCalculus.relation_to_clingo_ast_with_time(literal.atom, name, shift, append_arguments)
#         if literal.sign == Sign.NOSIGN:
#             sign = clingo.ast.Sign.NoSign
#         elif literal.sign == Sign.NEGATIVE:
#             sign = clingo.ast.Sign.Negation
#         else:
#             assert_never(literal.sign)
#         return clingo.ast.Literal(pyggp.gdl._loc, sign, atom)
#
#     @staticmethod
#     def sentence_to_clingo_ast_with_time(
#         sentence: Sentence,
#         dynamic_to_rename: Optional[Mapping[Signature, _ToRenameDict]] = None,
#         static_to_rename: Optional[Mapping[Signature, _ToRenameDict]] = None,
#     ) -> clingo.ast.AST:
#         if dynamic_to_rename is None:
#             dynamic_to_rename = {}
#         if static_to_rename is None:
#             static_to_rename = {}
#         to_rename = dynamic_to_rename | static_to_rename
#         if sentence.head.signature in to_rename:
#             head_name = to_rename[sentence.head.signature]["name"]
#             head_shift = to_rename[sentence.head.signature]["head_shift"]
#             body_shift = to_rename[sentence.head.signature]["body_shift"]
#             append_head_arguments = to_rename[sentence.head.signature]["append_arguments"]
#             head_atom = _EventCalculus.relation_to_clingo_ast_with_time(
#                 sentence.head,
#                 head_name,
#                 head_shift,
#                 append_head_arguments,
#             )
#             head_literal = clingo.ast.Literal(pyggp.gdl._loc, clingo.ast.Sign.NoSign, head_atom)
#             body_literals = []
#             for literal in sentence.body:
#                 if literal.atom.signature in to_rename:
#                     body_name = to_rename[literal.atom.signature]["name"]
#                     append_body_arguments = to_rename[literal.atom.signature]["append_arguments"]
#                     body_literals.append(
#                         _EventCalculus.literal_to_clingo_ast_with_time(
#                             literal,
#                             body_name,
#                             body_shift,
#                             append_body_arguments,
#                         ),
#                     )
#                 else:
#                     body_literals.append(literal.to_clingo_ast())
#             rule_ast = clingo.ast.Rule(pyggp.gdl._loc, head_literal, body_literals)
#         else:
#             rule_ast = sentence.to_clingo_ast()
#         return rule_ast
#
#
# class ClingoInterpreter(Interpreter):
#     """An interpreter for a GDL ruleset_resource using clingo.
#
#     Queries the clingo solver for the state transitions. Translates the GDL ruleset_resource to ASP.
#
#     Attributes:
#         ruleset: The ruleset_resource to interpret.
#
#
#     """
#
#     # region Magic Methods
#
#     def __init__(
#         self,
#         ruleset: Optional[Ruleset] = None,
#         model_timeout: Optional[float] = 10.0,
#         prove_only_model_timeout: Optional[float] = 2.0,
#     ) -> None:
#         """Initialize the interpreter.
#
#         Convert the sentences to clingo ASTs.
#
#         Args:
#             ruleset: The ruleset_resource to interpret.
#             model_timeout: The timeout in seconds for each model query.
#             prove_only_model_timeout: The timeout in seconds for proving that there is only one model.
#
#         """
#         super().__init__(ruleset)
#         self._rules = _Rules.from_ruleset(ruleset)
#         self._event_calculus = _EventCalculus.from_ruleset(ruleset)
#
#         self._model_timeout = model_timeout
#         self._prove_only_model_timeout = prove_only_model_timeout
#
#     # endregion
#
#     # region Methods
#
#     def get_roles(self) -> FrozenSet[ConcreteRole]:
#         ctl = _get_ctl(rules=self._rules.roles_rules)
#         model = self._get_model(ctl)
#         if model is None:
#             raise UnsatRolesInterpreterError
#         return frozenset(from_clingo_symbol(symbol.arguments[0]) for symbol in model if symbol.match("role", 1))
#
#     def get_init_state(self) -> State:
#         ctl = _get_ctl(rules=self._rules.init_rules)
#         model = self._get_model(ctl)
#         if model is None:
#             raise UnsatInitInterpreterError
#         return frozenset(from_clingo_symbol(symbol.arguments[0]) for symbol in model if symbol.match("init", 1))
#
#     def get_next_state(self, state: State, *plays: Play) -> State:
#         ctl = _get_ctl(state=state, plays=plays, rules=self._rules.next_rules)
#         model = self._get_model(ctl)
#         if model is None:
#             raise UnsatNextInterpreterError
#         return frozenset(from_clingo_symbol(symbol.arguments[0]) for symbol in model if symbol.match("next", 1))
#
#     @property
#     def has_incomplete_information(self) -> bool:
#         return bool(self._rules.sees_rules)
#
#     def get_sees(self, state: State) -> Mapping[ConcreteRole, State]:
#         if not self.has_incomplete_information:
#             return {role: state for role in self.get_roles()}
#         ctl = _get_ctl(state=state, rules=self._rules.sees_rules)
#         model = self._get_model(ctl)
#         if model is None:
#             raise UnsatSeesInterpreterError
#         views: MutableMapping[ConcreteRole, Optional[Set[Subrelation]]] = self._get_role_mapping(model, "sees", 2)
#         if Relation.random() in self.get_roles():
#             views[Relation.random()] = set(state)
#         return {role: frozenset(view) if view is not None else frozenset() for role, view in views.items()}
#
#     def get_legal_moves(self, state: State) -> Mapping[ConcreteRole, FrozenSet[Move]]:
#         ctl = _get_ctl(state=state, rules=self._rules.legal_rules)
#         model = self._get_model(ctl)
#         if model is None:
#             raise UnsatLegalInterpreterError
#         role_moves_mapping = self._get_role_mapping(model, "legal", 2)
#         return {
#             role: frozenset(moves) if moves is not None else frozenset() for role, moves in role_moves_mapping.items()
#         }
#
#     def get_goals(self, state: State) -> Mapping[ConcreteRole, Optional[int]]:
#         ctl = _get_ctl(state=state, rules=self._rules.goal_rules)
#         model = self._get_model(ctl)
#         if model is None:
#             raise UnsatGoalInterpreterError
#         role_goalset_mapping = self._get_role_mapping(model, "goal", 2)
#         goals: MutableMapping[ConcreteRole, Optional[int]] = {}
#         for role, goalset in role_goalset_mapping.items():
#             if goalset is None:
#                 goals[role] = None
#             elif len(goalset) != 1:
#                 raise MultipleGoalsInterpreterError
#             else:
#                 goal = next(iter(goalset))
#                 if not isinstance(goal, int):
#                     raise GoalNotIntegerInterpreterError
#                 goals[role] = goal
#         return goals
#
#     def is_terminal(self, state: State) -> bool:
#         ctl = _get_ctl(state=state, rules=self._rules.terminal_rules)
#         with SymbolicBackend(ctl.backend()) as backend:
#             backend.add_rule(pos_body=(Relation.terminal().to_clingo_symbol(),))
#         model = self._get_model(ctl)
#         return model is None
#
#     def get_developments(
#         self,
#         state_record: Optional[StateRecord] = None,
#         sees_record: Optional[SeesRecord] = None,
#         move_record: Optional[ConcreteRoleMoveMappingRecord] = None,
#     ) -> Iterator[Development]:
#         if state_record is None:
#             state_record = {}
#         if sees_record is None:
#             sees_record = {}
#         if move_record is None:
#             move_record = {}
#         _max_state_ply = max(state_record.keys(), default=-1)
#         _max_sees_ply = max(sees_record.keys(), default=-1)
#         _max_move_ply = max(move_record.keys(), default=-1)
#         current_ply = max(_max_state_ply, _max_sees_ply, _max_move_ply)
#         prg = []
#         ctl = Control()
#         ctl.configuration.solve.models = 0
#         for ply in range(0, current_ply + 1):
#             with SymbolicBackend(ctl.backend()) as backend:
#                 if ply in state_record:
#                     state = state_record[ply]
#                     for relation in state:
#                         symbol = to_clingo_symbol(relation)
#                         func = clingo.Function("holds_at", (symbol, clingo.Number(ply)))
#                         backend.add_rule(neg_body=(func,))
#                         prg.append(f":- not {func}.")
#                 if ply in sees_record:
#                     role_view = sees_record[ply]
#                     for role, view in role_view.items():
#                         role_symbol = to_clingo_symbol(role)
#                         for relation in view:
#                             symbol = to_clingo_symbol(relation)
#                             func = clingo.Function("sees_at", (role_symbol, symbol, clingo.Number(ply)))
#                             backend.add_rule(neg_body=(func,))
#                             prg.append(f":- not {func}.")
#                 if ply in move_record:
#                     for role, move in move_record[ply].items():
#                         role_symbol = to_clingo_symbol(role)
#                         move_symbol = to_clingo_symbol(move)
#                         func = clingo.Function("does_at", (role_symbol, move_symbol, clingo.Number(ply)))
#                         backend.add_rule(neg_body=(func,))
#                         prg.append(f":- not {func}.")
#         with clingo.ast.ProgramBuilder(ctl) as builder:
#             _does_at_atom = _clingo.create_atom(
#                 _clingo.create_function(
#                     "does_at",
#                     (
#                         _clingo.create_variable("Role"),
#                         _clingo.create_variable("Move"),
#                         _clingo.create_variable("Ply"),
#                     ),
#                 ),
#             )
#             _legal_at_atom = _clingo.create_atom(
#                 _clingo.create_function(
#                     "legal_at",
#                     (
#                         _clingo.create_variable("Role"),
#                         _clingo.create_variable("Move"),
#                         _clingo.create_variable("Ply"),
#                     ),
#                 ),
#             )
#             _does_at_literal = _clingo.create_literal(atom=_does_at_atom)
#             _legal_at_literal = _clingo.create_literal(atom=_legal_at_atom)
#             _right_guard = _clingo.create_guard(
#                 comparison=clingo.ast.ComparisonOperator.Equal,
#                 term=_clingo.create_symbolic_term(clingo.Number(1)),
#             )
#             _condition = (_legal_at_literal,)
#             _conditional_literal = _clingo.create_conditional_literal(_does_at_literal, _condition)
#             _head_aggregate = _clingo.create_aggregate(elements=(_conditional_literal,), right_guard=_right_guard)
#             _head = _head_aggregate
#             _role_function = _clingo.create_function("role", (_clingo.create_variable("Role"),))
#             _role_atom = _clingo.create_atom(_role_function)
#             _role_literal = _clingo.create_literal(atom=_role_atom)
#             _holds_at_function = _clingo.create_function(
#                 "holds_at",
#                 (
#                     _clingo.create_function("control", (_clingo.create_variable("Role"),)),
#                     _clingo.create_variable("Ply"),
#                 ),
#             )
#             _holds_at_atom = _clingo.create_atom(_holds_at_function)
#             _holds_at_literal = _clingo.create_literal(atom=_holds_at_atom)
#             _comparison_atom = _clingo.create_comparison(
#                 term=_clingo.create_symbolic_term(clingo.Number(0)),
#                 guards=(
#                     _clingo.create_guard(clingo.ast.ComparisonOperator.LessEqual, _clingo.create_variable("Ply")),
#                     _clingo.create_guard(
#                         clingo.ast.ComparisonOperator.LessThan,
#                         _clingo.create_symbolic_term(clingo.Number(current_ply)),
#                     ),
#                 ),
#             )
#             _comparison_literal = _clingo.create_literal(atom=_comparison_atom)
#             _body = (_role_literal, _comparison_literal, _holds_at_literal)
#             _rule = _clingo.create_rule(head=_head, body=_body)
#
#             builder.add(_rule)
#             prg.append(str(_rule))
#             _does_at_signature = clingo.ast.ShowSignature(pyggp.gdl._loc, "does_at", 3, True)
#             builder.add(_does_at_signature)
#             prg.append(str(_does_at_signature))
#             _holds_at_signature = clingo.ast.ShowSignature(pyggp.gdl._loc, "holds_at", 2, True)
#             builder.add(_holds_at_signature)
#             prg.append(str(_holds_at_signature))
#             _sees_at_signature = clingo.ast.ShowSignature(pyggp.gdl._loc, "sees_at", 3, True)
#             builder.add(_sees_at_signature)
#             prg.append(str(_sees_at_signature))
#             for rule in self._event_calculus.static:
#                 builder.add(rule)
#                 prg.append(str(rule))
#             for rule in self._event_calculus.dynamic:
#                 builder.add(rule)
#                 prg.append(str(rule))
#         ctl.ground(
#             (("base", ()), ("static", ()), *(("dynamic", (clingo.Number(i),)) for i in range(0, current_ply + 1))),
#         )
#         log.debug("Program: \n\t%s\n" % "\n\t".join(prg))
#         solve_handle = ctl.solve(yield_=True, async_=True)
#         assert isinstance(solve_handle, clingo.SolveHandle)
#         with solve_handle as handle:
#             handle.resume()
#             while True:
#                 ready = handle.wait(self._model_timeout)
#                 if not ready:
#                     raise TimeoutError("Timeout while waiting for model.")
#                 model = handle.model()
#                 if model is None:
#                     break
#                 symbols: Sequence[clingo.Symbol] = model.symbols(shown=True)
#                 handle.resume()
#                 moves: MutableMapping[int, Optional[MutableConcreteRoleMoveMapping]] = {
#                     ply: {} for ply in range(0, current_ply)
#                 }
#                 moves[current_ply] = None
#                 states: MutableStateRecord = {ply: set() for ply in range(0, current_ply + 1)}
#                 views: MutableSeesRecord = {ply: collections.defaultdict(set) for ply in range(0, current_ply + 1)}
#                 for symbol in symbols:
#                     if symbol.match("does_at", 3):
#                         role = from_clingo_symbol(symbol.arguments[0])
#                         move = from_clingo_symbol(symbol.arguments[1])
#                         ply = int(symbol.arguments[2].number)
#                         assert 0 <= ply < current_ply
#                         moves[ply][role] = move
#                     elif symbol.match("holds_at", 2):
#                         relation = from_clingo_symbol(symbol.arguments[0])
#                         ply = int(symbol.arguments[1].number)
#                         assert 0 <= ply <= current_ply
#                         states[ply].add(relation)
#                     elif symbol.match("sees_at", 3):
#                         role = from_clingo_symbol(symbol.arguments[0])
#                         relation = from_clingo_symbol(symbol.arguments[1])
#                         ply = int(symbol.arguments[2].number)
#                         assert 0 <= ply <= current_ply
#                         views[ply][role].add(relation)
#
#                 immutable_states = {ply: frozenset(state) for ply, state in states.items()}
#                 immutable_views = (
#                     {
#                         ply: {role: frozenset(view) for role, view in role_view.items()}
#                         for ply, role_view in views.items()
#                     }
#                     if self.has_incomplete_information or any(role_view for role_view in views.values())
#                     else None
#                 )
#                 immutable_moves = moves
#                 development: Development = tuple(
#                     (
#                         immutable_states[ply],
#                         None if immutable_views is None else immutable_views[ply],
#                         immutable_moves[ply],
#                     )
#                     for ply in range(0, current_ply + 1)
#                 )
#                 yield development
#
#     def _get_model(self, ctl: Control) -> Optional[Sequence[clingo.Symbol]]:
#         ctl.ground((("base", ()),))
#         solve_handle = ctl.solve(yield_=True, async_=True)
#         assert isinstance(solve_handle, clingo.SolveHandle)
#         with solve_handle as handle:
#             handle.resume()
#             ready = handle.wait(self._model_timeout)
#             if not ready:
#                 raise TimeoutError("Timeout while waiting for model.")  # pragma: no cover
#             model = handle.model()
#             if model is None:
#                 return None
#             symbols: Sequence[clingo.Symbol] = model.symbols(shown=True)
#             handle.resume()
#             ready = handle.wait(self._prove_only_model_timeout)
#             if not ready:
#                 raise TimeoutError("Timeout while proving that there is only one model.")  # pragma: no cover
#             _m = handle.model()
#             if _m is not None:
#                 raise MoreThanOneModelInterpreterError
#             return symbols
#
#     def _get_role_mapping(
#         self,
#         model: Sequence[clingo.Symbol] = (),
#         name: str = "",
#         arity: int = 0,
#     ) -> MutableMapping[ConcreteRole, Optional[Set[Subrelation]]]:
#         mapping: MutableMapping[ConcreteRole, Optional[Set[Subrelation]]] = {role: None for role in self.get_roles()}
#         unexpected_roles = set()
#         for symbol in model:
#             if symbol.match(name, arity):
#                 role = from_clingo_symbol(symbol.arguments[0])
#                 if role not in mapping:
#                     unexpected_roles.add(role)
#                 else:
#                     target = mapping[role]
#                     if target is None:
#                         target = set()
#                     assert isinstance(target, set)
#                     target.add(from_clingo_symbol(symbol.arguments[1]))
#                     mapping[role] = target
#         if unexpected_roles:
#             raise UnexpectedRoleInterpreterError
#         return mapping
#
#     # endregion
#
