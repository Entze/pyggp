# pylint: disable=missing-docstring,invalid-name,unused-argument
from common import MockAgent, mock_match, mock_ruleset_1, MockRuleset1Interpreter


def test_passes_state():
    agent = MockAgent()
    match = mock_match(ruleset=mock_ruleset_1, interpreter=MockRuleset1Interpreter(), agents=(agent,))

    assert not agent.called_abort_match
    match.abort_match()
    assert agent.called_abort_match