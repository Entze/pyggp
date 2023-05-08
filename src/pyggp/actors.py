"""All standard actors.

Actors are the interface between the game engine and the agents. Their API is inspired by the ggp.stanford.edu courses'
third chapter (see http://ggp.stanford.edu/chapters/chapter_03.html).

"""
from dataclasses import dataclass
from typing import Optional

import pyggp.game_description_language as gdl
from pyggp.agents import Agent
from pyggp.engine_primitives import Move, Role, View
from pyggp.exceptions.actor_exceptions import AgentIsNoneLocalActorError, PlayclockIsNoneActorError, TimeoutActorError
from pyggp.game_description_language.rulesets import Ruleset
from pyggp.gameclocks import GameClock


@dataclass
class Actor:
    """Base class for all actors."""

    # region Attributes and Properties

    startclock: Optional[GameClock] = None
    "Startclock of the actor."
    playclock: Optional[GameClock] = None
    "Playclock of the actor."
    is_human_actor: bool = False
    "Whether the actor is a human actor."

    # endregion

    def send_start(
        self,
        role: Role,
        ruleset: gdl.Ruleset,
        startclock_configuration: GameClock.Configuration,
        playclock_configuration: GameClock.Configuration,
    ) -> None:
        """Sends the start message to the agent.

        Args:
            role: Role of the agent
            ruleset: Ruleset of the match
            startclock_configuration: Configuration of startclock
            playclock_configuration: Configuration of playclock

        Raises:
            ActorTimeoutError: startclock expired

        """
        self.startclock = GameClock.from_configuration(startclock_configuration)
        with self.startclock:
            self.playclock = GameClock.from_configuration(playclock_configuration)
            self._send_start(role, ruleset, startclock_configuration, playclock_configuration)
        if self.startclock.is_expired:
            raise TimeoutActorError(
                available_time=startclock_configuration.total_time + startclock_configuration.delay,
                delta=self.startclock.last_delta,
                role=role,
            )

    def _send_start(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        raise NotImplementedError

    def send_play(self, ply: int, view: View) -> Move:
        """Sends the play message to the agent.

        Args:
            ply: Current ply
            view: Current state of the game as seen by the agent

        Returns:
            Agent's returned move

        Raises:
            ActorNotStartedError: playclock is None
            ActorTimeoutError: playclock expired

        """
        if self.playclock is None:
            raise PlayclockIsNoneActorError
        assert self.playclock is not None
        with self.playclock:
            move = self._send_play(ply, view)
        if self.playclock.is_expired:
            raise TimeoutActorError
        # Disables RET504 (Unnecessary variable assignment before `return` statement). Because: Check if playclock is
        # expired is required before returning the move.
        return move  # noqa: RET504

    def _send_play(self, ply: int, view: View) -> Move:
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

    def send_stop(self, view: View) -> None:
        """Sends the stop message to the agent.

        Messages the agent that the game has reached a terminal state.

        Args:
            view: The current state of the game as seen by the agent

        """
        self.startclock = None
        self.playclock = None
        self._send_stop(view)

    def _send_stop(self, view: View) -> None:
        raise NotImplementedError


@dataclass
class LocalActor(Actor):
    """Actor that communicates with an agent via python method calls."""

    # region Attributes and Properties

    agent: Optional[Agent] = None
    "Agent that is communicated with."

    # endregion

    # region Magic Methods

    def __post_init__(self) -> None:
        """Ensure that the agent is not None."""
        if self.agent is None:
            raise AgentIsNoneLocalActorError

    # endregion

    # region Methods

    def _send_start(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        if self.agent is None:
            raise AgentIsNoneLocalActorError
        assert self.agent is not None
        self.agent.prepare_match(role, ruleset, startclock_config, playclock_config)

    def _send_play(self, ply: int, view: View) -> Move:
        assert self.playclock is not None
        if self.agent is None:
            raise AgentIsNoneLocalActorError
        assert self.agent is not None
        return self.agent.calculate_move(ply, self.playclock.total_time_ns, view)

    def _send_abort(self) -> None:
        if self.agent is None:
            raise AgentIsNoneLocalActorError
        assert self.agent is not None
        self.agent.abort_match()

    def _send_stop(self, view: View) -> None:
        if self.agent is None:
            raise AgentIsNoneLocalActorError
        assert self.agent is not None
        self.agent.conclude_match(view)

    # endregion
