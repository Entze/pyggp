"""All standard actors.

Actors are the interface between the game engine and the agents. Their API is inspired by the ggp.stanford.edu courses'
third chapter (see http://ggp.stanford.edu/chapters/chapter_03.html).
"""

from typing import Optional

from pyggp.agents import Agent
from pyggp.exceptions.actor_exceptions import ActorNotStartedError, ActorTimeoutError
from pyggp.gameclocks import GameClock, GameClockConfiguration
from pyggp.gdl import ConcreteRole, Move, Role, Ruleset, State


class Actor:
    """Base class for all actors.

    Attributes:
        startclock: The startclock of the actor
        playclock: The playclock of the actor
        is_human_actor: Whether the actor is a human actor
    """

    def __init__(self, is_human_actor: bool = False) -> None:
        """Initializer.

        Args:
            is_human_actor: Whether the actor is a human actor

        """
        self.startclock: Optional[GameClock] = None
        self.playclock: Optional[GameClock] = None
        self.is_human_actor: bool = is_human_actor

    def __repr__(self) -> str:
        """Representation."""
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
            role: The role of the agent
            ruleset: The ruleset of the game
            startclock_config: The configuration of the startclock
            playclock_config: The configuration of the playclock

        Raises:
            ActorTimeoutError: The startclock expired

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
            move_nr: The number of the move
            view: The current state of the game as seen by the agent

        Returns:
            The agent's returned move

        Raises:
            ActorNotStartedError: The playclock is None
            ActorTimeoutError: The playclock expired
        """
        if self.playclock is None:
            raise ActorNotStartedError
        assert self.playclock is not None
        with self.playclock:
            move = self._send_play(move_nr, view)
        if self.playclock.is_expired:
            raise ActorTimeoutError
        return move

    def _send_play(self, move_nr: int, view: State) -> Move:
        raise NotImplementedError

    def send_abort(self) -> None:
        """Sends the abort message to the agent.

        This is called when the game is aborted (ended prematurely).

        """
        self.startclock = None
        self.playclock = None
        self._send_abort()

    def _send_abort(self) -> None:
        raise NotImplementedError

    def send_stop(self, view: State) -> None:
        """Sends the stop message to the agent.

        This is called when the game has reached a terminal state.

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
        agent: The agent that is controlled by this actor
        is_human_actor: Whether the actor is a human actor
    """

    def __init__(self, agent: Agent, is_human_actor: bool = False) -> None:
        """Initializer.

        Args:
            agent: The agent that is controlled by this actor
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
