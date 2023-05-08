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


class TreeAgentError(InterpreterAgentError):
    """Base class for all exceptions regarding tree agents."""


class TreeIsNoneTreeAgentError(TreeAgentError):
    """Accessed tree when it was None."""


class SearcherIsNoneTreeAgentError(TreeAgentError):
    """Accessed searcher when it was None."""


class ChooserIsNoneTreeAgentError(TreeAgentError):
    """Accessed chooser when it was None."""
