"""Exceptions regarding interpreters."""
from typing import Iterable, Mapping, Optional, Sequence

import clingo

from pyggp._logging import format_list, format_sorted_set
from pyggp.engine_primitives import Role


class InterpreterError(Exception):
    """Base class for all exceptions regarding interpreters."""


class TimeoutInterpreterError(InterpreterError):
    """Timed out during solving."""


class ModelTimeoutInterpreterError(TimeoutInterpreterError):
    """Timed out during solving for first model."""


class SolveTimeoutInterpreterError(TimeoutInterpreterError):
    """Timed out during solving for proving completion."""


class InvalidGDLInterpreterError(InterpreterError):
    """Base class for all exceptions regarding invalid GDL passed to an interpreter."""

    def __init__(self, reason: Optional[str] = None) -> None:
        message = "Invalid GDL"
        if reason is not None:
            message = f"Invalid GDL: {reason}"
        super().__init__(message)


class MoreThanOneModelInterpreterError(InvalidGDLInterpreterError):
    """More than one model was found in a context where only one is allowed."""

    def __init__(self, models: Optional[Iterable[Sequence[clingo.Symbol]]] = None) -> None:
        context: str = "More than one model found"
        models_str: str = ""
        if models is not None:
            models_str = ":\n" + "\n".join(format_sorted_set(model) for model in models)
        reason: str = f"{context}{models_str}"
        super().__init__(reason)


class UnsatInterpreterError(InvalidGDLInterpreterError):
    """No model was found in a context where at least one is required."""


class UnsatRolesInterpreterError(UnsatInterpreterError):
    """Rules for roles are unsatisfiable."""


class UnsatInitInterpreterError(UnsatInterpreterError):
    """Rules for init are unsatisfiable."""


class UnsatNextInterpreterError(UnsatInterpreterError):
    """Rules for next are unsatisfiable."""


class UnsatSeesInterpreterError(UnsatInterpreterError):
    """Rules for sees are unsatisfiable."""


class UnsatLegalInterpreterError(UnsatInterpreterError):
    """Rules for legal are unsatisfiable."""


class UnsatGoalInterpreterError(UnsatInterpreterError):
    """Rules for goal are unsatisfiable."""


class UnsatDevelopmentsInterpreterError(UnsatInterpreterError):
    """Rules for developments are unsatisfiable."""


class UnexpectedRoleInterpreterError(InvalidGDLInterpreterError):
    """Unexpected role found."""


class MultipleGoalsInterpreterError(InvalidGDLInterpreterError):
    """Multiple goals for a role found."""

    def __init__(self, goals: Optional[Mapping[Role, Sequence[Optional[int]]]] = None) -> None:
        context: str = "Multiple goals found"
        goals_str: str = ""
        if goals is not None:
            goals_str = ":\n" + "\n".join(f"{role}: {format_list(goals[role])}" for role in sorted(goals.keys()))
        reason: str = f"{context}{goals_str}"
        super().__init__(reason)


class GoalNotIntegerInterpreterError(InvalidGDLInterpreterError):
    """Goal is not an integer."""
