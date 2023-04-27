from unittest import mock

from pyggp.agents import InterpreterAgent


@mock.patch.object(InterpreterAgent, "__abstractmethods__", set())
def test_prepare_match() -> None:
    role = mock.MagicMock()
    ruleset = mock.MagicMock()
    startclock_config = mock.MagicMock()
    playclock_config = mock.MagicMock()
    agent = InterpreterAgent()

    agent.prepare_match(
        role,
        ruleset,
        startclock_config,
        playclock_config,
    )

    assert agent.role == role
    assert agent.ruleset == ruleset
    assert agent.startclock_config == startclock_config
    assert agent.playclock_config == playclock_config


@mock.patch.object(InterpreterAgent, "__abstractmethods__", set())
def test_conclude_match() -> None:
    view = mock.MagicMock()
    agent = InterpreterAgent()

    agent.conclude_match(view)

    assert agent.interpreter is None
    assert agent.role is None
    assert agent.ruleset is None
    assert agent.startclock_config is None
    assert agent.playclock_config is None
