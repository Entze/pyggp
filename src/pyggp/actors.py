"""All standard actors.

Actors are the interface between the game engine and the agents. Their API is inspired by the ggp.stanford.edu courses'
third chapter (see http://ggp.stanford.edu/chapters/chapter_03.html).

"""
import abc
from dataclasses import dataclass
from typing import Optional, Protocol

import pyggp.game_description_language as gdl
from pyggp._logging import format_id, format_timedelta, rich
from pyggp.agents import Agent
from pyggp.engine_primitives import Move, Role, View
from pyggp.exceptions.actor_exceptions import TimeoutActorError
from pyggp.game_description_language.rulesets import Ruleset
from pyggp.gameclocks import GameClock


class Actor(Protocol):
    startclock: Optional[GameClock]
    playclock: Optional[GameClock]
    is_human_actor: bool

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

    def send_stop(self, view: View) -> None:
        """Sends the stop message to the agent.

        Messages the agent that the game has reached a terminal state.

        Args:
            view: The current state of the game as seen by the agent

        """

    def send_abort(self) -> None:
        """Sends the abort message to the agent.

        Messages the agent that the game ended in an abnormal way. This may be in any state of the game, including
        terminal states.

        """


class _AbstractActor(Actor, abc.ABC):
    def __rich__(self) -> str:
        id_str = f"id={format_id(self)}"
        is_human_actor_str = "" if not self.is_human_actor else ", is_human_actor"
        attributes_str = f"{id_str}{is_human_actor_str}"
        information_str = ""
        if self.playclock is not None:
            information_str = f"\\[remaining_time={rich(self.playclock)}]"

        return f"{self.__class__.__name__}{information_str}({attributes_str})"

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
        self.startclock: Optional[GameClock] = GameClock.from_configuration(startclock_configuration)
        with self.startclock:
            self.playclock: Optional[GameClock] = GameClock.from_configuration(playclock_configuration)
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
        assert self.playclock is not None, "Assumption: playclock is not None (should have been set in send_start)"
        with self.playclock:
            move = self._send_play(ply, view)
        if self.playclock.is_expired:
            raise TimeoutActorError
        # Disables RET504 (Unnecessary variable assignment before `return` statement). Because: Check if playclock is
        # expired is required before returning the move.
        return move  # noqa: RET504

    def _send_play(self, ply: int, view: View) -> Move:
        raise NotImplementedError


@dataclass
class LocalActor(_AbstractActor):
    """Actor that communicates with an agent via python method calls."""

    # region Attributes and Properties

    agent: Agent
    startclock: Optional[GameClock] = None
    playclock: Optional[GameClock] = None
    is_human_actor: bool = False

    # endregion

    # region Methods

    def _send_start(
        self,
        role: Role,
        ruleset: Ruleset,
        startclock_config: GameClock.Configuration,
        playclock_config: GameClock.Configuration,
    ) -> None:
        self.agent.prepare_match(role, ruleset, startclock_config, playclock_config)

    def _send_play(self, ply: int, view: View) -> Move:
        assert self.playclock is not None, "Assumption: playclock is not None (should have been set in send_start)"
        return self.agent.calculate_move(ply, self.playclock.total_time_ns, view)

    def send_abort(self) -> None:
        self.agent.abort_match()

    def send_stop(self, view: View) -> None:
        self.agent.conclude_match(view)

    # endregion
