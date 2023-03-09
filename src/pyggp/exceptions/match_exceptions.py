from pyggp.actors import Actor
from pyggp.gdl import Move, Role


class MatchError(Exception):
    pass


class MatchNotStartedError(MatchError):
    pass


class MatchPrematurelyTerminatedError(MatchError):
    pass


class MatchDNSError(MatchPrematurelyTerminatedError):
    def __init__(self, role: Role, actor: Actor):
        message = f"{role=}, {actor=}"
        super().__init__(message)


class MatchDNFError(MatchPrematurelyTerminatedError):
    def __init__(self, move_nr: int, actor: Actor, role: Role, reason: str) -> None:
        message = f"Match terminated prematurely after move {move_nr} by {actor} as {role}: {reason}"
        super().__init__(message)


class MatchTimeoutError(MatchDNFError):
    def __init__(self, move_nr: int, actor: Actor, role: Role) -> None:
        super().__init__(move_nr, actor, role, "timeout")


class MatchIllegalMoveError(MatchDNFError):
    def __init__(self, move_nr: int, actor: Actor, role: Role, move: Move) -> None:
        super().__init__(move_nr, actor, role, f"illegal move({move})")
