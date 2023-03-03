from pyggp.visualizers import Visualizer


def test_as_expected_update_state() -> None:
    visualizer = Visualizer()
    assert visualizer._states == []
    visualizer.update_state(frozenset())
    assert visualizer._states == [frozenset()]
    visualizer.update_state(frozenset({1}), move_nr=3)
    assert visualizer._states == [frozenset(), None, None, frozenset({1})]
    visualizer.update_state(frozenset({2}), move_nr=1)
    assert visualizer._states == [frozenset(), frozenset({2}), None, frozenset({1})]
    visualizer.update_state(frozenset({3}), move_nr=0)
    assert visualizer._states == [frozenset({3}), frozenset({2}), None, frozenset({1})]
    visualizer.update_state(frozenset({4}), move_nr=-1)
    assert visualizer._states == [frozenset({3}), frozenset({2}), None, frozenset({4})]
