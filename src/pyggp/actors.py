from pyggp.agents import Agent
from pyggp.exceptions.actor_exceptions import ActorNotStartedError, ActorTimeoutError
from pyggp.gameclocks import GameClock, GameClockConfiguration
from pyggp.gdl import Move, Role, Ruleset, State


class Actor:
    def __init__(self) -> None:
        self.startclock: GameClock | None = None
        self.playclock: GameClock | None = None

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={hex(id(self))}, "
            f"startclock={self.startclock!r}, playclock={self.playclock!r})"
        )

    def send_start(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        self.startclock = GameClock(startclock_config)
        with self.startclock:
            self.playclock = GameClock(playclock_config)
            self._send_start(role, ruleset, startclock_config, playclock_config)
        if self.startclock.is_expired:
            raise TimeoutError

    def _send_start(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        raise NotImplementedError

    def send_play(self, move_nr: int, view: State) -> Move:
        if self.playclock is None:
            raise ActorNotStartedError
        assert self.playclock is not None
        with self.playclock:
            move = self._send_play(move_nr, view)
        if self.playclock.is_expired:
            raise TimeoutError
        return move

    def _send_play(self, move_nr: int, view: State) -> Move:
        raise NotImplementedError

    def send_abort(self) -> None:
        self.startclock = None
        self.playclock = None
        self._send_abort()

    def _send_abort(self) -> None:
        raise NotImplementedError

    def send_stop(self, view: State) -> None:
        self.startclock = None
        self.playclock = None
        self._send_stop(view)

    def _send_stop(self, view: State) -> None:
        raise NotImplementedError


class LocalActor(Actor):
    def __init__(self, agent: Agent) -> None:
        super().__init__()
        self.agent = agent

    def _send_start(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        self.agent.prepare_match(role, ruleset, startclock_config, playclock_config)

    def _send_play(self, move_nr: int, view: State) -> Move:
        assert self.playclock is not None
        return self.agent.calculate_move(move_nr, self.playclock.total_time_ns, view)

    def _send_abort(self) -> None:
        self.agent.abort_match()

    def _send_stop(self, view: State) -> None:
        self.agent.conclude_match(view)
