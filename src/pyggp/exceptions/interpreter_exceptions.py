"""Exceptions regarding interpreters."""


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


class MoreThanOneModelInterpreterError(InvalidGDLInterpreterError):
    """More than one model was found in a context where only one is allowed."""


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


class GoalNotIntegerInterpreterError(InvalidGDLInterpreterError):
    """Goal is not an integer."""
