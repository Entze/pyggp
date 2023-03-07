class AgentError(Exception):
    pass


class InterpreterAgentError(AgentError):
    pass


class InterpreterAgentWithoutInterpreterError(InterpreterAgentError):
    pass
