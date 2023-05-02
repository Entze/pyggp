"""Exceptions regarding agents."""


class AgentError(Exception):
    """Base class for all exceptions regarding agents."""


class RoleIsNoneAgentError(AgentError):
    """Accessed role when it was None."""


class PlayclockConfigurationIsNoneAgentError(AgentError):
    """Accessed playclock_configuration when it was None."""


class InterpreterAgentError(AgentError):
    """Base class for all exceptions regarding interpreter agents."""


class InterpreterIsNoneInterpreterAgentError(InterpreterAgentError):
    """Accessed interpreter when it was None."""


class MCTSAgentError(InterpreterAgentError):
    """Base class for all exceptions regarding MCTS agents."""


class RootIsNoneMCTSAgentError(MCTSAgentError):
    """Accessed root when it was None."""


class PlayclockIsNoneMCTSAgentError(MCTSAgentError):
    """Accessed play_clock when it was None."""
