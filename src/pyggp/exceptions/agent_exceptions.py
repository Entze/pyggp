"""Exceptions regarding agents."""


class AgentError(Exception):
    """Base class for all exceptions regarding agents."""


class InterpreterAgentError(AgentError):
    """Base class for all exceptions regarding interpreter agents."""


class InterpreterIsNoneInterpreterAgentError(InterpreterAgentError):
    """Accessed interpreter when it was None."""


class RoleIsNoneInterpreterAgentError(InterpreterAgentError):
    """Accessed role when it was None."""
