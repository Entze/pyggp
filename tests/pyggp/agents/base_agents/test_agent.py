from unittest import mock

from pyggp.agents import Agent


@mock.patch.object(Agent, "__abstractmethods__", set())
def test_with_stmt() -> None:
    agent = Agent()
    with mock.patch.object(agent, "set_up") as set_up, mock.patch.object(agent, "tear_down") as tear_down:
        set_up.assert_not_called()
        tear_down.assert_not_called()
        with agent:
            pass
        set_up.assert_called_once()
        tear_down.assert_called_once()
