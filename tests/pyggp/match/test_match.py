import time
from typing import TYPE_CHECKING, Any, Mapping, Union
from unittest import mock

import exceptiongroup
import pyggp.game_description_language as gdl
import pytest
from pyggp.engine_primitives import RANDOM, Role, State, View
from pyggp.exceptions.actor_exceptions import ActorError, TimeoutActorError
from pyggp.exceptions.match_exceptions import DidNotStartMatchError, IllegalMoveMatchError
from pyggp.gameclocks import GameClock
from pyggp.interpreters import Interpreter
from pyggp.match import _DNF_ILLEGAL_MOVE, _DNF_TIMEOUT, _DNS_TIMEOUT, Disqualification, Match, _StartProcessor

if TYPE_CHECKING:
    from pyggp.actors import Actor


@pytest.fixture()
def mock_ruleset() -> gdl.Ruleset:
    return mock.MagicMock()


@pytest.fixture()
def mock_interpreter() -> Interpreter:
    return mock.MagicMock()


@pytest.fixture()
def one_player_mock_match(
    mock_ruleset: gdl.Ruleset,
    mock_interpreter: Interpreter,
) -> Match:
    role: Role = Role(gdl.Subrelation(gdl.Relation("role")))
    actor: Actor = mock.MagicMock()
    role_actor_map: Mapping[Role, Actor] = {
        role: actor,
    }
    startclock_config: GameClock.Configuration = mock.MagicMock()
    role_startclock_configuration_map: Mapping[Role, GameClock.Configuration] = {
        role: startclock_config,
    }
    playclock_config: GameClock.Configuration = mock.MagicMock()
    role_playclock_configuration_map: Mapping[Role, GameClock.Configuration] = {
        role: playclock_config,
    }
    return Match(
        ruleset=mock_ruleset,
        interpreter=mock_interpreter,
        role_actor_map=role_actor_map,
        role_startclock_configuration_map=role_startclock_configuration_map,
        role_playclock_configuration_map=role_playclock_configuration_map,
    )


@pytest.fixture()
def two_player_mock_match(
    mock_ruleset: gdl.Ruleset,
    mock_interpreter: Interpreter,
) -> Match:
    role_1: Role = Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),))))
    role_2: Role = Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),))))
    actor_1: Actor = mock.MagicMock()
    actor_2: Actor = mock.MagicMock()
    role_actor_map: Mapping[Role, Actor] = {
        role_1: actor_1,
        role_2: actor_2,
    }
    startclock_config_1: GameClock.Configuration = mock.MagicMock()
    startclock_config_2: GameClock.Configuration = mock.MagicMock()
    role_startclock_configuration_map: Mapping[Role, GameClock.Configuration] = {
        role_1: startclock_config_1,
        role_2: startclock_config_2,
    }
    playclock_config_1: GameClock.Configuration = mock.MagicMock()
    playclock_config_2: GameClock.Configuration = mock.MagicMock()
    role_playclock_configuration_map: Mapping[Role, GameClock.Configuration] = {
        role_1: playclock_config_1,
        role_2: playclock_config_2,
    }

    return Match(
        ruleset=mock_ruleset,
        interpreter=mock_interpreter,
        role_actor_map=role_actor_map,
        role_startclock_configuration_map=role_startclock_configuration_map,
        role_playclock_configuration_map=role_playclock_configuration_map,
    )


# noinspection PyUnresolvedReferences
def test_start_two_player_match(two_player_mock_match: Match) -> None:
    init_state = State(frozenset())
    role_1, role_2 = sorted(two_player_mock_match.role_actor_map.keys())
    actor_1 = two_player_mock_match.role_actor_map[role_1]
    actor_2 = two_player_mock_match.role_actor_map[role_2]
    startclock_config_1 = GameClock.Configuration(total_time=1000.0, increment=0.0, delay=0.0)
    startclock_config_2 = GameClock.Configuration(total_time=1000.0, increment=0.0, delay=0.0)
    two_player_mock_match.role_startclock_configuration_map = {
        role_1: startclock_config_1,
        role_2: startclock_config_2,
    }

    playclock_config_1 = two_player_mock_match.role_playclock_configuration_map[role_1]
    playclock_config_2 = two_player_mock_match.role_playclock_configuration_map[role_2]

    interpreter = two_player_mock_match.interpreter
    interpreter.get_init_state.return_value = init_state
    interpreter.is_terminal.return_value = False

    assert not two_player_mock_match.states
    assert not two_player_mock_match.utilities
    assert not two_player_mock_match.is_finished
    actor_1.send_start.assert_not_called()
    actor_2.send_start.assert_not_called()

    two_player_mock_match.start()

    assert two_player_mock_match.states
    assert not two_player_mock_match.utilities
    assert not two_player_mock_match.is_finished
    assert two_player_mock_match.states[0] == init_state
    actor_1.send_start.assert_called_once_with(
        role=role_1,
        ruleset=two_player_mock_match.ruleset,
        startclock_configuration=startclock_config_1,
        playclock_configuration=playclock_config_1,
    )
    actor_2.send_start.assert_called_once_with(
        role=role_2,
        ruleset=two_player_mock_match.ruleset,
        startclock_configuration=startclock_config_2,
        playclock_configuration=playclock_config_2,
    )


def test_start_raises_on_timeout(one_player_mock_match: Match) -> None:
    (role,) = one_player_mock_match.role_actor_map.keys()
    actor = one_player_mock_match.role_actor_map[role]
    startclock_config = GameClock.Configuration(total_time=1000.0, increment=0.0, delay=0.0)
    one_player_mock_match.role_startclock_configuration_map = {
        role: startclock_config,
    }

    timeout_exception = TimeoutActorError()

    actor.send_start.side_effect = timeout_exception
    assert not one_player_mock_match.utilities
    assert not one_player_mock_match.is_finished

    with pytest.raises(exceptiongroup.ExceptionGroup) as exception_group:
        one_player_mock_match.start()

    assert exception_group.value.exceptions[0].__cause__ == timeout_exception
    assert one_player_mock_match.utilities
    assert one_player_mock_match.utilities == {role: _DNS_TIMEOUT}
    assert one_player_mock_match.is_finished


def test_start_raises_on_no_response(one_player_mock_match: Match) -> None:
    (role,) = one_player_mock_match.role_actor_map.keys()
    actor = one_player_mock_match.role_actor_map[role]
    startclock_config = GameClock.Configuration(
        total_time=0.1,
        increment=0.0,
        delay=0.0,
    )
    one_player_mock_match.role_startclock_configuration_map = {
        role: startclock_config,
    }

    def _no_response(*args: Any, **kwargs: Any) -> None:  # noqa: ARG001
        time.sleep(2.0)

    actor.send_start.side_effect = _no_response

    assert not one_player_mock_match.utilities
    assert not one_player_mock_match.is_finished

    with pytest.raises(exceptiongroup.ExceptionGroup) as exception_group, mock.patch.object(
        _StartProcessor,
        "total_time",
        0.1,
    ):
        one_player_mock_match.start()

    assert isinstance(exception_group.value.exceptions[0], DidNotStartMatchError)
    assert one_player_mock_match.utilities
    assert one_player_mock_match.utilities == {role: _DNS_TIMEOUT}
    assert one_player_mock_match.is_finished


def test_execute_ply_two_player_match(two_player_mock_match: Match) -> None:
    interpreter = two_player_mock_match.interpreter

    role_1, role_2 = sorted(two_player_mock_match.role_actor_map.keys())
    playclock_1 = mock.MagicMock()
    actor_1 = two_player_mock_match.role_actor_map[role_1]
    actor_2 = two_player_mock_match.role_actor_map[role_2]

    actor_1.is_human_actor = False
    actor_1.playclock = playclock_1

    playclock_1.get_timeout.return_value = 1000.0

    init_state = State(frozenset())
    two_player_mock_match.states = [init_state]
    interpreter.get_roles.return_value = frozenset({role_1, role_2})
    interpreter.get_sees_by_role.return_value = View(init_state)
    interpreter.is_terminal.return_value = False

    assert not two_player_mock_match.is_finished
    actor_1.send_play.assert_not_called()
    actor_2.send_play.assert_not_called()

    with mock.patch.object(Interpreter, "get_roles_in_control") as get_roles_in_control_mock:
        get_roles_in_control_mock.return_value = frozenset({role_1})
        two_player_mock_match.execute_ply()

    actor_1.send_play.assert_called_once_with(
        ply=0,
        view=View(init_state),
    )
    actor_2.send_play.assert_not_called()
    assert not two_player_mock_match.is_finished


def test_execute_ply_raises_on_timeout(one_player_mock_match: Match) -> None:
    interpreter = one_player_mock_match.interpreter

    (role,) = one_player_mock_match.role_actor_map.keys()
    actor = one_player_mock_match.role_actor_map[role]
    playclock_config = GameClock.Configuration(total_time=1000.0, increment=0.0, delay=0.0)
    one_player_mock_match.role_playclock_configuration_map = {
        role: playclock_config,
    }

    actor.playclock = mock.MagicMock()
    actor.playclock.get_timeout.return_value = 1000.0

    init_state = State(frozenset())
    one_player_mock_match.states = [init_state]
    interpreter.get_roles.return_value = frozenset({role})
    interpreter.get_sees_by_role.return_value = View(init_state)
    interpreter.is_terminal.return_value = False

    timeout_exception = TimeoutActorError()

    actor.send_play.side_effect = timeout_exception

    assert not one_player_mock_match.is_finished

    with mock.patch.object(Interpreter, "get_roles_in_control") as get_roles_in_control_mock:
        get_roles_in_control_mock.return_value = frozenset({role})
        with pytest.raises(exceptiongroup.ExceptionGroup) as exception_group:
            one_player_mock_match.execute_ply()

    assert exception_group.value.exceptions[0].__cause__ == timeout_exception
    assert one_player_mock_match.is_finished


def test_execute_ply_raises_on_actor_error(one_player_mock_match: Match) -> None:
    interpreter = one_player_mock_match.interpreter

    (role,) = one_player_mock_match.role_actor_map.keys()
    actor = one_player_mock_match.role_actor_map[role]
    playclock_config = GameClock.Configuration(total_time=1000.0, increment=0.0, delay=0.0)
    one_player_mock_match.role_playclock_configuration_map = {
        role: playclock_config,
    }

    actor.playclock = mock.MagicMock()
    actor.playclock.get_timeout.return_value = 1000.0

    init_state = State(frozenset())
    one_player_mock_match.states = [init_state]
    interpreter.get_roles.return_value = frozenset({role})
    interpreter.get_sees_by_role.return_value = View(init_state)
    interpreter.is_terminal.return_value = False

    actor_error = ActorError()

    actor.send_play.side_effect = actor_error

    assert not one_player_mock_match.is_finished

    with mock.patch.object(Interpreter, "get_roles_in_control") as get_roles_in_control_mock:
        get_roles_in_control_mock.return_value = frozenset({role})
        with pytest.raises(exceptiongroup.ExceptionGroup) as exception_group:
            one_player_mock_match.execute_ply()

    assert exception_group.value.exceptions[0].__cause__ == actor_error
    assert one_player_mock_match.is_finished


def test_execute_ply_raises_on_illegal_move(one_player_mock_match: Match) -> None:
    interpreter = one_player_mock_match.interpreter

    (role,) = one_player_mock_match.role_actor_map.keys()
    actor = one_player_mock_match.role_actor_map[role]
    playclock_config = GameClock.Configuration(total_time=1000.0, increment=0.0, delay=0.0)
    one_player_mock_match.role_playclock_configuration_map = {
        role: playclock_config,
    }

    actor.playclock = mock.MagicMock()
    actor.playclock.get_timeout.return_value = 1000.0

    init_state = State(frozenset())
    one_player_mock_match.states = [init_state]
    interpreter.get_roles.return_value = frozenset({role})
    interpreter.get_sees_by_role.return_value = View(init_state)
    interpreter.is_legal.return_value = False
    interpreter.is_terminal.return_value = False

    assert not one_player_mock_match.is_finished

    with mock.patch.object(Interpreter, "get_roles_in_control") as get_roles_in_control_mock:
        get_roles_in_control_mock.return_value = frozenset({role})
        with pytest.raises(exceptiongroup.ExceptionGroup) as exception_group:
            one_player_mock_match.execute_ply()

    assert isinstance(exception_group.value.exceptions[0], IllegalMoveMatchError)
    assert one_player_mock_match.is_finished


def test_conclude_two_player_match(two_player_mock_match: Match) -> None:
    interpreter = two_player_mock_match.interpreter

    role_1, role_2 = sorted(two_player_mock_match.role_actor_map.keys())
    actor_1 = two_player_mock_match.role_actor_map[role_1]
    actor_2 = two_player_mock_match.role_actor_map[role_2]

    init_state = State(frozenset())
    final_state = State(frozenset())
    two_player_mock_match.states = [init_state, final_state]
    interpreter.get_sees_by_role.return_value = View(final_state)
    interpreter.is_terminal.return_value = True
    utilities = {role_1: 1, role_2: 0}
    interpreter.get_goals.return_value = utilities

    assert two_player_mock_match.is_finished
    assert not two_player_mock_match.utilities
    actor_1.send_stop.assert_not_called()
    actor_2.send_stop.assert_not_called()

    two_player_mock_match.conclude()

    assert two_player_mock_match.is_finished
    assert two_player_mock_match.utilities == utilities
    actor_1.send_stop.assert_called_once_with(
        view=View(final_state),
    )
    actor_2.send_stop.assert_called_once_with(
        view=View(final_state),
    )


def test_abort_two_player_match(two_player_mock_match: Match) -> None:
    role_1, role_2 = sorted(two_player_mock_match.role_actor_map.keys())
    actor_1 = two_player_mock_match.role_actor_map[role_1]
    actor_2 = two_player_mock_match.role_actor_map[role_2]

    actor_1.send_abort.assert_not_called()
    actor_2.send_abort.assert_not_called()

    two_player_mock_match.abort()

    actor_1.send_abort.assert_called_once_with()
    actor_2.send_abort.assert_called_once_with()


@pytest.mark.parametrize(
    ("utilities", "expected"),
    [
        ({}, {}),
        (
            {Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 100},
            {Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 0},
        ),
        (
            {
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 100,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),)))): 0,
            },
            {
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 0,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),)))): 1,
            },
        ),
        (
            {
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 50,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),)))): 50,
            },
            {
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 0,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),)))): 0,
            },
        ),
        (
            {
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 50,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),)))): 50,
                RANDOM: None,
            },
            {
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 0,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),)))): 0,
                RANDOM: 2,
            },
        ),
        (
            {
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 100,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),)))): 50,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(3)),)))): 50,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(4)),)))): 0,
                RANDOM: None,
            },
            {
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 0,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),)))): 1,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(3)),)))): 1,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(4)),)))): 3,
                RANDOM: 4,
            },
        ),
        (
            {
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): None,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),)))): None,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(3)),)))): _DNF_ILLEGAL_MOVE,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(4)),)))): _DNF_TIMEOUT,
                RANDOM: None,
            },
            {
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(1)),)))): 0,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(2)),)))): 0,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(3)),)))): 3,
                Role(gdl.Subrelation(gdl.Relation("role", (gdl.Subrelation(gdl.Number(4)),)))): 3,
                RANDOM: 0,
            },
        ),
    ],
)
def test_get_rank(utilities: Mapping[Role, Union[int, None, Disqualification]], expected: Mapping[Role, int]) -> None:
    actual = Match.get_rank(utilities)
    assert actual == expected
