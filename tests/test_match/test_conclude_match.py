# pylint: disable=missing-docstring,invalid-name,unused-argument
from common import MockAgent, mock_ruleset_1, mock_match, MockRuleset1Interpreter


def test_passes_state():
    agent = MockAgent()
    match = mock_match(ruleset=mock_ruleset_1, interpreter=MockRuleset1Interpreter(), agents=(agent,))

    assert not agent.called_conclude_match
    match.conclude_match()
    assert agent.called_conclude_match
