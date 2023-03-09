class ActorError(Exception):
    pass


class ActorNotStartedError(ActorError):
    pass


class ActorTimeoutError(ActorError):
    pass


class ActorIllegalMoveError(ActorError):
    pass
