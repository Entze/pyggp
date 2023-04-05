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

    assert agent._role == role
    assert agent._ruleset == ruleset
    assert agent._startclock_config == startclock_config
    assert agent._playclock_config == playclock_config


@mock.patch.object(InterpreterAgent, "__abstractmethods__", set())
def test_conclude_match() -> None:
    view = mock.MagicMock()
    agent = InterpreterAgent()

    agent.conclude_match(view)

    assert agent._interpreter is None
    assert agent._role is None
    assert agent._ruleset is None
    assert agent._startclock_config is None
    assert agent._playclock_config is None
