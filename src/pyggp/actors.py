"""All standard actors.

Actors are the interface between the game engine and the agents. Their API is inspired by the ggp.stanford.edu courses'
third chapter (see http://ggp.stanford.edu/chapters/chapter_03.html).

"""

from typing import Optional

from pyggp.agents import Agent
from pyggp.exceptions.actor_exceptions import ActorPlayclockIsNoneError, ActorTimeoutError
from pyggp.gameclocks import GameClock, GameClockConfiguration
from pyggp.gdl import ConcreteRole, Move, Role, Ruleset, State


class Actor:
    """Base class for all actors.

    Attributes:
        startclock: Startclock of the actor
        playclock: Playclock of the actor
        is_human_actor: Whether the actor is a human actor

    """

    # Disables FBT001 (Boolean positional arg in function definition). Reason: is_human_actor is a value of an Actor
    # object, not a flag.
    def __init__(self, is_human_actor: bool = False) -> None:  # noqa: FBT001
        """Initializes Actor.

        Args:
            is_human_actor: Whether the actor is a human actor

        """
        self.startclock: Optional[GameClock] = None
        self.playclock: Optional[GameClock] = None
        self.is_human_actor: bool = is_human_actor

    def __repr__(self) -> str:
        """Gets representation of Actor.

        Returns:
            Representation of Actor

        """
        return (
            f"{self.__class__.__name__}(id={hex(id(self))}, "
            f"is_human_actor={self.is_human_actor!r}, "
            f"startclock={self.startclock!r}, "
            f"playclock={self.playclock!r})"
        )

    def send_start(
        self,
        role: ConcreteRole,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        """Sends the start message to the agent.

        Args:
            role: Role of the agent
            ruleset: Ruleset of the match
            startclock_config: Configuration of startclock
            playclock_config: Configuration of playclock

        Raises:
            ActorTimeoutError: startclock expired

        """
        self.startclock = GameClock(startclock_config)
        with self.startclock:
            self.playclock = GameClock(playclock_config)
            self._send_start(role, ruleset, startclock_config, playclock_config)
        if self.startclock.is_expired:
            raise ActorTimeoutError

    def _send_start(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClockConfiguration,
        playclock_config: GameClockConfiguration,
    ) -> None:
        raise NotImplementedError

    def send_play(self, move_nr: int, view: State) -> Move:
        """Sends the play message to the agent.

        Args:
            move_nr: Number of this move
            view: Current state of the game as seen by the agent

        Returns:
            Agent's returned move

        Raises:
            ActorNotStartedError: playclock is None
            ActorTimeoutError: playclock expired

        """
        if self.playclock is None:
            raise ActorPlayclockIsNoneError
        assert self.playclock is not None
        with self.playclock:
            move = self._send_play(move_nr, view)
        if self.playclock.is_expired:
            raise ActorTimeoutError
        # Disables RET504 (Unnecessary variable assignment before `return` statement). Reason: Check if playclock is
        # expired is required before returning the move.
        return move  # noqa: RET504

    def _send_play(self, move_nr: int, view: State) -> Move:
        raise NotImplementedError

    def send_abort(self) -> None:
        """Sends the abort message to the agent.

        Messages the agent that the game ended in an abnormal way. This may be in any state of the game, including
        terminal states.

        """
        self.startclock = None
        self.playclock = None
        self._send_abort()

    def _send_abort(self) -> None:
        raise NotImplementedError

    def send_stop(self, view: State) -> None:
        """Sends the stop message to the agent.

        Messages the agent that the game has reached a terminal state.

        Args:
            view: The current state of the game as seen by the agent

        """
        self.startclock = None
        self.playclock = None
        self._send_stop(view)

    def _send_stop(self, view: State) -> None:
        raise NotImplementedError


class LocalActor(Actor):
    """Actor that communicates with an agent via python method calls.

    Attributes:
        agent: Agent that is controlled by this actor
        is_human_actor: Whether the actor is a human actor

    """

    # Disables FBT001 (Boolean positional arg in function definition). Reason: is_human_actor is a value of an Actor
    # object, not a flag.
    def __init__(self, agent: Agent, is_human_actor: bool = False) -> None:  # noqa: FBT001
        """Initializes LocalActor.

        Args:
            agent: Agent that is controlled by this actor
            is_human_actor: Whether the actor is a human actor

        """
        super().__init__(is_human_actor=is_human_actor)
        self.agent: Agent = agent

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
