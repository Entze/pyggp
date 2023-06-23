import collections
from dataclasses import dataclass, field
from typing import DefaultDict, Set

import clingo
from typing_extensions import Self

import pyggp.game_description_language as gdl
from pyggp._clingo_interpreter.control_containers import ControlContainer
from pyggp.engine_primitives import ActionShape, GoalShape, Move, Role, SeesShape, StateShape
from pyggp.exceptions.interpreter_exceptions import GoalNotIntegerInterpreterError
from pyggp.mappings import FrozenDict


@dataclass(frozen=True)
class ShapeContainer:
    state_shape: StateShape = field(default_factory=frozenset)
    action_shape: ActionShape = field(default_factory=FrozenDict)
    sees_shape: SeesShape = field(default_factory=FrozenDict)
    goal_shape: GoalShape = field(default_factory=FrozenDict)

    @classmethod
    def from_control_container(cls, control_container: ControlContainer) -> Self:
        state_shape = ShapeContainer.get_state_shape(control_container.next)
        action_shape = ShapeContainer.get_action_shape(control_container.next)
        sees_shape = ShapeContainer.get_sees_shape(control_container.sees)
        goal_shape = ShapeContainer.get_goal_shape(control_container.goal)
        return cls(state_shape=state_shape, action_shape=action_shape, sees_shape=sees_shape, goal_shape=goal_shape)

    @staticmethod
    def get_state_shape(next_ctl: clingo.Control) -> StateShape:
        true_symbolic_atoms = next_ctl.symbolic_atoms.by_signature(name="true", arity=1)
        subrelations = (
            gdl.Subrelation.from_clingo_symbol(symbolic_atom.symbol) for symbolic_atom in true_symbolic_atoms
        )
        unpacked = (subrelation.symbol.arguments[0] for subrelation in subrelations)
        return frozenset(unpacked)

    @staticmethod
    def get_action_shape(next_ctl: clingo.Control) -> ActionShape:
        does_symbolic_atoms = next_ctl.symbolic_atoms.by_signature(name="does", arity=2)
        subrelations = (
            gdl.Subrelation.from_clingo_symbol(symbolic_atom.symbol) for symbolic_atom in does_symbolic_atoms
        )
        unpacked_arguments = (subrelation.symbol.arguments for subrelation in subrelations)
        unpacked = ((Role(arguments[0]), Move(arguments[1])) for arguments in unpacked_arguments)
        grouped: DefaultDict[Role, Set[Move]] = collections.defaultdict(set)
        for role, move in unpacked:
            grouped[role].add(move)
        grouped_frozen = {role: frozenset(moves) for role, moves in grouped.items()}
        return FrozenDict(grouped_frozen)

    @staticmethod
    def get_sees_shape(sees_ctl: clingo.Control) -> SeesShape:
        sees_symbolic_atoms = sees_ctl.symbolic_atoms.by_signature(name="sees", arity=2)
        subrelations = (
            gdl.Subrelation.from_clingo_symbol(symbolic_atom.symbol) for symbolic_atom in sees_symbolic_atoms
        )
        unpacked_arguments = (subrelation.symbol.arguments for subrelation in subrelations)
        unpacked = ((Role(arguments[0]), arguments[1]) for arguments in unpacked_arguments)
        grouped: DefaultDict[Role, Set[gdl.Subrelation]] = collections.defaultdict(set)
        for role, subrelation in unpacked:
            grouped[role].add(subrelation)
        grouped_frozen = {role: frozenset(subrelations) for role, subrelations in grouped.items()}
        return FrozenDict(grouped_frozen)

    @staticmethod
    def get_goal_shape(goal_ctl: clingo.Control) -> GoalShape:
        goal_symbolic_atoms = goal_ctl.symbolic_atoms.by_signature(name="goal", arity=2)
        subrelations = (
            gdl.Subrelation.from_clingo_symbol(symbolic_atom.symbol) for symbolic_atom in goal_symbolic_atoms
        )
        unpacked_arguments = (subrelation.symbol.arguments for subrelation in subrelations)
        unpacked = ((Role(arguments[0]), arguments[1]) for arguments in unpacked_arguments)
        grouped: DefaultDict[Role, Set[int]] = collections.defaultdict(set)
        for role, goal in unpacked:
            if not goal.is_number:
                raise GoalNotIntegerInterpreterError
            grouped[role].add(goal.symbol.number)
        grouped_frozen = {role: frozenset(goals) for role, goals in grouped.items()}
        return FrozenDict(grouped_frozen)
